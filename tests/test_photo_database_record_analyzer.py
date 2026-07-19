from __future__ import annotations

import csv
import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/photo_database_record_analyzer")

MIN_RECORD_SIZE = 8
MAX_RECORD_SIZE = 8192
COMMON_LENGTHS = [
    8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64,
    68, 72, 76, 80, 84, 88, 92, 96, 104, 112, 120, 128, 136,
    144, 160, 176, 192, 208, 224, 240, 256, 272, 288, 320,
    336, 352, 384, 416, 448, 480, 512, 544, 576, 640, 768,
    896, 1024, 1084, 2048, 2168, 3252, 4096
]

ASCII_RE = re.compile(rb"[\x20-\x7e]{4,}")
UTF16LE_RE = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")


def find_database() -> Path:
    files = sorted(CACHE_ROOT.rglob("Photo Database"))
    if not files:
        raise FileNotFoundError(f"Photo Database introuvable sous {CACHE_ROOT}")
    return files[0]


def entropy(chunk: bytes) -> float:
    if not chunk:
        return 0.0
    counts = Counter(chunk)
    total = len(chunk)
    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def ascii_ratio(chunk: bytes) -> float:
    if not chunk:
        return 0.0
    good = sum(1 for b in chunk if 32 <= b <= 126 or b in (9, 10, 13))
    return good / len(chunk)


def zero_ratio(chunk: bytes) -> float:
    if not chunk:
        return 0.0
    return chunk.count(0) / len(chunk)


