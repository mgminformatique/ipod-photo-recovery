from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import csv
import math
import re
import struct


ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/photo_database_refs")
OUT.mkdir(parents=True, exist_ok=True)

TILE_MIN = 102
TILE_MAX = 174


def find_photo_database() -> Path:
    candidates = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name.lower().replace("_", " ") == "photo database"
    ]

    if not candidates:
        candidates = [
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and "photo" in path.name.lower()
            and "database" in path.name.lower()
        ]

    if not candidates:
        raise FileNotFoundError(
            f"Aucun fichier Photo Database trouvé sous {ROOT}"
        )

    candidates.sort(
        key=lambda path: (
            path.name.lower() != "photo database",
            -path.stat().st_size,
        )
    )

    return candidates[0]


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def ascii_strings(
    data: bytes,
    minimum_length: int = 4,
):
    pattern = re.compile(
        rb"[\x20-\x7e]{"
        + str(minimum_length).encode()
        + rb",}"
    )

    for match in pattern.finditer(data):
        yield (
            match.start(),
            match.group().decode(
                "ascii",
                errors="replace",
            ),
        )


def utf16le_strings(
    data: bytes,
    minimum_characters: int = 4,
):
    pattern = re.compile(
        rb"(?:[\x20-\x7e]\x00){"
        + str(minimum_characters).encode()
        + rb",}"
    )

    for match in pattern.finditer(data):
        yield (
            match.start(),
            match.group().decode(
                "utf-16le",
                errors="replace",
            ),
        )


def context_hex(
    data: bytes,
    offset: int,
    radius: int = 24,
) -> str:
    start = max(0, offset - radius)
    end = min(len(data), offset + radius)

    return data[start:end].hex(" ")


def scan_integer_references(data: bytes):
    rows = []

    formats = [
        ("u16le", 2, "<H"),
        ("u16be", 2, ">H"),
        ("u32le", 4, "<I"),
        ("u32be", 4, ">I"),
    ]

    for encoding, width, fmt in formats:
        for offset in range(0, len(data) - width + 1):
            value = struct.unpack_from(
                fmt,
                data,
                offset,
            )[0]

            if TILE_MIN <= value <= TILE_MAX:
                rows.append({
                    "offset": offset,
                    "encoding": encoding,
                    "width": width,
                    "value": value,
                    "alignment_2": offset % 2,
                    "alignment_4": offset % 4,
                    "alignment_8": offset % 8,
                    "alignment_12": offset % 12,
                    "alignment_16": offset % 16,
                    "alignment_24": offset % 24,
                    "context_hex": context_hex(
                        data,
                        offset,
                    ),
                })

    return rows


def scan_text_references(data: bytes):
    rows = []

    for tile_id in range(TILE_MIN, TILE_MAX + 1):
        patterns = [
            (
                "ascii_T",
                f"T{tile_id}".encode("ascii"),
            ),
            (
                "ascii_number",
                str(tile_id).encode("ascii"),
            ),
            (
                "utf16le_T",
                f"T{tile_id}".encode("utf-16le"),
            ),
        ]

        for pattern_type, pattern in patterns:
            start = 0

            while True:
                offset = data.find(pattern, start)

                if offset < 0:
                    break

                rows.append({
                    "offset": offset,
                    "pattern_type": pattern_type,
                    "tile_id": tile_id,
                    "pattern_hex": pattern.hex(" "),
                    "context_hex": context_hex(
                        data,
                        offset,
                        40,
                    ),
                })

                start = offset + 1

    return rows


def analyze_spacing(rows):
    grouped = defaultdict(list)

    for row in rows:
        grouped[
            (
                row["encoding"],
                row["value"],
            )
        ].append(row["offset"])

    spacing_counts = Counter()

    for offsets in grouped.values():
        offsets.sort()

        for left, right in zip(
            offsets,
            offsets[1:],
        ):
            spacing = right - left

            if 0 < spacing <= 4096:
                spacing_counts[spacing] += 1

    return spacing_counts


