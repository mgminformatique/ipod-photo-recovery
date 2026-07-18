from __future__ import annotations

from collections import Counter
from pathlib import Path
import csv
import hashlib
import math
import statistics


SOURCE = Path(
    "/home/murph/Desktop/iPod Photo Cache/F08/T157.ithmb"
)

OUT = Path("output/t157_page_map")
OUT.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 4096


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    value = 0.0

    for count in counts.values():
        probability = count / total
        value -= probability * math.log2(probability)

    return value


def dominant_byte(data: bytes) -> tuple[int, float]:
    if not data:
        return 0, 1.0

    byte_value, count = Counter(data).most_common(1)[0]

    return byte_value, count / len(data)


def byte_difference(a: bytes, b: bytes) -> float:
    if not a or not b:
        return 1.0

    length = min(len(a), len(b))

    different = sum(
        left != right
        for left, right in zip(
            a[:length],
            b[:length],
        )
    )

    return different / length


def mean_absolute_difference(a: bytes, b: bytes) -> float:
    if not a or not b:
        return 255.0

    length = min(len(a), len(b))

    total = sum(
        abs(left - right)
        for left, right in zip(
            a[:length],
            b[:length],
        )
    )

    return total / length


def classify_page(
    page_entropy: float,
    dominant_ratio: float,
    zero_ratio: float,
    one_ratio: float,
) -> str:
    if dominant_ratio >= 0.98:
        return "PADDING"

    if page_entropy <= 0.50:
        return "LOW_ENTROPY"

    if page_entropy >= 7.70:
        return "HIGH_ENTROPY"

    if page_entropy >= 6.00:
        return "MEDIUM_HIGH"

    if page_entropy >= 3.00:
        return "MEDIUM"

    return "LOW"


