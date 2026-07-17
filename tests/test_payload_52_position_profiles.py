from pathlib import Path
import struct
import math
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT = Path("output/payload_52_position_profiles.txt")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
DATA_PAGES = 52

TARGET_T_NUMBERS = {130} | set(range(154, 175))
EXCLUDED = {157, 168}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def is_marker(header: int):
    return header in {
        0x00000000,
        0x0D000000,
    }


def classify_payload(payload: bytes):
    counts = Counter(payload)
    ent = entropy(payload)

    zero_one = counts.get(0, 0) + counts.get(1, 0)
    padding = zero_one / len(payload) >= 0.95

    return {
        "entropy": ent,
        "unique": len(counts),
        "mean": sum(payload) / len(payload),
        "padding": padding,
        "zero": counts.get(0, 0),
        "one": counts.get(1, 0),
    }


units = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if (
        t_number not in TARGET_T_NUMBERS
        or t_number in EXCLUDED
    ):
        continue

    raw = path.read_bytes()
    page_count = len(raw) // PAGE_SIZE

    pages = []

    for page_index in range(page_count):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        pages.append({
            "index": page_index,
            "header": struct.unpack_from(">I", page, 0)[0],
            "payload": page[HEADER_SIZE:],
        })

    marker_indexes = [
        page["index"]
        for page in pages
        if is_marker(page["header"])
    ]

    clusters = []

    for marker_index in marker_indexes:
        if (
            clusters
            and marker_index == clusters[-1][-1] + 1
        ):
            clusters[-1].append(marker_index)
        else:
            clusters.append([marker_index])

    for left, right in zip(clusters, clusters[1:]):
        start = left[-1] + 1
        end = right[0] - 1

        if end - start + 1 != DATA_PAGES:
            continue

        unit_pages = pages[start:end + 1]

        units.append({
            "file": str(path.relative_to(CACHE)),
            "start": start,
            "end": end,
            "left_pattern": "".join(
                "D" if pages[index]["header"] == 0x0D000000 else "Z"
                for index in left
            ),
            "pages": unit_pages,
        })


print("=" * 140)
print("PAYLOAD 52-POSITION PROFILES")
print("=" * 140)
print(f"units={len(units)}")
print()

profiles = defaultdict(list)

for unit_index, unit in enumerate(units):
    for position, page in enumerate(unit["pages"]):
        stats = classify_payload(page["payload"])

        profiles[position].append({
            **stats,
            "payload": page["payload"],
            "file": unit["file"],
            "unit": unit_index,
            "page": page["index"],
        })


print("=" * 140)
print("POSITION SUMMARY")
print("=" * 140)

for position in range(DATA_PAGES):
    rows = profiles[position]
    count = len(rows)

    padding_count = sum(row["padding"] for row in rows)

    avg_entropy = sum(row["entropy"] for row in rows) / count
    avg_unique = sum(row["unique"] for row in rows) / count
    avg_mean = sum(row["mean"] for row in rows) / count

    print(
        f"position={position:02d} "
        f"count={count:3d} "
        f"entropy={avg_entropy:6.3f} "
        f"unique={avg_unique:7.2f} "
        f"mean={avg_mean:7.2f} "
        f"padding={padding_count:3d}/{count:3d} "
        f"{padding_count / count * 100:6.2f}%"
    )


print()
print("=" * 140)
print("AVERAGE EXACT SIMILARITY BY POSITION")
print("=" * 140)

for position in range(DATA_PAGES):
    rows = profiles[position]

    total_same = 0
    total_bytes = 0
    comparisons = 0

    for left, right in zip(rows, rows[1:]):
        same = sum(
            a == b
            for a, b in zip(
                left["payload"],
                right["payload"],
            )
        )

        total_same += same
        total_bytes += len(left["payload"])
        comparisons += 1

    percentage = (
        total_same / total_bytes * 100
        if total_bytes
        else 0.0
    )

    print(
        f"position={position:02d} "
        f"comparisons={comparisons:3d} "
        f"similarity={percentage:7.3f}%"
    )


print()
print("=" * 140)
print("MOST STABLE POSITIONS")
print("=" * 140)

stability_rows = []

for position in range(DATA_PAGES):
    rows = profiles[position]

    entropy_values = [
        row["entropy"]
        for row in rows
    ]

    mean_entropy = (
        sum(entropy_values) / len(entropy_values)
    )

    variance = (
        sum(
            (value - mean_entropy) ** 2
            for value in entropy_values
        ) / len(entropy_values)
    )

    stability_rows.append(
        (
            variance,
            position,
            mean_entropy,
        )
    )

for variance, position, mean_entropy in sorted(stability_rows):
    print(
        f"position={position:02d} "
        f"entropy_mean={mean_entropy:6.3f} "
        f"entropy_variance={variance:8.4f}"
    )


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
