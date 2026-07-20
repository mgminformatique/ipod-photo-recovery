from __future__ import annotations

import csv
import hashlib
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/ithmb_database_link_probe_fast")

BLOCK_SIZES = (16, 24, 32, 64, 128, 256, 512, 1024)
FRAGMENT_SIZES = (8, 12, 16, 24, 32)

MAX_BLOCKS_PER_FILE_PER_SIZE = 300
MAX_FRAGMENT_SAMPLES_PER_FILE_PER_SIZE = 300
MAX_HITS_PER_NEEDLE = 50


def find_database() -> Path:
    matches = sorted(CACHE_ROOT.rglob("Photo Database"))
    if not matches:
        raise FileNotFoundError(f"Photo Database introuvable sous {CACHE_ROOT}")
    return matches[0]


def find_ithmb_files() -> list[Path]:
    files = sorted(CACHE_ROOT.rglob("*.ithmb"))
    if not files:
        raise FileNotFoundError(f"Aucun fichier .ithmb trouvé sous {CACHE_ROOT}")
    return files


def sampled_offsets(length: int, size: int, limit: int) -> list[int]:
    if length < size:
        return []

    count = ((length - size) // size) + 1
    if count <= limit:
        return [i * size for i in range(count)]

    offsets = set()

    edge = min(40, count)
    for i in range(edge):
        offsets.add(i * size)
        offsets.add((count - 1 - i) * size)

    remaining = max(1, limit - len(offsets))
    for i in range(remaining):
        idx = round(i * (count - 1) / max(remaining - 1, 1))
        offsets.add(idx * size)

    return sorted(offsets)[:limit]


def all_occurrences(data: bytes, needle: bytes, max_hits: int = MAX_HITS_PER_NEEDLE) -> list[int]:
    hits = []
    start = 0

    while len(hits) < max_hits:
        pos = data.find(needle, start)
        if pos < 0:
            break
        hits.append(pos)
        start = pos + 1

    return hits


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def u32_variants(value: int) -> tuple[tuple[str, bytes], ...]:
    value &= 0xFFFFFFFF
    return (
        ("u32le", struct.pack("<I", value)),
        ("u32be", struct.pack(">I", value)),
    )


def u64_variants(value: int) -> tuple[tuple[str, bytes], ...]:
    value &= 0xFFFFFFFFFFFFFFFF
    return (
        ("u64le", struct.pack("<Q", value)),
        ("u64be", struct.pack(">Q", value)),
    )


def build_db_indexes(db: bytes):
    indexes = {}

    for size in set(FRAGMENT_SIZES) | {4, 8}:
        index = defaultdict(list)
        stop = len(db) - size + 1

        for offset in range(stop):
            chunk = db[offset:offset + size]
            if len(index[chunk]) < MAX_HITS_PER_NEEDLE:
                index[chunk].append(offset)

        indexes[size] = index

    return indexes


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    db_path = find_database()
    db = db_path.read_bytes()
    ithmb_files = find_ithmb_files()

    print("=" * 110)
    print("ITHMB ↔ PHOTO DATABASE LINK PROBE — FAST")
    print("=" * 110)
    print(f"Photo Database : {db_path}")
    print(f"Taille DB      : {len(db):,}")
    print(f"Fichiers ITHMB : {len(ithmb_files)}")
    print()

    print("[1/5] Indexation unique de la Photo Database...")
    db_indexes = build_db_indexes(db)
    print("      Indexation terminée.")
    print()

    numeric_hits = []
    digest_hits = []
    fragment_hits = []
    metric_candidates = []

    print("[2/5] Tailles et empreintes complètes...")

    for index, path in enumerate(ithmb_files, 1):
        data = path.read_bytes()
        relative = str(path.relative_to(CACHE_ROOT))

        print(f"  [{index:02d}/{len(ithmb_files):02d}] {relative}")

        numeric_values = {
            "file_size": len(data),
            "crc32": zlib.crc32(data) & 0xFFFFFFFF,
            "adler32": zlib.adler32(data) & 0xFFFFFFFF,
        }

        for name, value in numeric_values.items():
            variants = list(u32_variants(value))
            if name == "file_size":
                variants.extend(u64_variants(value))

            for encoding, needle in variants:
                db_offsets = db_indexes[len(needle)].get(needle, [])
                for db_offset in db_offsets:
                    numeric_hits.append(
                        {
                            "source": relative,
                            "name": name,
                            "value": value,
                            "encoding": encoding,
                            "db_offset": db_offset,
                            "needle_hex": needle.hex(),
                        }
                    )

        digests = {
            "md5": hashlib.md5(data).digest(),
            "sha1": hashlib.sha1(data).digest(),
            "sha256": hashlib.sha256(data).digest(),
        }

        for digest_name, digest in digests.items():
            variants = (
                ("raw", digest),
                ("reversed", digest[::-1]),
                ("hex_lower", digest.hex().encode("ascii")),
                ("hex_upper", digest.hex().upper().encode("ascii")),
            )

            for variant_name, needle in variants:
                for db_offset in all_occurrences(db, needle):
                    digest_hits.append(
                        {
                            "source": relative,
                            "digest": digest_name,
                            "variant": variant_name,
                            "db_offset": db_offset,
                            "needle_hex": needle.hex(),
                        }
                    )

    print()
    print("[3/5] Fragments exacts échantillonnés...")

    for index, path in enumerate(ithmb_files, 1):
        data = path.read_bytes()
        relative = str(path.relative_to(CACHE_ROOT))

        print(f"  [{index:02d}/{len(ithmb_files):02d}] {relative}")

        for size in FRAGMENT_SIZES:
            offsets = sampled_offsets(
                len(data),
                size,
                MAX_FRAGMENT_SAMPLES_PER_FILE_PER_SIZE,
            )

            db_index = db_indexes[size]

            for source_offset in offsets:
                fragment = data[source_offset:source_offset + size]
                for db_offset in db_index.get(fragment, []):
                    fragment_hits.append(
                        {
                            "source": relative,
                            "fragment_size": size,
                            "source_offset": source_offset,
                            "db_offset": db_offset,
                            "fragment_hex": fragment.hex(),
                        }
                    )

    print()
    print("[4/5] Métriques de blocs échantillonnées...")

    value_frequency = Counter()

    for index, path in enumerate(ithmb_files, 1):
        data = path.read_bytes()
        relative = str(path.relative_to(CACHE_ROOT))

        print(f"  [{index:02d}/{len(ithmb_files):02d}] {relative}")

        for block_size in BLOCK_SIZES:
            offsets = sampled_offsets(
                len(data),
                block_size,
                MAX_BLOCKS_PER_FILE_PER_SIZE,
            )

            for source_offset in offsets:
                block = data[source_offset:source_offset + block_size]

                metrics = {
                    "crc32": zlib.crc32(block) & 0xFFFFFFFF,
                    "adler32": zlib.adler32(block) & 0xFFFFFFFF,
                    "sum32": sum(block) & 0xFFFFFFFF,
                }

                for metric, value in metrics.items():
                    value_frequency[(metric, value)] += 1

                    metric_candidates.append(
                        {
                            "source": relative,
                            "block_size": block_size,
                            "source_offset": source_offset,
                            "metric": metric,
                            "value": value,
                        }
                    )

    block_metric_hits = []

    for row in metric_candidates:
        frequency = value_frequency[(row["metric"], row["value"])]

        if frequency > 4:
            continue

        for encoding, needle in u32_variants(row["value"]):
            for db_offset in db_indexes[4].get(needle, []):
                block_metric_hits.append(
                    {
                        **row,
                        "encoding": encoding,
                        "db_offset": db_offset,
                        "needle_hex": needle.hex(),
                        "global_frequency": frequency,
                    }
                )

    print()
    print("[5/5] Écriture des rapports...")

    write_csv(
        OUTPUT_ROOT / "file_numeric_hits.csv",
        numeric_hits,
        ["source", "name", "value", "encoding", "db_offset", "needle_hex"],
    )

    write_csv(
        OUTPUT_ROOT / "digest_hits.csv",
        digest_hits,
        ["source", "digest", "variant", "db_offset", "needle_hex"],
    )

    write_csv(
        OUTPUT_ROOT / "exact_fragment_hits.csv",
        fragment_hits,
        [
            "source",
            "fragment_size",
            "source_offset",
            "db_offset",
            "fragment_hex",
        ],
    )

    write_csv(
        OUTPUT_ROOT / "block_metric_hits.csv",
        block_metric_hits,
        [
            "source",
            "block_size",
            "source_offset",
            "metric",
            "value",
            "encoding",
            "db_offset",
            "needle_hex",
            "global_frequency",
        ],
    )

    summary_path = OUTPUT_ROOT / "summary.txt"

    with summary_path.open("w", encoding="utf-8") as report:
        report.write("=" * 110 + "\n")
        report.write("ITHMB ↔ PHOTO DATABASE LINK PROBE — FAST SUMMARY\n")
        report.write("=" * 110 + "\n\n")
        report.write(f"Photo Database size : {len(db)}\n")
        report.write(f"ITHMB files         : {len(ithmb_files)}\n")
        report.write(f"File numeric hits   : {len(numeric_hits)}\n")
        report.write(f"Digest hits         : {len(digest_hits)}\n")
        report.write(f"Exact fragment hits : {len(fragment_hits)}\n")
        report.write(f"Block metric hits   : {len(block_metric_hits)}\n\n")

        report.write("FILE NUMERIC HITS\n")
        report.write("-" * 110 + "\n")
        for row in numeric_hits[:300]:
            report.write(
                f"{row['source']} | {row['name']}={row['value']} | "
                f"{row['encoding']} | DB=0x{row['db_offset']:08x}\n"
            )

        report.write("\nDIGEST HITS\n")
        report.write("-" * 110 + "\n")
        for row in digest_hits[:300]:
            report.write(
                f"{row['source']} | {row['digest']} | {row['variant']} | "
                f"DB=0x{row['db_offset']:08x}\n"
            )

        report.write("\nEXACT FRAGMENT HITS\n")
        report.write("-" * 110 + "\n")
        for row in fragment_hits[:300]:
            report.write(
                f"{row['source']} | size={row['fragment_size']} | "
                f"source=0x{row['source_offset']:08x} | "
                f"DB=0x{row['db_offset']:08x}\n"
            )

        report.write("\nBLOCK METRIC HITS\n")
        report.write("-" * 110 + "\n")
        for row in block_metric_hits[:500]:
            report.write(
                f"{row['source']} | block={row['block_size']} | "
                f"source=0x{row['source_offset']:08x} | "
                f"{row['metric']}={row['value']} | "
                f"{row['encoding']} | DB=0x{row['db_offset']:08x} | "
                f"freq={row['global_frequency']}\n"
            )

    print()
    print("=" * 110)
    print("RÉSULTATS")
    print("=" * 110)
    print(f"Valeurs de fichiers trouvées : {len(numeric_hits)}")
    print(f"Empreintes complètes trouvées: {len(digest_hits)}")
    print(f"Fragments exacts trouvés     : {len(fragment_hits)}")
    print(f"Métriques de blocs trouvées  : {len(block_metric_hits)}")
    print()
    print(f"Résumé : {summary_path}")
    print()
    print("Commande suivante :")
    print(f"  sed -n '1,320p' {summary_path}")


if __name__ == "__main__":
    main()