def marker_for_class(page_class: str) -> str:
    markers = {
        "PADDING": ".",
        "LOW_ENTROPY": "_",
        "LOW": "-",
        "MEDIUM": "=",
        "MEDIUM_HIGH": "#",
        "HIGH_ENTROPY": "@",
    }

    return markers.get(page_class, "?")


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {SOURCE}"
        )

    data = SOURCE.read_bytes()

    pages = [
        data[offset:offset + PAGE_SIZE]
        for offset in range(0, len(data), PAGE_SIZE)
        if len(data[offset:offset + PAGE_SIZE]) == PAGE_SIZE
    ]

    remainder = len(data) % PAGE_SIZE

    print("=" * 130)
    print("T157 PAGE MAP")
    print("=" * 130)
    print(f"Source:    {SOURCE}")
    print(f"Size:      {len(data)} bytes")
    print(f"Pages:     {len(pages)}")
    print(f"Remainder: {remainder} bytes")
    print()

    rows = []

    previous_page = None

    for index, page in enumerate(pages):
        page_entropy = entropy(page)
        dominant_value, dominant_ratio = dominant_byte(page)

        zero_ratio = page.count(0x00) / len(page)
        one_ratio = page.count(0x01) / len(page)
        ff_ratio = page.count(0xFF) / len(page)

        page_class = classify_page(
            page_entropy,
            dominant_ratio,
            zero_ratio,
            one_ratio,
        )

        if previous_page is None:
            difference_ratio = 0.0
            mad = 0.0
        else:
            difference_ratio = byte_difference(
                previous_page,
                page,
            )

            mad = mean_absolute_difference(
                previous_page,
                page,
            )

        first_u32_le = int.from_bytes(
            page[0:4],
            "little",
            signed=False,
        )

        first_u32_be = int.from_bytes(
            page[0:4],
            "big",
            signed=False,
        )

        row = {
            "page": index,
            "offset": index * PAGE_SIZE,
            "entropy": page_entropy,
            "class": page_class,
            "dominant_byte": f"0x{dominant_value:02x}",
            "dominant_ratio": dominant_ratio,
            "zero_ratio": zero_ratio,
            "one_ratio": one_ratio,
            "ff_ratio": ff_ratio,
            "difference_from_previous": difference_ratio,
            "mad_from_previous": mad,
            "first_u32_le": first_u32_le,
            "first_u32_be": first_u32_be,
            "sha1": hashlib.sha1(page).hexdigest(),
        }

        rows.append(row)
        previous_page = page

    csv_path = OUT / "pages.csv"

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

    map_lines = []

    for start in range(0, len(rows), 64):
        group = rows[start:start + 64]

        symbols = "".join(
            marker_for_class(row["class"])
            for row in group
        )

        map_lines.append(
            f"{start:04d}-{start + len(group) - 1:04d} "
            f"{symbols}"
        )

    map_path = OUT / "map.txt"

    map_path.write_text(
        "\n".join(map_lines) + "\n",
        encoding="utf-8",
    )

    transitions = []

    for index in range(1, len(rows)):
        previous = rows[index - 1]
        current = rows[index]

        entropy_jump = abs(
            current["entropy"]
            - previous["entropy"]
        )

        class_change = (
            current["class"]
            != previous["class"]
        )

        strong_difference = (
            current["difference_from_previous"]
            >= 0.80
        )

        if (
            entropy_jump >= 1.0
            or class_change
            or strong_difference
        ):
            transitions.append({
                "page": current["page"],
                "previous_class": previous["class"],
                "current_class": current["class"],
                "previous_entropy": previous["entropy"],
                "current_entropy": current["entropy"],
                "entropy_jump": entropy_jump,
                "difference_ratio": current[
                    "difference_from_previous"
                ],
                "mad": current["mad_from_previous"],
            })

    transition_path = OUT / "transitions.csv"

    with transition_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        if transitions:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(transitions[0].keys()),
            )

            writer.writeheader()
            writer.writerows(transitions)

    duplicate_groups = {}

    for row in rows:
        duplicate_groups.setdefault(
            row["sha1"],
            [],
        ).append(row["page"])

    duplicates = [
        pages_list
        for pages_list in duplicate_groups.values()
        if len(pages_list) > 1
    ]

    duplicate_path = OUT / "duplicate_pages.txt"

    with duplicate_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for pages_list in sorted(
            duplicates,
            key=lambda values: (
                -len(values),
                values[0],
            ),
        ):
            handle.write(
                f"{len(pages_list):3d} copies: "
                + ", ".join(
                    str(page)
                    for page in pages_list
                )
                + "\n"
            )

    classes = Counter(
        row["class"]
        for row in rows
    )

    entropies = [
        row["entropy"]
        for row in rows
    ]

    differences = [
        row["difference_from_previous"]
        for row in rows[1:]
    ]

    summary_lines = [
        f"Source: {SOURCE}",
        f"Size bytes: {len(data)}",
        f"Full pages: {len(pages)}",
        f"Remainder bytes: {remainder}",
        "",
        "Page classes:",
    ]

    for page_class, count in sorted(
        classes.items()
    ):
        summary_lines.append(
            f"  {page_class}: {count}"
        )

    summary_lines.extend([
        "",
        f"Entropy minimum: {min(entropies):.4f}",
        f"Entropy maximum: {max(entropies):.4f}",
        f"Entropy mean: {statistics.mean(entropies):.4f}",
        f"Entropy median: {statistics.median(entropies):.4f}",
        "",
        (
            "Mean page difference: "
            f"{statistics.mean(differences):.4f}"
        ),
        (
            "Median page difference: "
            f"{statistics.median(differences):.4f}"
        ),
        "",
        f"Transition candidates: {len(transitions)}",
        f"Duplicate page groups: {len(duplicates)}",
        "",
        "Legend:",
        "  . = padding",
        "  _ = very low entropy",
        "  - = low entropy",
        "  = = medium entropy",
        "  # = medium-high entropy",
        "  @ = high entropy",
    ])

    summary_path = OUT / "summary.txt"

    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(summary_lines))
    print()
    print(f"Map:         {map_path}")
    print(f"Pages CSV:   {csv_path}")
    print(f"Transitions: {transition_path}")
    print(f"Duplicates:  {duplicate_path}")
    print(f"Summary:     {summary_path}")


if __name__ == "__main__":
    main()
