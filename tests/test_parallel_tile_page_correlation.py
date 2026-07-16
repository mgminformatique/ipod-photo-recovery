from pathlib import Path
import struct
import math
from collections import defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

TARGET_TILES = {2368, 2376, 2384, 2392, 2400, 2407}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


def pearson(left: bytes, right: bytes) -> float:
    n = min(len(left), len(right))

    if n == 0:
        return 0.0

    a = left[:n]
    b = right[:n]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    num = 0.0
    den_a = 0.0
    den_b = 0.0

    for x, y in zip(a, b):
        da = x - mean_a
        db = y - mean_b

        num += da * db
        den_a += da * da
        den_b += db * db

    if den_a == 0 or den_b == 0:
        return 0.0

    return num / math.sqrt(den_a * den_b)


def mae(left: bytes, right: bytes) -> float:
    n = min(len(left), len(right))

    if n == 0:
        return 0.0

    return sum(
        abs(x - y)
        for x, y in zip(left[:n], right[:n])
    ) / n


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

            page_index = f56 // 9

            if not 0 <= page_index < full_pages:
                continue

            data_page = raw[
                page_index * PAGE_SIZE:
                (page_index + 1) * PAGE_SIZE
            ]

            rows_by_tile[tile_id].append({
                "file": str(path.relative_to(CACHE)),
                "page": page_index,
                "base": tile_id - page_index,
                "payload": data_page[HEADER_SIZE:],
            })


print("=" * 120)
print("PARALLEL TILE PAGE CORRELATION")
print("=" * 120)

for tile_id in sorted(rows_by_tile):
    rows = sorted(
        rows_by_tile[tile_id],
        key=lambda row: (row["page"], row["file"])
    )

    print()
    print("-" * 120)
    print(f"TILE {tile_id}")
    print("-" * 120)

    for left_index in range(len(rows)):
        for right_index in range(left_index + 1, len(rows)):
            left = rows[left_index]
            right = rows[right_index]

            direct_corr = pearson(left["payload"], right["payload"])
            inverted = bytes(255 - value for value in right["payload"])
            inverted_corr = pearson(left["payload"], inverted)

            print(
                f"{left_index:02d}<->{right_index:02d} "
                f"page_delta={right['page'] - left['page']:+4d} "
                f"corr={direct_corr:+.5f} "
                f"inverted_corr={inverted_corr:+.5f} "
                f"mae={mae(left['payload'], right['payload']):7.3f}"
            )

            print(
                f"  A file={left['file']} page={left['page']} base={left['base']}"
            )
            print(
                f"  B file={right['file']} page={right['page']} base={right['base']}"
            )
