from pathlib import Path
import struct
from collections import defaultdict, Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


rows = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    for page_index in range(full_pages):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
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
            f56 = struct.unpack_from(">H", record, 0x56)[0]

            if f56 % 9:
                continue

            index9 = f56 // 9
            base_id = tile_id - index9

            rows.append({
                "file": str(path.relative_to(CACHE)),
                "tile_id": tile_id,
                "index9": index9,
                "base_id": base_id,
                "page": page_index,
                "record": record_index,
            })


by_tile = defaultdict(list)

for row in rows:
    by_tile[row["tile_id"]].append(row)

print("=" * 130)
print("PAYLOAD F56 PARALLEL 128 FAMILIES")
print("=" * 130)

relation_counts = Counter()

for tile_id in sorted(by_tile):
    tile_rows = sorted(
        by_tile[tile_id],
        key=lambda row: (row["index9"], row["file"])
    )

    indexes = sorted(set(row["index9"] for row in tile_rows))
    index_set = set(indexes)

    pairs = []

    for index in indexes:
        for delta in (128, 256):
            if index + delta in index_set:
                pairs.append((index, index + delta, delta))
                relation_counts[delta] += 1

    if not pairs:
        continue

    print()
    print("-" * 130)
    print(f"tile_id={tile_id}")
    print(f"indexes={indexes}")

    for left, right, delta in pairs:
        print(
            f"  relation: {left} -> {right} "
            f"delta={delta}"
        )

        for row in tile_rows:
            if row["index9"] not in (left, right):
                continue

            print(
                f"    index9={row['index9']:4d} "
                f"base={row['base_id']:4d} "
                f"file={row['file']} "
                f"page={row['page']:4d} "
                f"record={row['record']}"
            )

print()
print("=" * 130)
print("RELATION SUMMARY")
print("=" * 130)

for delta, count in sorted(relation_counts.items()):
    print(
        f"delta={delta:3d} "
        f"relations={count}"
    )

print()
print("=" * 130)
print("INDEX RANGES BY BASE")
print("=" * 130)

by_base = defaultdict(list)

for row in rows:
    by_base[row["base_id"]].append(row["index9"])

for base_id in sorted(by_base):
    values = by_base[base_id]

    print(
        f"base={base_id:4d} "
        f"count={len(values):3d} "
        f"index9_min={min(values):4d} "
        f"index9_max={max(values):4d}"
    )
