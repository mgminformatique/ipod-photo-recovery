from __future__ import annotations

import csv
import struct
import sys
from collections import Counter
from pathlib import Path

try:
    import numpy as np
except ImportError:
    print("Module requis : numpy")
    print("Installation : sudo apt install python3-numpy")
    sys.exit(1)


CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/block_metadata_probe")

TARGETS = [
    "T154.ithmb",
    "T155.ithmb",
    "T170.ithmb",
    "T173.ithmb",
]

BLOCK_SIZES = [544, 1084]

# On inspecte les octets aux débuts et fins de blocs.
WINDOW = 16

# Valeurs connues que nous voulons chercher dans la Photo Database.
SEARCH_VALUES = [
    180,
    360,
    540,
    544,
    1080,
    1084,
    2168,
    3252,
]


def locate_file(filename: str) -> Path | None:
    matches = sorted(CACHE_ROOT.rglob(filename))
    return matches[0] if matches else None


def locate_photo_database() -> Path | None:
    exact = sorted(CACHE_ROOT.rglob("Photo Database"))
    if exact:
        return exact[0]

    loose = sorted(
        path
        for path in CACHE_ROOT.rglob("*")
        if path.is_file()
        and "photo" in path.name.lower()
        and "database" in path.name.lower()
    )

    return loose[0] if loose else None


def integer_views(chunk: bytes) -> dict[str, int]:
    result: dict[str, int] = {}

    if len(chunk) >= 2:
        result["u16le"] = struct.unpack_from("<H", chunk, 0)[0]
        result["u16be"] = struct.unpack_from(">H", chunk, 0)[0]

    if len(chunk) >= 4:
        result["u32le"] = struct.unpack_from("<I", chunk, 0)[0]
        result["u32be"] = struct.unpack_from(">I", chunk, 0)[0]
        result["s32le"] = struct.unpack_from("<i", chunk, 0)[0]
        result["s32be"] = struct.unpack_from(">i", chunk, 0)[0]

    return result


def sequence_metrics(values: np.ndarray) -> dict[str, float | int]:
    if len(values) == 0:
        return {
            "count": 0,
            "unique": 0,
            "constant_percent": 0.0,
            "step_plus_1_percent": 0.0,
            "step_minus_1_percent": 0.0,
            "monotonic_non_decreasing_percent": 0.0,
            "mean_delta": 0.0,
            "median_delta": 0.0,
            "std_delta": 0.0,
        }

    unique = len(np.unique(values))

    if len(values) < 2:
        return {
            "count": len(values),
            "unique": unique,
            "constant_percent": 100.0,
            "step_plus_1_percent": 0.0,
            "step_minus_1_percent": 0.0,
            "monotonic_non_decreasing_percent": 100.0,
            "mean_delta": 0.0,
            "median_delta": 0.0,
            "std_delta": 0.0,
        }

    signed = values.astype(np.int64)
    delta = np.diff(signed)

    return {
        "count": len(values),
        "unique": unique,
        "constant_percent": float(np.mean(delta == 0) * 100.0),
        "step_plus_1_percent": float(np.mean(delta == 1) * 100.0),
        "step_minus_1_percent": float(np.mean(delta == -1) * 100.0),
        "monotonic_non_decreasing_percent": float(np.mean(delta >= 0) * 100.0),
        "mean_delta": float(np.mean(delta)),
        "median_delta": float(np.median(delta)),
        "std_delta": float(np.std(delta)),
    }


def entropy_u8(values: np.ndarray) -> float:
    if len(values) == 0:
        return 0.0

    counts = np.bincount(values.astype(np.uint8), minlength=256)
    probabilities = counts[counts > 0] / len(values)

    return float(-np.sum(probabilities * np.log2(probabilities)))


def inspect_byte_positions(
    blocks: np.ndarray,
    output_path: Path,
) -> None:
    block_size = blocks.shape[1]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)

        writer.writerow(
            [
                "position",
                "from_end",
                "mean",
                "std",
                "entropy",
                "unique",
                "zero_percent",
                "ff_percent",
                "same_as_previous_block_percent",
            ]
        )

        for position in range(block_size):
            column = blocks[:, position]
            same_previous = (
                float(np.mean(column[1:] == column[:-1]) * 100.0)
                if len(column) > 1
                else 100.0
            )

            writer.writerow(
                [
                    position,
                    position - block_size,
                    f"{float(np.mean(column)):.6f}",
                    f"{float(np.std(column)):.6f}",
                    f"{entropy_u8(column):.6f}",
                    len(np.unique(column)),
                    f"{float(np.mean(column == 0) * 100.0):.6f}",
                    f"{float(np.mean(column == 255) * 100.0):.6f}",
                    f"{same_previous:.6f}",
                ]
            )


