from __future__ import annotations

from collections import Counter
from pathlib import Path
import csv
import math
import statistics


ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/ithmb_structure_inventory")

OUT.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 4096
SAMPLE_SIZE = 1024 * 1024

RECORD_SIZES = (
    12,
    16,
    20,
    24,
    28,
    32,
    36,
    40,
    48,
    64,
    80,
    96,
    128,
    160,
    192,
    256,
    512,
    1024,
    2048,
    4096,
)


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    entropy = 0.0

    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)

    return entropy


def byte_ratio(data: bytes, value: int) -> float:
    if not data:
        return 0.0

    return data.count(value) / len(data)


def dominant_byte_stats(data: bytes) -> tuple[int, float]:
    if not data:
        return 0, 1.0

    counts = Counter(data)
    byte_value, count = counts.most_common(1)[0]

    return byte_value, count / len(data)


def page_entropies(data: bytes) -> list[float]:
    values = []

    for offset in range(0, len(data), PAGE_SIZE):
        page = data[offset:offset + PAGE_SIZE]

        if len(page) != PAGE_SIZE:
            continue

        values.append(shannon_entropy(page))

    return values


def page_dominant_ratios(data: bytes) -> list[float]:
    values = []

    for offset in range(0, len(data), PAGE_SIZE):
        page = data[offset:offset + PAGE_SIZE]

        if len(page) != PAGE_SIZE:
            continue

        _, ratio = dominant_byte_stats(page)
        values.append(ratio)

    return values


def count_low_entropy_pages(entropies: list[float]) -> int:
    return sum(
        entropy <= 0.50
        for entropy in entropies
    )


def count_high_entropy_pages(entropies: list[float]) -> int:
    return sum(
        entropy >= 7.50
        for entropy in entropies
    )


def count_padding_pages(
    entropies: list[float],
    dominant_ratios: list[float],
) -> int:
    return sum(
        entropy <= 0.50 or dominant_ratio >= 0.97
        for entropy, dominant_ratio in zip(
            entropies,
            dominant_ratios,
        )
    )


def repeated_page_ratio(data: bytes) -> float:
    pages = []

    for offset in range(0, len(data), PAGE_SIZE):
        page = data[offset:offset + PAGE_SIZE]

        if len(page) == PAGE_SIZE:
            pages.append(page)

    if not pages:
        return 0.0

    unique_pages = len(set(pages))

    return 1.0 - (unique_pages / len(pages))


def repeated_chunk_ratio(
    data: bytes,
    chunk_size: int,
) -> float:
    if chunk_size <= 0:
        return 0.0

    chunks = []

    for offset in range(0, len(data), chunk_size):
        chunk = data[offset:offset + chunk_size]

        if len(chunk) == chunk_size:
            chunks.append(chunk)

    if not chunks:
        return 0.0

    unique_chunks = len(set(chunks))

    return 1.0 - (unique_chunks / len(chunks))


def divisibility_string(size: int) -> str:
    matches = [
        str(record_size)
        for record_size in RECORD_SIZES
        if size % record_size == 0
    ]

    return ",".join(matches)


def likely_record_sizes(
    size: int,
    data: bytes,
) -> str:
    candidates = []

    for record_size in RECORD_SIZES:
        if size % record_size != 0:
            continue

        record_count = size // record_size

        if record_count < 2:
            continue

        repeat_ratio = repeated_chunk_ratio(
            data,
            record_size,
        )

        candidates.append(
            (
                repeat_ratio,
                record_size,
                record_count,
            )
        )

    candidates.sort(reverse=True)

    return ";".join(
        (
            f"{record_size}B:"
            f"{record_count}records:"
            f"repeat={repeat_ratio:.3f}"
        )
        for repeat_ratio, record_size, record_count
        in candidates[:8]
    )


def detect_24_byte_structure(data: bytes) -> dict:
    if len(data) < 48:
        return {
            "records_24": 0,
            "unique_first4": 0,
            "monotonic_first4_ratio": 0.0,
            "repeated_first4_ratio": 0.0,
            "zero_tail_ratio": 0.0,
        }

    record_count = len(data) // 24

    first_values = []
    zero_tail_records = 0

    for index in range(record_count):
        record = data[index * 24:(index + 1) * 24]

        if len(record) != 24:
            continue

        first_values.append(
            int.from_bytes(
                record[0:4],
                "little",
                signed=False,
            )
        )

        if record[16:24] == b"\x00" * 8:
            zero_tail_records += 1

    if len(first_values) < 2:
        monotonic_ratio = 0.0
    else:
        monotonic_steps = sum(
            first_values[index + 1]
            >= first_values[index]
            for index in range(len(first_values) - 1)
        )

        monotonic_ratio = (
            monotonic_steps
            / (len(first_values) - 1)
        )

    unique_first4 = len(set(first_values))

    repeated_first4_ratio = (
        1.0
        - unique_first4 / len(first_values)
        if first_values
        else 0.0
    )

    zero_tail_ratio = (
        zero_tail_records / record_count
        if record_count
        else 0.0
    )

    return {
        "records_24": record_count,
        "unique_first4": unique_first4,
        "monotonic_first4_ratio": monotonic_ratio,
        "repeated_first4_ratio": repeated_first4_ratio,
        "zero_tail_ratio": zero_tail_ratio,
    }