def write_csv(
    path: Path,
    rows: list[dict],
    fieldnames: list[str],
):
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    database = find_photo_database()
    data = database.read_bytes()

    print("=" * 120)
    print("ANALYSE DES RÉFÉRENCES DANS PHOTO DATABASE")
    print("=" * 120)
    print(f"Fichier : {database}")
    print(f"Taille  : {len(data)} octets")
    print(f"Entropie: {entropy(data):.4f}")
    print()

    ascii_rows = [
        {
            "offset": offset,
            "type": "ascii",
            "text": text,
        }
        for offset, text in ascii_strings(data)
    ]

    utf16_rows = [
        {
            "offset": offset,
            "type": "utf16le",
            "text": text,
        }
        for offset, text in utf16le_strings(data)
    ]

    string_rows = sorted(
        ascii_rows + utf16_rows,
        key=lambda row: (
            row["offset"],
            row["type"],
        ),
    )

    integer_rows = scan_integer_references(data)
    text_reference_rows = scan_text_references(data)

    spacing_counts = analyze_spacing(integer_rows)

    write_csv(
        OUT / "strings.csv",
        string_rows,
        [
            "offset",
            "type",
            "text",
        ],
    )

    write_csv(
        OUT / "integer_tile_references.csv",
        integer_rows,
        [
            "offset",
            "encoding",
            "width",
            "value",
            "alignment_2",
            "alignment_4",
            "alignment_8",
            "alignment_12",
            "alignment_16",
            "alignment_24",
            "context_hex",
        ],
    )

    write_csv(
        OUT / "text_tile_references.csv",
        text_reference_rows,
        [
            "offset",
            "pattern_type",
            "tile_id",
            "pattern_hex",
            "context_hex",
        ],
    )

    encoding_counts = Counter(
        row["encoding"]
        for row in integer_rows
    )

    value_counts = Counter(
        (
            row["encoding"],
            row["value"],
        )
        for row in integer_rows
    )

    aligned_counts = Counter()

    for row in integer_rows:
        for alignment in (
            2,
            4,
            8,
            12,
            16,
            24,
        ):
            if row[f"alignment_{alignment}"] == 0:
                aligned_counts[
                    (
                        row["encoding"],
                        alignment,
                    )
                ] += 1

    summary_lines = [
        f"Photo Database: {database}",
        f"Size bytes: {len(data)}",
        f"Entropy: {entropy(data):.6f}",
        "",
        f"Readable strings: {len(string_rows)}",
        f"Integer references {TILE_MIN}-{TILE_MAX}: "
        f"{len(integer_rows)}",
        f"Text references T{TILE_MIN}-T{TILE_MAX}: "
        f"{len(text_reference_rows)}",
        "",
        "Integer hits by encoding:",
    ]

    for encoding, count in sorted(
        encoding_counts.items()
    ):
        summary_lines.append(
            f"  {encoding}: {count}"
        )

    summary_lines.extend([
        "",
        "Aligned integer hits:",
    ])

    for (
        encoding,
        alignment,
    ), count in sorted(
        aligned_counts.items()
    ):
        summary_lines.append(
            f"  {encoding} aligned {alignment:2d}: "
            f"{count}"
        )

    summary_lines.extend([
        "",
        "Most frequent tile IDs:",
    ])

    for (
        encoding,
        value,
    ), count in value_counts.most_common(80):
        summary_lines.append(
            f"  {encoding:<5} "
            f"T{value:<3}: {count}"
        )

    summary_lines.extend([
        "",
        "Most common spacing between matching references:",
    ])

    for spacing, count in spacing_counts.most_common(50):
        summary_lines.append(
            f"  spacing={spacing:4d}: {count}"
        )

    summary_lines.extend([
        "",
        "Readable strings:",
    ])

    for row in string_rows[:300]:
        summary_lines.append(
            f"  0x{row['offset']:08x} "
            f"{row['type']:<7} "
            f"{row['text'][:160]}"
        )

    summary_path = OUT / "summary.txt"

    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(summary_lines[:160]))
    print()
    print("=" * 120)
    print("TERMINÉ")
    print("=" * 120)
    print(f"Résumé :       {summary_path}")
    print(f"Chaînes :      {OUT / 'strings.csv'}")
    print(
        "Références :   "
        f"{OUT / 'integer_tile_references.csv'}"
    )
    print(
        "Références txt:"
        f" {OUT / 'text_tile_references.csv'}"
    )


if __name__ == "__main__":
    main()