def inspect_candidate_fields(
    blocks: np.ndarray,
    output_path: Path,
) -> list[dict[str, object]]:
    block_size = blocks.shape[1]
    results: list[dict[str, object]] = []

    starts = list(range(0, min(WINDOW, block_size - 3)))
    starts += list(range(max(0, block_size - WINDOW), block_size - 3))
    starts = sorted(set(starts))

    for start in starts:
        chunk_matrix = blocks[:, start : start + 4]

        for name, dtype in [
            ("u16le", "<u2"),
            ("u16be", ">u2"),
            ("u32le", "<u4"),
            ("u32be", ">u4"),
            ("s32le", "<i4"),
            ("s32be", ">i4"),
        ]:
            width = 2 if "16" in name else 4
            raw = chunk_matrix[:, :width].copy()
            values = raw.view(dtype).reshape(-1)

            metrics = sequence_metrics(values)

            row = {
                "field_start": start,
                "field_from_end": start - block_size,
                "field_type": name,
                **metrics,
                "first_value": int(values[0]),
                "last_value": int(values[-1]),
                "minimum": int(np.min(values)),
                "maximum": int(np.max(values)),
            }

            results.append(row)

    results.sort(
        key=lambda row: (
            -float(row["step_plus_1_percent"]),
            -float(row["monotonic_non_decreasing_percent"]),
            int(row["unique"]),
        )
    )

    fieldnames = [
        "rank",
        "field_start",
        "field_from_end",
        "field_type",
        "count",
        "unique",
        "first_value",
        "last_value",
        "minimum",
        "maximum",
        "constant_percent",
        "step_plus_1_percent",
        "step_minus_1_percent",
        "monotonic_non_decreasing_percent",
        "mean_delta",
        "median_delta",
        "std_delta",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for rank, row in enumerate(results, start=1):
            writer.writerow({"rank": rank, **row})

    return results


def inspect_boundary_windows(
    blocks: np.ndarray,
    output_path: Path,
) -> None:
    block_size = blocks.shape[1]

    positions = list(range(0, min(WINDOW, block_size)))
    positions += list(range(max(0, block_size - WINDOW), block_size))
    positions = sorted(set(positions))

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)

        header = ["block_index"]
        for position in positions:
            header.append(f"byte_{position}")
        writer.writerow(header)

        max_rows = min(len(blocks), 5000)

        for block_index in range(max_rows):
            writer.writerow(
                [block_index]
                + [int(blocks[block_index, position]) for position in positions]
            )


def inspect_four_byte_patterns(
    blocks: np.ndarray,
    output_path: Path,
) -> None:
    block_size = blocks.shape[1]

    candidates = {
        "first4": blocks[:, 0:4],
        "last4": blocks[:, block_size - 4 : block_size],
    }

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)

        writer.writerow(
            [
                "location",
                "pattern_hex",
                "count",
                "percent",
                "u16le_0",
                "u16le_2",
                "u32le",
                "u32be",
            ]
        )

        for location, matrix in candidates.items():
            patterns = Counter(bytes(row) for row in matrix)
            total = len(matrix)

            for pattern, count in patterns.most_common(100):
                writer.writerow(
                    [
                        location,
                        pattern.hex(" "),
                        count,
                        f"{count / total * 100.0:.6f}",
                        struct.unpack_from("<H", pattern, 0)[0],
                        struct.unpack_from("<H", pattern, 2)[0],
                        struct.unpack_from("<I", pattern, 0)[0],
                        struct.unpack_from(">I", pattern, 0)[0],
                    ]
                )