def u16le(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 2:
        return struct.unpack_from("<H", data, offset)[0]
    return None


def u16be(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 2:
        return struct.unpack_from(">H", data, offset)[0]
    return None


def u32le(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 4:
        return struct.unpack_from("<I", data, offset)[0]
    return None


def u32be(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 4:
        return struct.unpack_from(">I", data, offset)[0]
    return None


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def scan_windows(data: bytes, window: int = 256, step: int = 64) -> list[dict]:
    rows = []
    for start in range(0, len(data), step):
        chunk = data[start:start + window]
        if not chunk:
            continue
        rows.append({
            "start_decimal": start,
            "start_hex": f"0x{start:08x}",
            "length": len(chunk),
            "entropy": round(entropy(chunk), 6),
            "ascii_ratio": round(ascii_ratio(chunk), 6),
            "zero_ratio": round(zero_ratio(chunk), 6),
            "unique_bytes": len(set(chunk)),
        })
    return rows


def scan_strings(data: bytes) -> list[dict]:
    rows = []
    for m in ASCII_RE.finditer(data):
        rows.append({
            "offset_decimal": m.start(),
            "offset_hex": f"0x{m.start():08x}",
            "end_decimal": m.end(),
            "length": m.end() - m.start(),
            "encoding": "ascii",
            "value": m.group().decode("ascii", errors="replace"),
        })
    for m in UTF16LE_RE.finditer(data):
        rows.append({
            "offset_decimal": m.start(),
            "offset_hex": f"0x{m.start():08x}",
            "end_decimal": m.end(),
            "length": m.end() - m.start(),
            "encoding": "utf16le",
            "value": m.group().decode("utf-16le", errors="replace"),
        })
    rows.sort(key=lambda r: int(r["offset_decimal"]))
    return rows


def scan_zero_runs(data: bytes, minimum: int = 8) -> list[dict]:
    rows = []
    start = None
    for i, b in enumerate(data):
        if b == 0 and start is None:
            start = i
        elif b != 0 and start is not None:
            length = i - start
            if length >= minimum:
                rows.append({
                    "start_decimal": start,
                    "start_hex": f"0x{start:08x}",
                    "end_decimal": i,
                    "length": length,
                    "alignment_mod4": start % 4,
                    "alignment_mod16": start % 16,
                })
            start = None
    if start is not None:
        length = len(data) - start
        if length >= minimum:
            rows.append({
                "start_decimal": start,
                "start_hex": f"0x{start:08x}",
                "end_decimal": len(data),
                "length": length,
                "alignment_mod4": start % 4,
                "alignment_mod16": start % 16,
            })
    return rows


def repeated_prefixes(data: bytes, width: int, alignment: int = 4) -> list[dict]:
    positions = defaultdict(list)
    for offset in range(0, len(data) - width + 1, alignment):
        positions[data[offset:offset + width]].append(offset)

    rows = []
    for signature, offsets in positions.items():
        if len(offsets) < 3:
            continue
        gaps = [offsets[i] - offsets[i - 1] for i in range(1, len(offsets))]
        gap_counts = Counter(gaps)
        most_gap, most_gap_count = gap_counts.most_common(1)[0]
        rows.append({
            "width": width,
            "signature_hex": signature.hex(" "),
            "count": len(offsets),
            "first_offset": offsets[0],
            "first_offset_hex": f"0x{offsets[0]:08x}",
            "last_offset": offsets[-1],
            "most_common_gap": most_gap,
            "most_common_gap_count": most_gap_count,
            "regularity_percent": round(most_gap_count / len(gaps) * 100, 3),
            "offsets_preview": " ".join(f"0x{x:x}" for x in offsets[:20]),
        })

    rows.sort(key=lambda r: (-int(r["count"]), -float(r["regularity_percent"])))
    return rows


def candidate_length_fields(data: bytes) -> list[dict]:
    rows = []
    readers = [
        ("u16le", 2, u16le),
        ("u16be", 2, u16be),
        ("u32le", 4, u32le),
        ("u32be", 4, u32be),
    ]

    for offset in range(0, len(data) - 4):
        for encoding, width, reader in readers:
            value = reader(data, offset)
            if value is None or not (MIN_RECORD_SIZE <= value <= MAX_RECORD_SIZE):
                continue

            end = offset + value
            if end > len(data):
                continue

            score = 0
            reasons = []

            if offset % width == 0:
                score += 1
                reasons.append("aligned")

            if value in COMMON_LENGTHS:
                score += 2
                reasons.append("common_length")

            # Does another plausible length start exactly at the end?
            next_same = reader(data, end)
            if next_same is not None and MIN_RECORD_SIZE <= next_same <= MAX_RECORD_SIZE:
                score += 3
                reasons.append("next_record_same_encoding")

            # Does the end align well?
            if end % 4 == 0:
                score += 1
                reasons.append("end_mod4")
            if end % 16 == 0:
                score += 1
                reasons.append("end_mod16")

            # Compare rough statistics of this possible record.
            chunk = data[offset:end]
            ent = entropy(chunk)
            zr = zero_ratio(chunk)
            ar = ascii_ratio(chunk)

            if zr >= 0.10:
                score += 1
                reasons.append("contains_zeros")
            if ar >= 0.15:
                score += 1
                reasons.append("contains_text")
            if ent <= 6.5:
                score += 1
                reasons.append("structured_entropy")

            if score >= 5:
                rows.append({
                    "offset_decimal": offset,
                    "offset_hex": f"0x{offset:08x}",
                    "encoding": encoding,
                    "field_width": width,
                    "candidate_length": value,
                    "end_decimal": end,
                    "end_hex": f"0x{end:08x}",
                    "score": score,
                    "reasons": "|".join(reasons),
                    "entropy": round(ent, 6),
                    "zero_ratio": round(zr, 6),
                    "ascii_ratio": round(ar, 6),
                    "next_value_same_encoding": next_same,
                })

    rows.sort(key=lambda r: (-int(r["score"]), int(r["offset_decimal"])))
    return rows


def chain_length_records(data: bytes, candidates: list[dict]) -> list[dict]:
    by_start = defaultdict(list)
    for row in candidates:
        by_start[int(row["offset_decimal"])].append(row)

    chains = []
    visited = set()

    for start in sorted(by_start):
        for seed in by_start[start]:
            key = (start, seed["encoding"], seed["candidate_length"])
            if key in visited:
                continue

            chain = []
            cursor = start
            encoding = str(seed["encoding"])

            while cursor in by_start:
                matching = [
                    x for x in by_start[cursor]
                    if x["encoding"] == encoding
                ]
                if not matching:
                    break

                best = max(matching, key=lambda x: int(x["score"]))
                chain.append(best)
                visited.add((
                    int(best["offset_decimal"]),
                    best["encoding"],
                    best["candidate_length"],
                ))

                next_cursor = int(best["end_decimal"])
                if next_cursor <= cursor:
                    break
                cursor = next_cursor

                if len(chain) >= 1000:
                    break

            if len(chain) >= 2:
                lengths = [int(x["candidate_length"]) for x in chain]
                chains.append({
                    "start_decimal": int(chain[0]["offset_decimal"]),
                    "start_hex": chain[0]["offset_hex"],
                    "end_decimal": int(chain[-1]["end_decimal"]),
                    "end_hex": chain[-1]["end_hex"],
                    "encoding": encoding,
                    "record_count": len(chain),
                    "total_bytes": int(chain[-1]["end_decimal"]) - int(chain[0]["offset_decimal"]),
                    "unique_lengths": len(set(lengths)),
                    "most_common_length": Counter(lengths).most_common(1)[0][0],
                    "lengths_preview": " ".join(map(str, lengths[:50])),
                    "offsets_preview": " ".join(
                        f"0x{int(x['offset_decimal']):x}" for x in chain[:30]
                    ),
                })

    chains.sort(key=lambda r: (-int(r["record_count"]), int(r["start_decimal"])))
    return chains


def scan_pointer_like_values(data: bytes) -> list[dict]:
    rows = []
    size = len(data)

    for encoding, reader in (("u32le", u32le), ("u32be", u32be)):
        values = defaultdict(list)
        for offset in range(0, len(data) - 3, 4):
            value = reader(data, offset)
            if value is not None and 0 <= value < size:
                values[value].append(offset)

        for value, sources in values.items():
            if value == 0:
                continue
            target_chunk = data[value:value + 32]
            rows.append({
                "encoding": encoding,
                "target_decimal": value,
                "target_hex": f"0x{value:08x}",
                "reference_count": len(sources),
                "source_offsets_preview": " ".join(f"0x{x:x}" for x in sources[:20]),
                "target_mod4": value % 4,
                "target_mod16": value % 16,
                "target_entropy_32": round(entropy(target_chunk), 6),
                "target_zero_ratio_32": round(zero_ratio(target_chunk), 6),
                "target_ascii_ratio_32": round(ascii_ratio(target_chunk), 6),
                "target_hex_preview": target_chunk.hex(" "),
            })

    rows.sort(key=lambda r: (-int(r["reference_count"]), int(r["target_decimal"])))
    return rows


def summarize_regions(window_rows: list[dict]) -> list[dict]:
    if not window_rows:
        return []

    labels = []
    for row in window_rows:
        ent = float(row["entropy"])
        ar = float(row["ascii_ratio"])
        zr = float(row["zero_ratio"])

        if zr >= 0.35:
            label = "zero_heavy"
        elif ar >= 0.30 and ent <= 6.8:
            label = "text_or_metadata"
        elif ent >= 7.5:
            label = "high_entropy"
        else:
            label = "mixed"

        labels.append((row, label))

    regions = []
    current_label = labels[0][1]
    start = int(labels[0][0]["start_decimal"])
    current = [labels[0][0]]

    for row, label in labels[1:]:
        if label == current_label:
            current.append(row)
            continue

        regions.append(_region_row(start, current, current_label))
        current_label = label
        start = int(row["start_decimal"])
        current = [row]

    regions.append(_region_row(start, current, current_label))
    return regions


def _region_row(start: int, rows: list[dict], label: str) -> dict:
    end = int(rows[-1]["start_decimal"]) + int(rows[-1]["length"])
    return {
        "start_decimal": start,
        "start_hex": f"0x{start:08x}",
        "end_decimal": end,
        "end_hex": f"0x{end:08x}",
        "length": end - start,
        "classification": label,
        "window_count": len(rows),
        "mean_entropy": round(
            sum(float(x["entropy"]) for x in rows) / len(rows), 6
        ),
        "mean_ascii_ratio": round(
            sum(float(x["ascii_ratio"]) for x in rows) / len(rows), 6
        ),
        "mean_zero_ratio": round(
            sum(float(x["zero_ratio"]) for x in rows) / len(rows), 6
        ),
    }


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    db_path = find_database()
    data = db_path.read_bytes()

    print("=" * 100)
    print("PHOTO DATABASE RECORD ANALYZER")
    print("=" * 100)
    print(f"Fichier : {db_path}")
    print(f"Taille  : {len(data):,} octets")
    print(f"Entropie globale : {entropy(data):.6f}")
    print(f"Ratio ASCII      : {ascii_ratio(data):.6f}")
    print(f"Ratio zéros      : {zero_ratio(data):.6f}")
    print()

    print("[1/8] Analyse des fenêtres...")
    windows = scan_windows(data)
    write_csv(OUTPUT_ROOT / "window_statistics.csv", windows)

    print("[2/8] Classification des régions...")
    regions = summarize_regions(windows)
    write_csv(OUTPUT_ROOT / "regions.csv", regions)

    print("[3/8] Extraction des chaînes...")
    strings = scan_strings(data)
    write_csv(OUTPUT_ROOT / "strings.csv", strings)

    print("[4/8] Recherche des séries de zéros...")
    zero_runs = scan_zero_runs(data)
    write_csv(OUTPUT_ROOT / "zero_runs.csv", zero_runs)

    print("[5/8] Recherche de signatures répétées...")
    repeated = []
    for width in (4, 8, 12, 16):
        repeated.extend(repeated_prefixes(data, width, alignment=4))
    repeated.sort(key=lambda r: (-int(r["count"]), int(r["width"])))
    write_csv(OUTPUT_ROOT / "repeated_signatures.csv", repeated)

    print("[6/8] Recherche de champs de longueur possibles...")
    length_candidates = candidate_length_fields(data)
    write_csv(OUTPUT_ROOT / "candidate_length_fields.csv", length_candidates)

    print("[7/8] Construction de chaînes de records...")
    chains = chain_length_records(data, length_candidates)
    write_csv(OUTPUT_ROOT / "record_chains.csv", chains)

    print("[8/8] Recherche de pointeurs/offsets possibles...")
    pointers = scan_pointer_like_values(data)
    write_csv(OUTPUT_ROOT / "pointer_candidates.csv", pointers)

    print()
    print("=" * 100)
    print("RÉGIONS PRINCIPALES")
    print("=" * 100)
    print(
        f"{'début':>10} {'fin':>10} {'taille':>9} "
        f"{'classe':>18} {'entropie':>10} {'ascii':>9} {'zéros':>9}"
    )
    for row in regions[:80]:
        print(
            f"{row['start_hex']:>10} {row['end_hex']:>10} "
            f"{int(row['length']):9d} {row['classification']:>18} "
            f"{float(row['mean_entropy']):10.4f} "
            f"{float(row['mean_ascii_ratio']):9.4f} "
            f"{float(row['mean_zero_ratio']):9.4f}"
        )

    print()
    print("=" * 100)
    print("MEILLEURES CHAÎNES DE RECORDS CANDIDATES")
    print("=" * 100)
    if not chains:
        print("Aucune chaîne cohérente de records trouvée.")
    else:
        print(
            f"{'début':>10} {'fin':>10} {'enc':>7} {'records':>8} "
            f"{'octets':>10} {'longueur dominante':>19}"
        )
        for row in chains[:50]:
            print(
                f"{row['start_hex']:>10} {row['end_hex']:>10} "
                f"{row['encoding']:>7} {int(row['record_count']):8d} "
                f"{int(row['total_bytes']):10d} "
                f"{int(row['most_common_length']):19d}"
            )

    print()
    print("=" * 100)
    print("SIGNATURES RÉPÉTÉES LES PLUS FORTES")
    print("=" * 100)
    print(
        f"{'largeur':>7} {'compte':>8} {'gap':>10} "
        f"{'régularité':>11} {'signature'}"
    )
    for row in repeated[:50]:
        print(
            f"{int(row['width']):7d} {int(row['count']):8d} "
            f"{int(row['most_common_gap']):10d} "
            f"{float(row['regularity_percent']):10.2f}% "
            f"{row['signature_hex']}"
        )

    print()
    print("=" * 100)
    print("POINTEURS CANDIDATS LES PLUS RÉFÉRENCÉS")
    print("=" * 100)
    print(
        f"{'enc':>7} {'cible':>10} {'références':>11} "
        f"{'mod4':>5} {'entropie32':>11} {'ascii32':>9}"
    )
    for row in pointers[:50]:
        print(
            f"{row['encoding']:>7} {row['target_hex']:>10} "
            f"{int(row['reference_count']):11d} "
            f"{int(row['target_mod4']):5d} "
            f"{float(row['target_entropy_32']):11.4f} "
            f"{float(row['target_ascii_ratio_32']):9.4f}"
        )

    print()
    print("=" * 100)
    print("TERMINÉ")
    print("=" * 100)
    print(f"Dossier : {OUTPUT_ROOT}")
    print()
    print("Fichiers prioritaires :")
    print(f"  {OUTPUT_ROOT}/regions.csv")
    print(f"  {OUTPUT_ROOT}/record_chains.csv")
    print(f"  {OUTPUT_ROOT}/repeated_signatures.csv")
    print(f"  {OUTPUT_ROOT}/candidate_length_fields.csv")
    print(f"  {OUTPUT_ROOT}/pointer_candidates.csv")
    print(f"  {OUTPUT_ROOT}/strings.csv")


if __name__ == "__main__":
    main()
