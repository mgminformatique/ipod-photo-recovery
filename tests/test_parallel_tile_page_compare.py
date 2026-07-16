from pathlib import Path
import struct
import math
import hashlib
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
PAYLOAD_SIZE = PAGE_SIZE - HEADER_SIZE

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

# Tiles ayant plusieurs familles parallèles bien visibles.
TARGET_TILES = {
    2368,
    2376,
    2384,
    2392,
    2400,
    2407,
}


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


def exact_similarity(left: bytes, right: bytes):
    total = min(len(left), len(right))

    if total == 0:
        return 0, 0.0

    same = sum(
        a == b
        for a, b in zip(left[:total], right[:total])
    )

    return same, same / total * 100


def best_shift_similarity(left: bytes, right: bytes, max_shift=128):
    best_shift = 0
    best_same = -1
    best_total = 1

    for shift in range(-max_shift, max_shift + 1):
        if shift < 0:
            a = left[-shift:]
            b = right[:len(a)]
        elif shift > 0:
            a = left[:-shift]
            b = right[shift:]
        else:
            a = left
            b = right

        total = min(len(a), len(b))

        if total <= 0:
            continue

        same = sum(
            x == y
            for x, y in zip(a[:total], b[:total])
        )

        if same > best_same:
            best_same = same
            best_total = total
            best_shift = shift

    return (
        best_shift,
        best_same,
        best_same / best_total * 100,
    )


rows_by_tile = defaultdict(list)

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    for table_page in range(full_pages):
        page = raw[
            table_page * PAGE_SIZE:
            (table_page + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        if struct.unpack_from(">I", page, 0)[0] != 0x0D000000:
            continue

        payload = page[HEADER_SIZE:]

        for record_index in range(RECORD_COUNT):
            start = RECORD_START + record_index * RECORD_SIZE
            record = payload[start:start + RECORD_SIZE]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]

            if tile_id not in TARGET_TILES:
                continue

            f56 = struct.unpack_from(">H", record, 0x56)[0]

            if f56 % 9:
                continue

            data_page = f56 // 9

            if not 0 <= data_page < full_pages:
                continue

            data_offset = data_page * PAGE_SIZE
            data_page_raw = raw[
                data_offset:
                data_offset + PAGE_SIZE
            ]

            header = struct.unpack_from(">I", data_page_raw, 0)[0]
            page_payload = data_page_raw[HEADER_SIZE:]

            rows_by_tile[tile_id].append({
                "file": str(path.relative_to(CACHE)),
                "table_page": table_page,
                "record": record_index,
                "f56": f56,
                "index9": data_page,
                "base_id": tile_id - data_page,
                "header": header,
                "payload": page_payload,
            })


print("=" * 135)
print("PARALLEL TILE PHYSICAL PAGE COMPARISON")
print("=" * 135)

for tile_id in sorted(rows_by_tile):
    rows = sorted(
        rows_by_tile[tile_id],
        key=lambda row: (
            row["index9"],
            row["file"],
        )
    )

    print()
    print("=" * 135)
    print(f"TILE {tile_id}")
    print("=" * 135)

    for index, row in enumerate(rows):
        payload = row["payload"]

        print(
            f"entry={index:02d} "
            f"file={row['file']:18s} "
            f"index9/page={row['index9']:4d} "
            f"base={row['base_id']:4d} "
            f"header=0x{row['header']:08x} "
            f"entropy={entropy(payload):6.3f} "
            f"sha1={hashlib.sha1(payload).hexdigest()}"
        )

        print(
            "  first32="
            + payload[:32].hex(" ")
        )

    print()
    print("PAIR COMPARISONS")
    print("-" * 135)

    for left_index in range(len(rows)):
        for right_index in range(left_index + 1, len(rows)):
            left = rows[left_index]
            right = rows[right_index]

            same, exact_percent = exact_similarity(
                left["payload"],
                right["payload"],
            )

            shift, shifted_same, shifted_percent = (
                best_shift_similarity(
                    left["payload"],
                    right["payload"],
                )
            )

            print(
                f"{left_index:02d}<->{right_index:02d} "
                f"page_delta="
                f"{right['index9'] - left['index9']:+4d} "
                f"exact={same:4d}/{PAYLOAD_SIZE} "
                f"{exact_percent:6.2f}% "
                f"best_shift={shift:+4d} "
                f"shifted={shifted_same:4d} "
                f"{shifted_percent:6.2f}%"
            )

print()
print("=" * 135)
print("PAGE DELTA SUMMARY")
print("=" * 135)

delta_counts = Counter()

for tile_id, rows in rows_by_tile.items():
    indexes = sorted(set(row["index9"] for row in rows))

    for left, right in zip(indexes, indexes[1:]):
        delta_counts[right - left] += 1

for delta, count in delta_counts.most_common():
    print(
        f"delta={delta:4d} "
        f"count={count}"
    )