def analyze_target(filename: str) -> None:
    path = locate_file(filename)

    if path is None:
        print(f"[ABSENT] {filename}")
        return

    data = path.read_bytes()
    target_output = OUTPUT_ROOT / path.stem
    target_output.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print(f"Fichier : {path}")
    print(f"Taille  : {len(data):,} octets")

    for block_size in BLOCK_SIZES:
        block_count = len(data) // block_size
        remainder = len(data) % block_size

        if block_count < 2:
            continue

        raw = np.frombuffer(
            data[: block_count * block_size],
            dtype=np.uint8,
        ).reshape(block_count, block_size)

        block_output = target_output / f"block_{block_size}"
        block_output.mkdir(parents=True, exist_ok=True)

        inspect_byte_positions(
            raw,
            block_output / "byte_positions.csv",
        )

        ranked_fields = inspect_candidate_fields(
            raw,
            block_output / "candidate_integer_fields.csv",
        )

        inspect_boundary_windows(
            raw,
            block_output / "boundary_bytes_first5000.csv",
        )

        inspect_four_byte_patterns(
            raw,
            block_output / "four_byte_patterns.csv",
        )

        print()
        print(
            f"Bloc {block_size}: "
            f"{block_count:,} blocs, reste {remainder} octets"
        )

        print(
            f"{'rang':>4} {'pos':>6} {'fin':>6} {'type':>7} "
            f"{'unique':>8} {'+1 %':>10} {'stable %':>10} "
            f"{'mono %':>10} {'premier':>12} {'dernier':>12}"
        )

        for rank, row in enumerate(ranked_fields[:12], start=1):
            print(
                f"{rank:4d} "
                f"{int(row['field_start']):6d} "
                f"{int(row['field_from_end']):6d} "
                f"{str(row['field_type']):>7} "
                f"{int(row['unique']):8d} "
                f"{float(row['step_plus_1_percent']):10.3f} "
                f"{float(row['constant_percent']):10.3f} "
                f"{float(row['monotonic_non_decreasing_percent']):10.3f} "
                f"{int(row['first_value']):12d} "
                f"{int(row['last_value']):12d}"
            )

        print(f"Résultats : {block_output}")


def search_database_values(database_path: Path) -> None:
    data = database_path.read_bytes()
    output_path = OUTPUT_ROOT / "photo_database_value_hits.csv"

    rows = []

    for value in SEARCH_VALUES:
        encodings = {
            "u16le": struct.pack("<H", value)
            if 0 <= value <= 0xFFFF
            else None,
            "u16be": struct.pack(">H", value)
            if 0 <= value <= 0xFFFF
            else None,
            "u32le": struct.pack("<I", value),
            "u32be": struct.pack(">I", value),
        }

        for encoding_name, needle in encodings.items():
            if needle is None:
                continue

            start = 0
            hit_count = 0

            while True:
                offset = data.find(needle, start)

                if offset < 0:
                    break

                context_start = max(0, offset - 16)
                context_end = min(len(data), offset + len(needle) + 16)
                context = data[context_start:context_end]

                rows.append(
                    {
                        "value": value,
                        "encoding": encoding_name,
                        "offset_decimal": offset,
                        "offset_hex": f"0x{offset:08x}",
                        "context_hex": context.hex(" "),
                    }
                )

                hit_count += 1
                start = offset + 1

                if hit_count >= 5000:
                    break

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "value",
            "encoding",
            "offset_decimal",
            "offset_hex",
            "context_hex",
        ]

        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 96)
    print("PHOTO DATABASE")
    print("=" * 96)
    print(f"Fichier : {database_path}")
    print(f"Taille  : {len(data):,} octets")
    print(f"Hits    : {len(rows):,}")
    print(f"CSV     : {output_path}")

    summary = Counter((row["value"], row["encoding"]) for row in rows)

    print()
    print(f"{'valeur':>8} {'encodage':>8} {'hits':>8}")

    for value in SEARCH_VALUES:
        for encoding in ["u16le", "u16be", "u32le", "u32be"]:
            count = summary[(value, encoding)]

            if count:
                print(f"{value:8d} {encoding:>8} {count:8d}")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print("ITHMB BLOCK METADATA PROBE")
    print("=" * 96)
    print()
    print("Objectif : déterminer si les 4 octets autour des blocs")
    print("544 / 1084 sont des compteurs, offsets, en-têtes ou padding.")
    print()

    for target in TARGETS:
        analyze_target(target)
        print()

    database_path = locate_photo_database()

    if database_path is None:
        print("[ABSENT] Photo Database introuvable")
    else:
        search_database_values(database_path)

    print()
    print("=" * 96)
    print("TERMINÉ")
    print("=" * 96)
    print(f"Dossier : {OUTPUT_ROOT}")
    print()
    print("Fichiers les plus importants :")
    print(f"  {OUTPUT_ROOT}/T154/block_544/candidate_integer_fields.csv")
    print(f"  {OUTPUT_ROOT}/T154/block_1084/candidate_integer_fields.csv")
    print(f"  {OUTPUT_ROOT}/T154/block_544/four_byte_patterns.csv")
    print(f"  {OUTPUT_ROOT}/photo_database_value_hits.csv")


if __name__ == "__main__":
    main()
