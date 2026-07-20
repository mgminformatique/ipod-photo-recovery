from __future__ import annotations

import hashlib
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/ithmb_database_link_probe")

BLOCK_SIZES = (16, 24, 32, 64, 128, 256, 512, 1024)
MAX_BLOCKS_PER_FILE_PER_SIZE = 2000
EXACT_FRAGMENT_SIZES = (8, 12, 16, 24, 32)


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


def all_occurrences(data: bytes, needle: bytes, max_hits: int = 100) -> list[int]:
    if not needle:
        return []

    hits = []
    start = 0
    while len(hits) < max_hits:
        pos = data.find(needle, start)
        if pos < 0:
            break
        hits.append(pos)
        start = pos + 1
    return hits


def encode_u32(value: int) -> dict[str, bytes]:
    value &= 0xFFFFFFFF
    return {
        "u32le": struct.pack("<I", value),
        "u32be": struct.pack(">I", value),
    }


def encode_u64(value: int) -> dict[str, bytes]:
    value &= 0xFFFFFFFFFFFFFFFF
    return {
        "u64le": struct.pack("<Q", value),
        "u64be": struct.pack(">Q", value),
    }


def xor8(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def sum8(data: bytes) -> int:
    return sum(data) & 0xFF


def sum16(data: bytes) -> int:
    return sum(data) & 0xFFFF


def sum32(data: bytes) -> int:
    return sum(data) & 0xFFFFFFFF


def sampled_offsets(length: int, block_size: int, limit: int) -> list[int]:
    count = max(0, (length - block_size) // block_size + 1)
    if count <= limit:
        return [i * block_size for i in range(count)]

    offsets = set()

    # Beginning and end.
    edge = min(200, count)
    for i in range(edge):
        offsets.add(i * block_size)
        offsets.add((count - 1 - i) * block_size)

    # Evenly distributed samples.
    remaining = max(1, limit - len(offsets))
    for i in range(remaining):
        index = round(i * (count - 1) / max(remaining - 1, 1))
        offsets.add(index * block_size)

    return sorted(offsets)[:limit]


def search_numeric_value(
    db_data: bytes,
    source_file: Path,
    category: str,
    name: str,
    value: int,
    width: int,
    output_rows: list[dict],
) -> None:
    encodings = encode_u32(value) if width == 32 else encode_u64(value)

    for endian, encoded in encodings.items():
        hits = all_occurrences(db_data, encoded)
        for db_offset in hits:
            output_rows.append(
                {
                    "source": str(source_file.relative_to(CACHE_ROOT)),
                    "category": category,
                    "name": name,
                    "value": value,
                    "encoding": endian,
                    "db_offset": db_offset,
                    "needle_hex": encoded.hex(),
                }
            )


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    db_path = find_database()
    db_data = db_path.read_bytes()
    ithmb_files = find_ithmb_files()

    print("=" * 110)
    print("ITHMB ↔ PHOTO DATABASE LINK PROBE")
    print("=" * 110)
    print(f"Photo Database : {db_path}")
    print(f"Taille DB      : {len(db_data):,}")
    print(f"Fichiers ITHMB : {len(ithmb_files)}")
    print()

    numeric_hits = []
    digest_hits = []
    fragment_hits = []
    block_metric_hits = []

    print("[1/5] Recherche des tailles et empreintes de fichiers...")

    for index, path in enumerate(ithmb_files, 1):
        data = path.read_bytes()
        relative = path.relative_to(CACHE_ROOT)

        print(f"  [{index:02d}/{len(ithmb_files):02d}] {relative} ({len(data):,} octets)")

        search_numeric_value(
            db_data, path, "file", "file_size", len(data), 32, numeric_hits
        )
        search_numeric_value(
            db_data, path, "file", "file_size", len(data), 64, numeric_hits
        )

        crc = zlib.crc32(data) & 0xFFFFFFFF
        adler = zlib.adler32(data) & 0xFFFFFFFF

        search_numeric_value(
            db_data, path, "file", "crc32", crc, 32, numeric_hits
        )
        search_numeric_value(
            db_data, path, "file", "adler32", adler, 32, numeric_hits
        )

        digests = {
            "md5": hashlib.md5(data).digest(),
            "sha1": hashlib.sha1(data).digest(),
            "sha256": hashlib.sha256(data).digest(),
        }

        for digest_name, digest in digests.items():
            for variant_name, needle in (
                ("raw", digest),
                ("reversed", digest[::-1]),
                ("hex_ascii_lower", digest.hex().encode("ascii")),
                ("hex_ascii_upper", digest.hex().upper().encode("ascii")),
            ):
                hits = all_occurrences(db_data, needle)
                for db_offset in hits:
                    digest_hits.append(
                        {
                            "source": str(relative),
                            "digest": digest_name,
                            "variant": variant_name,
                            "db_offset": db_offset,
                            "needle_hex": needle.hex(),
                        }
                    )

    print()
    print("[2/5] Recherche de fragments exacts...")

    for path in ithmb_files:
        data = path.read_bytes()
        relative = path.relative_to(CACHE_ROOT)

        for fragment_size in EXACT_FRAGMENT_SIZES:
            offsets = sampled_offsets(
                len(data), fragment_size, MAX_BLOCKS_PER_FILE_PER_SIZE
            )

            for source_offset in offsets:
                fragment = data[source_offset:source_offset + fragment_size]
                if len(fragment) != fragment_size:
                    continue

                hits = all_occurrences(db_data, fragment)
                for db_offset in hits:
                    fragment_hits.append(
                        {
                            "source": str(relative),
                            "fragment_size": fragment_size,
                            "source_offset": source_offset,
                            "db_offset": db_offset,
                            "fragment_hex": fragment.hex(),
                        }
                    )

    print()
    print("[3/5] Recherche des métriques de blocs...")

    value_frequency = Counter()

    for path in ithmb_files:
        data = path.read_bytes()
        relative = path.relative_to(CACHE_ROOT)

        for block_size in BLOCK_SIZES:
            offsets = sampled_offsets(
                len(data), block_size, MAX_BLOCKS_PER_FILE_PER_SIZE
            )

            for source_offset in offsets:
                block = data[source_offset:source_offset + block_size]
                if len(block) != block_size:
                    continue

                metrics = {
                    "crc32": zlib.crc32(block) & 0xFFFFFFFF,
                    "adler32": zlib.adler32(block) & 0xFFFFFFFF,
                    "sum32": sum32(block),
                }

                for metric_name, value in metrics.items():
                    value_frequency[(metric_name, value)] += 1

                    for endian, encoded in encode_u32(value).items():
                        hits = all_occurrences(db_data, encoded)
                        for db_offset in hits:
                            block_metric_hits.append(
                                {
                                    "source": str(relative),
                                    "block_size": block_size,
                                    "source_offset": source_offset,
                                    "metric": metric_name,
                                    "value": value,
                                    "encoding": endian,
                                    "db_offset": db_offset,
                                    "needle_hex": encoded.hex(),
                                }
                            )

    print()
    print("[4/5] Filtrage statistique des collisions...")

    # Frequent values are less meaningful and likely accidental.
    filtered_block_hits = []
    for row in block_metric_hits:
        frequency = value_frequency[(row["metric"], row["value"])]
        row["global_frequency"] = frequency
        if frequency <= 4:
            filtered_block_hits.append(row)

    print()
    print("[5/5] Écriture des rapports...")

    write_csv(
        OUTPUT_ROOT / "file_numeric_hits.csv",
        numeric_hits,
        [
            "source",
            "category",
            "name",
            "value",
            "encoding",
            "db_offset",
            "needle_hex",
        ],
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
        OUTPUT_ROOT / "block_metric_hits_all.csv",
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

    write_csv(
        OUTPUT_ROOT / "block_metric_hits_filtered.csv",
        filtered_block_hits,
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
        report.write("ITHMB ↔ PHOTO DATABASE LINK PROBE SUMMARY\n")
        report.write("=" * 110 + "\n\n")
        report.write(f"Photo Database size     : {len(db_data)}\n")
        report.write(f"ITHMB files             : {len(ithmb_files)}\n")
        report.write(f"File numeric hits       : {len(numeric_hits)}\n")
        report.write(f"Digest hits             : {len(digest_hits)}\n")
        report.write(f"Exact fragment hits     : {len(fragment_hits)}\n")
        report.write(f"Block metric hits all   : {len(block_metric_hits)}\n")
        report.write(f"Block metric hits unique: {len(filtered_block_hits)}\n\n")

        report.write("FILE NUMERIC HITS\n")
        report.write("-" * 110 + "\n")
        for row in numeric_hits[:200]:
            report.write(
                f"{row['source']} | {row['name']}={row['value']} | "
                f"{row['encoding']} | DB 0x{row['db_offset']:08x}\n"
            )

        report.write("\nDIGEST HITS\n")
        report.write("-" * 110 + "\n")
        for row in digest_hits[:200]:
            report.write(
                f"{row['source']} | {row['digest']} | {row['variant']} | "
                f"DB 0x{row['db_offset']:08x}\n"
            )

        report.write("\nEXACT FRAGMENT HITS\n")
        report.write("-" * 110 + "\n")
        for row in fragment_hits[:200]:
            report.write(
                f"{row['source']} | size={row['fragment_size']} | "
                f"source=0x{row['source_offset']:08x} | "
                f"DB=0x{row['db_offset']:08x}\n"
            )

        report.write("\nFILTERED BLOCK METRIC HITS\n")
        report.write("-" * 110 + "\n")
        for row in filtered_block_hits[:500]:
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
    print(f"Métriques filtrées           : {len(filtered_block_hits)}")
    print()
    print(f"Résumé : {summary_path}")
    print()
    print("Commande suivante :")
    print(f"  sed -n '1,320p' {summary_path}")


if __name__ == "__main__":
    main()
