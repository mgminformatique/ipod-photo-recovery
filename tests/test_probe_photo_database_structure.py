from __future__ import annotations

from collections import Counter
from pathlib import Path
import csv
import math
import statistics
import struct
import zlib


ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DATABASE = ROOT / "Photo Database"
OUT = Path("output/photo_database_structure")
OUT.mkdir(parents=True, exist_ok=True)

MIN_RECORD_SIZE = 8
MAX_RECORD_SIZE = 512

COMMON_DIMENSIONS = {
    16, 20, 24, 32, 40, 48, 50, 56, 60, 64,
    72, 75, 80, 90, 96, 100, 120, 128, 132,
    144, 150, 160, 176, 180, 192, 200, 220,
    240, 256, 288, 300, 320, 360, 480, 640,
    720, 768, 800, 1024, 1280, 1600, 1920,
    2048, 2560, 3264, 4000, 4032,
}


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def chi_square_uniform(data: bytes) -> float:
    if not data:
        return 0.0

    expected = len(data) / 256
    counts = Counter(data)

    return sum(
        ((counts.get(value, 0) - expected) ** 2) / expected
        for value in range(256)
    )


def compression_ratio(data: bytes) -> float:
    if not data:
        return 0.0

    compressed = zlib.compress(data, level=9)
    return len(compressed) / len(data)


def read_uint(
    data: bytes,
    offset: int,
    width: int,
    endian: str,
) -> int | None:
    if offset + width > len(data):
        return None

    if width == 2:
        fmt = "<H" if endian == "le" else ">H"
    elif width == 4:
        fmt = "<I" if endian == "le" else ">I"
    else:
        raise ValueError(width)

    return struct.unpack_from(fmt, data, offset)[0]


