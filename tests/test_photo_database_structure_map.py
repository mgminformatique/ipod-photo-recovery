from __future__ import annotations

import csv
import math
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/photo_database_structure_map")

VALUES = [180, 360, 540, 544, 1080, 1084, 2168, 3252]
CONTEXT_RADIUS = 96
MAX_STRING_DISTANCE = 256

ITHMB_PATTERN = re.compile(rb"T\d{3}\.ithmb", re.IGNORECASE)
PRINTABLE_PATTERN = re.compile(rb"[\x20-\x7e]{4,}")
UTF16LE_PATTERN = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")


def find_photo_database() -> Path:
    candidates = sorted(CACHE_ROOT.rglob("Photo Database"))
    if not candidates:
        raise FileNotFoundError(
            f"Photo Database introuvable sous {CACHE_ROOT}"
        )
    return candidates[0]


def read_u16le(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 2:
        return struct.unpack_from("<H", data, offset)[0]
    return None


def read_u16be(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 2:
        return struct.unpack_from(">H", data, offset)[0]
    return None


def read_u32le(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 4:
        return struct.unpack_from("<I", data, offset)[0]
    return None


def read_u32be(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 4:
        return struct.unpack_from(">I", data, offset)[0]
    return None


def read_s32le(data: bytes, offset: int) -> int | None:
    if 0 <= offset <= len(data) - 4:
        return struct.unpack_from("<i", data, offset)[0]
    return None


def ascii_preview(chunk: bytes) -> str:
    return "".join(
        chr(byte) if 32 <= byte <= 126 else "."
        for byte in chunk
    )


def hexdump(data: bytes, start: int, end: int) -> str:
    lines = []
    cursor = max(0, start)
    end = min(len(data), end)

    while cursor < end:
        row = data[cursor : cursor + 16]
        hex_part = " ".join(f"{byte:02x}" for byte in row)
        hex_part = f"{hex_part:<47}"
        lines.append(
            f"{cursor:08x}  {hex_part}  |{ascii_preview(row)}|"
        )
        cursor += 16

    return "\n".join(lines)


def find_all(data: bytes, needle: bytes) -> list[int]:
    offsets = []
    cursor = 0

    while True:
        offset = data.find(needle, cursor)
        if offset < 0:
            break
        offsets.append(offset)
        cursor = offset + 1

    return offsets


def discover_strings(data: bytes) -> list[dict[str, object]]:
    strings = []

    for match in PRINTABLE_PATTERN.finditer(data):
        value = match.group().decode("ascii", errors="replace")
        strings.append(
            {
                "offset": match.start(),
                "end": match.end(),
                "encoding": "ascii",
                "value": value,
            }
        )

    for match in UTF16LE_PATTERN.finditer(data):
        value = match.group().decode("utf-16le", errors="replace")
        strings.append(
            {
                "offset": match.start(),
                "end": match.end(),
                "encoding": "utf16le",
                "value": value,
            }
        )

    strings.sort(key=lambda item: int(item["offset"]))
    return strings


def nearest_strings(
    strings: list[dict[str, object]],
    offset: int,
    max_distance: int = MAX_STRING_DISTANCE,
) -> list[dict[str, object]]:
    candidates = []

    for item in strings:
        item_start = int(item["offset"])
        item_end = int(item["end"])

        if item_start <= offset <= item_end:
            distance = 0
        else:
            distance = min(abs(offset - item_start), abs(offset - item_end))

        if distance <= max_distance:
            candidates.append({**item, "distance": distance})

    candidates.sort(
        key=lambda item: (
            int(item["distance"]),
            abs(int(item["offset"]) - offset),
        )
    )

    return candidates[:8]


def local_numeric_window(data: bytes, offset: int) -> list[dict[str, object]]:
    rows = []

    for relative in range(-32, 33, 2):
        absolute = offset + relative

        if absolute < 0 or absolute >= len(data):
            continue

        rows.append(
            {
                "relative": relative,
                "absolute": absolute,
                "u16le": read_u16le(data, absolute),
                "u16be": read_u16be(data, absolute),
                "u32le": read_u32le(data, absolute),
                "u32be": read_u32be(data, absolute),
                "s32le": read_s32le(data, absolute),
            }
        )

    return rows


def score_possible_offset(value: int | None, file_size: int) -> bool:
    if value is None:
        return False
    return 0 <= value < file_size


def score_possible_dimension(value: int | None) -> bool:
    if value is None:
        return False
    return 1 <= value <= 10000


def score_possible_file_size(value: int | None) -> bool:
    if value is None:
        return False
    return 1024 <= value <= 100_000_000


def inspect_hit(
    data: bytes,
    strings: list[dict[str, object]],
    value: int,
    encoding: str,
    width: int,
    offset: int,
    hit_index: int,
) -> dict[str, object]:
    nearby = nearest_strings(strings, offset)
    nearest_text = " || ".join(
        f"{item['encoding']}@0x{int(item['offset']):x}:"
        f"{item['value']}"
        for item in nearby
    )

    ithmb_nearby = [
        item for item in nearby
        if re.search(r"T\d{3}\.ithmb", str(item["value"]), re.IGNORECASE)
    ]

    window = local_numeric_window(data, offset)

    plausible_offsets = []
    plausible_dimensions = []
    plausible_sizes = []

    for item in window:
        for key in ("u16le", "u16be", "u32le", "u32be"):
            candidate = item[key]
            label = f"{int(item['relative']):+d}:{key}={candidate}"

            if score_possible_offset(candidate, len(data)):
                plausible_offsets.append(label)

            if score_possible_dimension(candidate):
                plausible_dimensions.append(label)

            if score_possible_file_size(candidate):
                plausible_sizes.append(label)

    context_start = max(0, offset - CONTEXT_RADIUS)
    context_end = min(len(data), offset + width + CONTEXT_RADIUS)

    return {
        "hit_index": hit_index,
        "value": value,
        "encoding": encoding,
        "width": width,
        "offset_decimal": offset,
        "offset_hex": f"0x{offset:08x}",
        "offset_mod_2": offset % 2,
        "offset_mod_4": offset % 4,
        "offset_mod_8": offset % 8,
        "offset_mod_16": offset % 16,
        "nearest_strings": nearest_text,
        "near_ithmb_reference": (
            " || ".join(str(item["value"]) for item in ithmb_nearby)
        ),
        "plausible_offsets": " | ".join(plausible_offsets[:20]),
        "plausible_dimensions": " | ".join(plausible_dimensions[:20]),
        "plausible_sizes": " | ".join(plausible_sizes[:20]),
        "context_hex": data[context_start:context_end].hex(" "),
        "context_ascii": ascii_preview(data[context_start:context_end]),
    }


def build_hit_report(
    data: bytes,
    strings: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    hit_index = 0

    encoders = [
        ("u16le", 2, lambda value: struct.pack("<H", value)),
        ("u16be", 2, lambda value: struct.pack(">H", value)),
        ("u32le", 4, lambda value: struct.pack("<I", value)),
        ("u32be", 4, lambda value: struct.pack(">I", value)),
    ]

    for value in VALUES:
        for encoding, width, encoder in encoders:
            needle = encoder(value)

            for offset in find_all(data, needle):
                hit_index += 1
                rows.append(
                    inspect_hit(
                        data,
                        strings,
                        value,
                        encoding,
                        width,
                        offset,
                        hit_index,
                    )
                )

    rows.sort(
        key=lambda row: (
            int(row["offset_decimal"]),
            int(row["width"]),
            str(row["encoding"]),
            int(row["value"]),
        )
    )

    for index, row in enumerate(rows, start=1):
        row["sorted_index"] = index
        previous_offset = (
            int(rows[index - 2]["offset_decimal"])
            if index > 1
            else None
        )
        next_offset = (
            int(rows[index]["offset_decimal"])
            if index < len(rows)
            else None
        )
        current = int(row["offset_decimal"])

        row["distance_from_previous_hit"] = (
            current - previous_offset if previous_offset is not None else ""
        )
        row["distance_to_next_hit"] = (
            next_offset - current if next_offset is not None else ""
        )

    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_strings_csv(
    path: Path,
    strings: list[dict[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["offset", "offset_hex", "end", "encoding", "value"],
        )
        writer.writeheader()

        for item in strings:
            writer.writerow(
                {
                    **item,
                    "offset_hex": f"0x{int(item['offset']):08x}",
                }
            )


def write_individual_reports(
    data: bytes,
    rows: list[dict[str, object]],
) -> None:
    reports_dir = OUTPUT_ROOT / "hit_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        index = int(row["sorted_index"])
        offset = int(row["offset_decimal"])
        width = int(row["width"])
        value = int(row["value"])
        encoding = str(row["encoding"])

        start = max(0, offset - 128)
        end = min(len(data), offset + width + 128)

        numeric_rows = local_numeric_window(data, offset)

        lines = [
            "=" * 96,
            f"HIT #{index}",
            "=" * 96,
            f"Valeur          : {value}",
            f"Encodage        : {encoding}",
            f"Offset décimal  : {offset}",
            f"Offset hex      : 0x{offset:08x}",
            f"Alignement      : mod2={offset % 2}, mod4={offset % 4}, "
            f"mod8={offset % 8}, mod16={offset % 16}",
            f"Hit précédent   : {row['distance_from_previous_hit']}",
            f"Hit suivant     : {row['distance_to_next_hit']}",
            "",
            "Chaînes proches :",
            str(row["nearest_strings"]) or "(aucune)",
            "",
            "Référence ITHMB proche :",
            str(row["near_ithmb_reference"]) or "(aucune)",
            "",
            "Valeurs numériques autour du hit :",
            "",
            (
                f"{'rel':>5} {'offset':>10} {'u16le':>8} {'u16be':>8} "
                f"{'u32le':>12} {'u32be':>12} {'s32le':>12}"
            ),
        ]

        for item in numeric_rows:
            lines.append(
                f"{int(item['relative']):5d} "
                f"0x{int(item['absolute']):08x} "
                f"{str(item['u16le']):>8} "
                f"{str(item['u16be']):>8} "
                f"{str(item['u32le']):>12} "
                f"{str(item['u32be']):>12} "
                f"{str(item['s32le']):>12}"
            )

        lines.extend(
            [
                "",
                "Hexdump ±128 octets :",
                "",
                hexdump(data, start, end),
                "",
            ]
        )

        filename = (
            f"{index:03d}_offset_{offset:08x}_{value}_{encoding}.txt"
        )
        (reports_dir / filename).write_text(
            "\n".join(lines),
            encoding="utf-8",
        )


def detect_repeated_distances(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_signature: dict[tuple[int, str], list[int]] = defaultdict(list)

    for row in rows:
        signature = (int(row["value"]), str(row["encoding"]))
        by_signature[signature].append(int(row["offset_decimal"]))

    output_rows = []

    for (value, encoding), offsets in sorted(by_signature.items()):
        if len(offsets) < 2:
            continue

        distances = [
            offsets[index] - offsets[index - 1]
            for index in range(1, len(offsets))
        ]

        counts = Counter(distances)

        for distance, count in counts.most_common():
            output_rows.append(
                {
                    "value": value,
                    "encoding": encoding,
                    "distance": distance,
                    "count": count,
                    "percent_of_gaps": (
                        count / len(distances) * 100.0
                    ),
                    "is_known_candidate": distance in VALUES,
                    "multiple_of_4": distance % 4 == 0,
                    "multiple_of_544": distance % 544 == 0,
                    "multiple_of_1084": distance % 1084 == 0,
                }
            )

    output_rows.sort(
        key=lambda row: (
            -int(row["count"]),
            int(row["distance"]),
        )
    )

    return output_rows


def scan_ithmb_references(
    data: bytes,
    strings: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []

    for match in ITHMB_PATTERN.finditer(data):
        offset = match.start()
        name = match.group().decode("ascii", errors="replace")
        rows.append(
            {
                "offset_decimal": offset,
                "offset_hex": f"0x{offset:08x}",
                "name": name,
                "nearby_hex": data[
                    max(0, offset - 64):
                    min(len(data), match.end() + 64)
                ].hex(" "),
                "nearby_ascii": ascii_preview(
                    data[
                        max(0, offset - 64):
                        min(len(data), match.end() + 64)
                    ]
                ),
            }
        )

    # Also retain decoded strings that mention .ithmb.
    known = {(row["offset_decimal"], row["name"]) for row in rows}

    for item in strings:
        value = str(item["value"])
        if ".ithmb" not in value.lower():
            continue

        key = (int(item["offset"]), value)
        if key in known:
            continue

        rows.append(
            {
                "offset_decimal": int(item["offset"]),
                "offset_hex": f"0x{int(item['offset']):08x}",
                "name": value,
                "nearby_hex": data[
                    max(0, int(item["offset"]) - 64):
                    min(len(data), int(item["end"]) + 64)
                ].hex(" "),
                "nearby_ascii": ascii_preview(
                    data[
                        max(0, int(item["offset"]) - 64):
                        min(len(data), int(item["end"]) + 64)
                    ]
                ),
            }
        )

    rows.sort(key=lambda row: int(row["offset_decimal"]))
    return rows


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    database_path = find_photo_database()
    data = database_path.read_bytes()

    print("=" * 96)
    print("PHOTO DATABASE STRUCTURE MAP")
    print("=" * 96)
    print(f"Fichier : {database_path}")
    print(f"Taille  : {len(data):,} octets")
    print()

    strings = discover_strings(data)
    print(f"Chaînes détectées : {len(strings):,}")

    rows = build_hit_report(data, strings)
    print(f"Occurrences numériques : {len(rows):,}")

    ithmb_rows = scan_ithmb_references(data, strings)
    print(f"Références .ithmb : {len(ithmb_rows):,}")

    repeated_distances = detect_repeated_distances(rows)

    write_csv(OUTPUT_ROOT / "all_value_hits.csv", rows)
    write_strings_csv(OUTPUT_ROOT / "all_strings.csv", strings)
    write_csv(OUTPUT_ROOT / "ithmb_references.csv", ithmb_rows)
    write_csv(
        OUTPUT_ROOT / "repeated_hit_distances.csv",
        repeated_distances,
    )
    write_individual_reports(data, rows)

    print()
    print("=" * 96)
    print("RÉSUMÉ DES HITS")
    print("=" * 96)
    print(
        f"{'#':>3} {'offset':>10} {'valeur':>8} {'enc':>7} "
        f"{'mod4':>5} {'avant':>8} {'après':>8} {'ITHMB proche'}"
    )

    for row in rows:
        print(
            f"{int(row['sorted_index']):3d} "
            f"{str(row['offset_hex']):>10} "
            f"{int(row['value']):8d} "
            f"{str(row['encoding']):>7} "
            f"{int(row['offset_mod_4']):5d} "
            f"{str(row['distance_from_previous_hit']):>8} "
            f"{str(row['distance_to_next_hit']):>8} "
            f"{str(row['near_ithmb_reference'])[:40]}"
        )

    print()
    print("=" * 96)
    print("DISTANCES RÉPÉTÉES LES PLUS FRÉQUENTES")
    print("=" * 96)
    print(
        f"{'valeur':>8} {'enc':>7} {'distance':>10} "
        f"{'compte':>8} {'%':>8} {'×544':>6} {'×1084':>7}"
    )

    for row in repeated_distances[:30]:
        print(
            f"{int(row['value']):8d} "
            f"{str(row['encoding']):>7} "
            f"{int(row['distance']):10d} "
            f"{int(row['count']):8d} "
            f"{float(row['percent_of_gaps']):8.2f} "
            f"{str(row['multiple_of_544']):>6} "
            f"{str(row['multiple_of_1084']):>7}"
        )

    print()
    print("=" * 96)
    print("TERMINÉ")
    print("=" * 96)
    print(f"Dossier principal : {OUTPUT_ROOT}")
    print()
    print("Fichiers à examiner en priorité :")
    print(f"  {OUTPUT_ROOT}/all_value_hits.csv")
    print(f"  {OUTPUT_ROOT}/ithmb_references.csv")
    print(f"  {OUTPUT_ROOT}/repeated_hit_distances.csv")
    print(f"  {OUTPUT_ROOT}/hit_reports/")


if __name__ == "__main__":
    main()