def classify_file(
    size: int,
    entropy: float,
    pages: int,
    padding_pages: int,
    records_24: int,
    monotonic_24: float,
    repeat_24: float,
    repeated_pages: float,
) -> str:
    padding_ratio = (
        padding_pages / pages
        if pages
        else 0.0
    )

    if (
        size % 24 == 0
        and records_24 >= 20
        and monotonic_24 >= 0.70
    ):
        return "TABLE_24B"

    if (
        pages >= 20
        and padding_ratio >= 0.05
        and entropy >= 4.0
    ):
        return "PAYLOAD_PAGED"

    if (
        size < 256 * 1024
        and entropy < 6.5
    ):
        return "SMALL_TABLE"

    if (
        entropy >= 7.5
        and padding_ratio < 0.02
    ):
        return "HIGH_ENTROPY"

    if repeated_pages >= 0.25:
        return "REPEATED_PAGES"

    return "UNKNOWN"


def format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"

    if size >= 1024:
        return f"{size / 1024:.2f} KB"

    return f"{size} B"


def main() -> None:
    if not ROOT.exists():
        raise FileNotFoundError(
            f"Dossier introuvable : {ROOT}"
        )

    files = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".ithmb"
    )

    print("=" * 150)
    print("INVENTAIRE STRUCTUREL COMPLET DES .ITHMB")
    print("=" * 150)
    print(f"Source : {ROOT}")
    print(f"Fichiers : {len(files)}")
    print()

    rows = []

    for index, path in enumerate(files):
        data = path.read_bytes()
        size = len(data)

        if size <= SAMPLE_SIZE:
            entropy_data = data
        else:
            half = SAMPLE_SIZE // 2

            entropy_data = (
                data[:half]
                + data[-half:]
            )

        entropy = shannon_entropy(entropy_data)

        pages = size // PAGE_SIZE
        remainder = size % PAGE_SIZE

        entropies = page_entropies(data)
        dominant_ratios = page_dominant_ratios(data)

        low_entropy_pages = count_low_entropy_pages(
            entropies
        )

        high_entropy_pages = count_high_entropy_pages(
            entropies
        )

        padding_pages = count_padding_pages(
            entropies,
            dominant_ratios,
        )

        repeated_pages = repeated_page_ratio(data)

        ratio_00 = byte_ratio(entropy_data, 0x00)
        ratio_01 = byte_ratio(entropy_data, 0x01)
        ratio_ff = byte_ratio(entropy_data, 0xFF)

        dominant_byte, dominant_ratio = (
            dominant_byte_stats(entropy_data)
        )

        structure_24 = detect_24_byte_structure(data)

        classification = classify_file(
            size=size,
            entropy=entropy,
            pages=pages,
            padding_pages=padding_pages,
            records_24=structure_24["records_24"],
            monotonic_24=structure_24[
                "monotonic_first4_ratio"
            ],
            repeat_24=structure_24[
                "repeated_first4_ratio"
            ],
            repeated_pages=repeated_pages,
        )

        row = {
            "index": index,
            "file": str(path),
            "folder": path.parent.name,
            "name": path.name,
            "size_bytes": size,
            "size_human": format_size(size),
            "pages_4096": pages,
            "page_remainder": remainder,
            "entropy": entropy,
            "ratio_00": ratio_00,
            "ratio_01": ratio_01,
            "ratio_ff": ratio_ff,
            "dominant_byte": f"0x{dominant_byte:02x}",
            "dominant_ratio": dominant_ratio,
            "low_entropy_pages": low_entropy_pages,
            "high_entropy_pages": high_entropy_pages,
            "padding_pages": padding_pages,
            "padding_page_ratio": (
                padding_pages / pages
                if pages
                else 0.0
            ),
            "repeated_page_ratio": repeated_pages,
            "records_24": structure_24["records_24"],
            "unique_first4_24": structure_24[
                "unique_first4"
            ],
            "monotonic_first4_ratio_24": structure_24[
                "monotonic_first4_ratio"
            ],
            "repeated_first4_ratio_24": structure_24[
                "repeated_first4_ratio"
            ],
            "zero_tail_ratio_24": structure_24[
                "zero_tail_ratio"
            ],
            "divisible_by": divisibility_string(size),
            "likely_record_sizes": likely_record_sizes(
                size,
                data,
            ),
            "classification": classification,
        }

        rows.append(row)

        print(
            f"{index:02d} "
            f"{path.parent.name}/{path.name:<12} "
            f"{format_size(size):>10} "
            f"pages={pages:4d} "
            f"H={entropy:5.2f} "
            f"padding={padding_pages:3d} "
            f"24B={structure_24['records_24']:6d} "
            f"{classification}"
        )

    csv_path = OUT / "inventory.csv"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)

    by_class = Counter(
        row["classification"]
        for row in rows
    )

    summary_lines = [
        f"Source: {ROOT}",
        f"Total files: {len(rows)}",
        "",
        "Classifications:",
    ]

    for classification, count in sorted(
        by_class.items()
    ):
        summary_lines.append(
            f"  {classification}: {count}"
        )

    summary_lines.extend([
        "",
        "Largest files:",
    ])

    for row in sorted(
        rows,
        key=lambda item: item["size_bytes"],
        reverse=True,
    )[:20]:
        summary_lines.append(
            f"  {row['size_human']:>10} "
            f"{row['folder']}/{row['name']} "
            f"{row['classification']}"
        )

    summary_lines.extend([
        "",
        "Largest possible 24-byte record counts:",
    ])

    for row in sorted(
        rows,
        key=lambda item: item["records_24"],
        reverse=True,
    )[:20]:
        summary_lines.append(
            f"  {row['records_24']:7d} records "
            f"{row['folder']}/{row['name']} "
            f"mono={row['monotonic_first4_ratio_24']:.3f} "
            f"{row['classification']}"
        )

    summary_path = OUT / "summary.txt"

    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 150)
    print("TERMINÉ")
    print("=" * 150)
    print(f"CSV :     {csv_path}")
    print(f"Résumé :  {summary_path}")


if __name__ == "__main__":
    main()