def monotonic_ratio(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0

    comparisons = len(values) - 1

    increasing = sum(
        right >= left
        for left, right in zip(values, values[1:])
    )

    return increasing / comparisons


def strict_increasing_ratio(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0

    comparisons = len(values) - 1

    increasing = sum(
        right > left
        for left, right in zip(values, values[1:])
    )

    return increasing / comparisons


def uniqueness_ratio(values: list[int]) -> float:
    if not values:
        return 0.0

    return len(set(values)) / len(values)


def small_value_ratio(
    values: list[int],
    maximum: int,
) -> float:
    if not values:
        return 0.0

    return sum(
        0 <= value <= maximum
        for value in values
    ) / len(values)


def dimension_ratio(values: list[int]) -> float:
    if not values:
        return 0.0

    plausible = 0

    for value in values:
        if value in COMMON_DIMENSIONS:
            plausible += 1
        elif 8 <= value <= 8192:
            if value % 8 == 0:
                plausible += 0.25

    return plausible / len(values)


def ithmb_files() -> list[Path]:
    return sorted(ROOT.rglob("*.ithmb"))


def collect_file_sizes() -> list[int]:
    return sorted(
        path.stat().st_size
        for path in ithmb_files()
    )


def offset_size_ratio(
    values: list[int],
    file_sizes: list[int],
) -> float:
    if not values or not file_sizes:
        return 0.0

    maximum = max(file_sizes)

    plausible = sum(
        0 <= value <= maximum
        for value in values
    )

    return plausible / len(values)


def exact_file_size_matches(
    values: list[int],
    file_sizes: list[int],
) -> int:
    file_size_set = set(file_sizes)

    return sum(
        value in file_size_set
        for value in values
    )


def nearest_file_boundary_ratio(
    values: list[int],
    file_sizes: list[int],
    tolerance: int = 4096,
) -> float:
    if not values or not file_sizes:
        return 0.0

    hits = 0

    for value in values:
        for file_size in file_sizes:
            if abs(value - file_size) <= tolerance:
                hits += 1
                break

    return hits / len(values)


def column_values(
    data: bytes,
    record_size: int,
    start_offset: int,
    field_offset: int,
    width: int,
    endian: str,
    limit: int = 10000,
) -> list[int]:
    values = []

    position = start_offset + field_offset

    while (
        position + width <= len(data)
        and len(values) < limit
    ):
        value = read_uint(
            data,
            position,
            width,
            endian,
        )

        if value is None:
            break

        values.append(value)
        position += record_size

    return values


def score_column(
    values: list[int],
    width: int,
    file_sizes: list[int],
) -> dict:
    if len(values) < 4:
        return {
            "score": 0.0,
        }

    unique = uniqueness_ratio(values)
    monotonic = monotonic_ratio(values)
    strict_monotonic = strict_increasing_ratio(values)

    small_255 = small_value_ratio(values, 255)
    small_4096 = small_value_ratio(values, 4096)
    small_65535 = small_value_ratio(values, 65535)

    dimensions = dimension_ratio(values)
    file_offset = offset_size_ratio(values, file_sizes)
    exact_sizes = exact_file_size_matches(values, file_sizes)
    near_sizes = nearest_file_boundary_ratio(values, file_sizes)

    most_common_count = Counter(values).most_common(1)[0][1]
    repeated_ratio = most_common_count / len(values)

    zero_ratio = values.count(0) / len(values)

    deltas = [
        right - left
        for left, right in zip(values, values[1:])
    ]

    positive_deltas = [
        delta
        for delta in deltas
        if delta > 0
    ]

    regular_delta_ratio = 0.0
    dominant_delta = ""

    if positive_deltas:
        dominant, count = Counter(
            positive_deltas
        ).most_common(1)[0]

        dominant_delta = dominant
        regular_delta_ratio = count / len(positive_deltas)

    score = 0.0

    # Champs de type compteur ou offset croissant
    score += monotonic * 2.5
    score += strict_monotonic * 2.0
    score += regular_delta_ratio * 2.0

    # Champs à valeurs plausibles
    score += dimensions * 2.0
    score += file_offset * 0.8
    score += near_sizes * 1.5

    # Champs enum / flags / petites valeurs
    score += small_255 * 0.8
    score += small_4096 * 0.5

    # Colonnes structurées, ni toutes identiques ni totalement aléatoires
    if 0.02 <= unique <= 0.95:
        score += 1.0

    if 0.05 <= repeated_ratio <= 0.95:
        score += 0.5

    if 0.01 <= zero_ratio <= 0.95:
        score += 0.5

    # Les correspondances exactes de tailles sont très intéressantes
    score += min(exact_sizes, 5) * 0.5

    # Pénalité légère si tous les nombres sont énormes et aléatoires
    if (
        width == 4
        and small_65535 < 0.01
        and monotonic < 0.55
        and repeated_ratio < 0.05
    ):
        score -= 1.5

    return {
        "score": score,
        "unique_ratio": unique,
        "monotonic_ratio": monotonic,
        "strict_monotonic_ratio": strict_monotonic,
        "small_255_ratio": small_255,
        "small_4096_ratio": small_4096,
        "small_65535_ratio": small_65535,
        "dimension_ratio": dimensions,
        "file_offset_ratio": file_offset,
        "exact_file_size_matches": exact_sizes,
        "near_file_size_ratio": near_sizes,
        "repeated_ratio": repeated_ratio,
        "zero_ratio": zero_ratio,
        "dominant_delta": dominant_delta,
        "regular_delta_ratio": regular_delta_ratio,
        "minimum": min(values),
        "maximum": max(values),
        "sample": " ".join(
            str(value)
            for value in values[:12]
        ),
    }


def evaluate_record_layouts(
    data: bytes,
    file_sizes: list[int],
) -> list[dict]:
    rows = []

    for record_size in range(
        MIN_RECORD_SIZE,
        MAX_RECORD_SIZE + 1,
    ):
        # On teste plusieurs décalages initiaux, car un en-tête
        # peut précéder la table.
        maximum_start = min(record_size, 64)

        for start_offset in range(maximum_start):
            record_count = (
                len(data) - start_offset
            ) // record_size

            if record_count < 8:
                continue

            remainder = (
                len(data) - start_offset
            ) % record_size

            best_columns = []

            for width in (2, 4):
                for endian in ("le", "be"):
                    maximum_field = min(
                        record_size - width,
                        128,
                    )

                    for field_offset in range(
                        0,
                        maximum_field + 1,
                        width,
                    ):
                        values = column_values(
                            data=data,
                            record_size=record_size,
                            start_offset=start_offset,
                            field_offset=field_offset,
                            width=width,
                            endian=endian,
                        )

                        metrics = score_column(
                            values,
                            width,
                            file_sizes,
                        )

                        score = metrics.get(
                            "score",
                            0.0,
                        )

                        if score <= 0:
                            continue

                        best_columns.append({
                            "score": score,
                            "width": width,
                            "endian": endian,
                            "field_offset": field_offset,
                            **metrics,
                        })

            best_columns.sort(
                key=lambda item: item["score"],
                reverse=True,
            )

            top = best_columns[:5]

            if not top:
                continue

            layout_score = sum(
                column["score"]
                for column in top
            )

            # Bonus lorsque la taille divise presque exactement le fichier.
            if remainder == 0:
                layout_score += 4.0
            elif remainder <= 8:
                layout_score += 2.0
            elif remainder <= 32:
                layout_score += 0.5

            rows.append({
                "record_size": record_size,
                "start_offset": start_offset,
                "record_count": record_count,
                "remainder": remainder,
                "layout_score": layout_score,
                "best_column_score": top[0]["score"],
                "best_width": top[0]["width"],
                "best_endian": top[0]["endian"],
                "best_field_offset": top[0]["field_offset"],
                "best_sample": top[0]["sample"],
                "best_minimum": top[0]["minimum"],
                "best_maximum": top[0]["maximum"],
                "best_monotonic": top[0]["monotonic_ratio"],
                "best_dimension_ratio": top[0]["dimension_ratio"],
                "best_file_offset_ratio": top[0]["file_offset_ratio"],
                "best_exact_size_matches": top[0]["exact_file_size_matches"],
                "top_columns": top,
            })

    rows.sort(
        key=lambda row: row["layout_score"],
        reverse=True,
    )

    return rows


def block_similarity(
    data: bytes,
    block_size: int,
) -> float:
    blocks = [
        data[offset:offset + block_size]
        for offset in range(
            0,
            len(data) - block_size + 1,
            block_size,
        )
    ]

    if len(blocks) < 2:
        return 0.0

    similarities = []

    for left, right in zip(
        blocks,
        blocks[1:],
    ):
        same = sum(
            a == b
            for a, b in zip(left, right)
        )

        similarities.append(
            same / block_size
        )

    return statistics.mean(similarities)


def write_layout_csv(rows: list[dict]) -> Path:
    destination = OUT / "candidate_layouts.csv"

    fieldnames = [
        "record_size",
        "start_offset",
        "record_count",
        "remainder",
        "layout_score",
        "best_column_score",
        "best_width",
        "best_endian",
        "best_field_offset",
        "best_sample",
        "best_minimum",
        "best_maximum",
        "best_monotonic",
        "best_dimension_ratio",
        "best_file_offset_ratio",
        "best_exact_size_matches",
    ]

    with destination.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow({
                key: row[key]
                for key in fieldnames
            })

    return destination


def write_columns_csv(rows: list[dict]) -> Path:
    destination = OUT / "candidate_columns.csv"

    fieldnames = [
        "record_size",
        "start_offset",
        "record_count",
        "remainder",
        "layout_score",
        "column_rank",
        "column_score",
        "width",
        "endian",
        "field_offset",
        "minimum",
        "maximum",
        "unique_ratio",
        "monotonic_ratio",
        "strict_monotonic_ratio",
        "small_255_ratio",
        "small_4096_ratio",
        "small_65535_ratio",
        "dimension_ratio",
        "file_offset_ratio",
        "exact_file_size_matches",
        "near_file_size_ratio",
        "repeated_ratio",
        "zero_ratio",
        "dominant_delta",
        "regular_delta_ratio",
        "sample",
    ]

    with destination.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for layout in rows[:500]:
            for rank, column in enumerate(
                layout["top_columns"],
                start=1,
            ):
                writer.writerow({
                    "record_size": layout["record_size"],
                    "start_offset": layout["start_offset"],
                    "record_count": layout["record_count"],
                    "remainder": layout["remainder"],
                    "layout_score": layout["layout_score"],
                    "column_rank": rank,
                    "column_score": column["score"],
                    "width": column["width"],
                    "endian": column["endian"],
                    "field_offset": column["field_offset"],
                    "minimum": column["minimum"],
                    "maximum": column["maximum"],
                    "unique_ratio": column["unique_ratio"],
                    "monotonic_ratio": column["monotonic_ratio"],
                    "strict_monotonic_ratio": column[
                        "strict_monotonic_ratio"
                    ],
                    "small_255_ratio": column["small_255_ratio"],
                    "small_4096_ratio": column[
                        "small_4096_ratio"
                    ],
                    "small_65535_ratio": column[
                        "small_65535_ratio"
                    ],
                    "dimension_ratio": column["dimension_ratio"],
                    "file_offset_ratio": column[
                        "file_offset_ratio"
                    ],
                    "exact_file_size_matches": column[
                        "exact_file_size_matches"
                    ],
                    "near_file_size_ratio": column[
                        "near_file_size_ratio"
                    ],
                    "repeated_ratio": column["repeated_ratio"],
                    "zero_ratio": column["zero_ratio"],
                    "dominant_delta": column["dominant_delta"],
                    "regular_delta_ratio": column[
                        "regular_delta_ratio"
                    ],
                    "sample": column["sample"],
                })

    return destination


def main() -> None:
    if not DATABASE.exists():
        raise FileNotFoundError(
            f"Fichier absent : {DATABASE}"
        )

    data = DATABASE.read_bytes()
    files = ithmb_files()
    file_sizes = collect_file_sizes()

    print("=" * 120)
    print("RECHERCHE DE STRUCTURE DANS PHOTO DATABASE")
    print("=" * 120)
    print(f"Base : {DATABASE}")
    print(f"Taille : {len(data)} octets")
    print(f"Fichiers .ithmb : {len(files)}")
    print(f"Entropie : {entropy(data):.6f}")
    print(f"Chi-square : {chi_square_uniform(data):.3f}")
    print(
        "Ratio après compression zlib : "
        f"{compression_ratio(data):.6f}"
    )
    print()

    print(
        f"Analyse des tailles d'enregistrement "
        f"{MIN_RECORD_SIZE} à {MAX_RECORD_SIZE}..."
    )

    rows = evaluate_record_layouts(
        data,
        file_sizes,
    )

    layouts_csv = write_layout_csv(rows)
    columns_csv = write_columns_csv(rows)

    similarity_rows = []

    for block_size in range(8, 513):
        similarity_rows.append({
            "block_size": block_size,
            "similarity": block_similarity(
                data,
                block_size,
            ),
            "remainder": len(data) % block_size,
        })

    similarity_rows.sort(
        key=lambda row: row["similarity"],
        reverse=True,
    )

    similarity_csv = OUT / "block_similarity.csv"

    with similarity_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "block_size",
                "similarity",
                "remainder",
            ],
        )

        writer.writeheader()
        writer.writerows(similarity_rows)

    summary_lines = [
        f"Database: {DATABASE}",
        f"Size: {len(data)}",
        f"Entropy: {entropy(data):.6f}",
        f"Chi-square uniform: {chi_square_uniform(data):.6f}",
        f"Zlib compression ratio: {compression_ratio(data):.6f}",
        f"Ithmb files: {len(files)}",
        "",
        "Top 50 candidate record layouts:",
    ]

    for rank, row in enumerate(
        rows[:50],
        start=1,
    ):
        summary_lines.append(
            f"{rank:2d}. "
            f"record={row['record_size']:3d} "
            f"start={row['start_offset']:2d} "
            f"count={row['record_count']:5d} "
            f"remainder={row['remainder']:3d} "
            f"score={row['layout_score']:8.3f} | "
            f"field=+{row['best_field_offset']:3d} "
            f"u{row['best_width'] * 8}"
            f"{row['best_endian']} "
            f"column_score={row['best_column_score']:7.3f} "
            f"mono={row['best_monotonic']:.3f} "
            f"dim={row['best_dimension_ratio']:.3f} "
            f"fileoff={row['best_file_offset_ratio']:.3f} "
            f"exact_sizes={row['best_exact_size_matches']}"
        )

        summary_lines.append(
            f"    sample: {row['best_sample']}"
        )

    summary_lines.extend([
        "",
        "Top 40 block similarities:",
    ])

    for rank, row in enumerate(
        similarity_rows[:40],
        start=1,
    ):
        summary_lines.append(
            f"{rank:2d}. "
            f"block={row['block_size']:3d} "
            f"similarity={row['similarity']:.6f} "
            f"remainder={row['remainder']}"
        )

    summary = OUT / "summary.txt"

    summary.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print()
    print("\n".join(summary_lines))
    print()
    print("=" * 120)
    print("TERMINÉ")
    print("=" * 120)
    print(f"Résumé : {summary}")
    print(f"Layouts : {layouts_csv}")
    print(f"Colonnes : {columns_csv}")
    print(f"Similarités : {similarity_csv}")


if __name__ == "__main__":
    main()
