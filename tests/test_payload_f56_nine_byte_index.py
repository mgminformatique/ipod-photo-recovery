from pathlib import Path
import struct
from collections import Counter, defaultdict

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


rows_by_file = defaultdict(list)

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

        header = struct.unpack_from(">I", page, 0)[0]

        if header != 0x0D000000:
            continue

        payload = page[HEADER_SIZE:]

        for record_index in range(RECORD_COUNT):
            start = RECORD_START + record_index * RECORD_SIZE
            record = payload[start:start + RECORD_SIZE]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]
            f56 = struct.unpack_from(">H", record, 0x56)[0]

            divisible = (f56 % 9 == 0)
            index9 = f56 // 9
            base_id = tile_id - index9

            rows_by_file[str(path.relative_to(CACHE))].append({
                "page": page_index,
                "record": record_index,
                "tile_id": tile_id,
                "f56": f56,
                "remainder": f56 % 9,
                "index9": index9,
                "base_id": base_id,
                "divisible": divisible,
            })


print("=" * 120)
print("PAYLOAD F56 NINE-BYTE INDEX")
print("=" * 120)

global_bases = Counter()
global_remainders = Counter()

for filename, rows in sorted(rows_by_file.items()):
    rows.sort(key=lambda row: (row["tile_id"], row["page"]))

    bases = Counter(row["base_id"] for row in rows)
    remainders = Counter(row["remainder"] for row in rows)

    global_bases.update(bases)
    global_remainders.update(remainders)

    divisible_count = sum(row["divisible"] for row in rows)

    print()
    print("-" * 120)
    print(filename)
    print(
        f"records={len(rows)} "
        f"divisible_by_9={divisible_count}/{len(rows)} "
        f"{divisible_count / len(rows) * 100:.2f}%"
    )

    print("base distribution:")

    for base_id, count in bases.most_common():
        print(
            f"  base_id={base_id:5d} "
            f"count={count:3d}"
        )

    print("remainder distribution:")

    for remainder, count in sorted(remainders.items()):
        print(
            f"  remainder={remainder} "
            f"count={count}"
        )

    print()
    print(
        "tile  f56  f56/9  rem  base_id  page  rec"
    )

    for row in rows:
        marker = "" if row["remainder"] == 0 else "  <--"

        print(
            f"{row['tile_id']:4d} "
            f"{row['f56']:5d} "
            f"{row['index9']:6d} "
            f"{row['remainder']:3d} "
            f"{row['base_id']:7d} "
            f"{row['page']:5d} "
            f"{row['record']:3d}"
            f"{marker}"
        )

print()
print("=" * 120)
print("GLOBAL BASE DISTRIBUTION")
print("=" * 120)

for base_id, count in global_bases.most_common():
    print(
        f"base_id={base_id:5d} "
        f"count={count:4d}"
    )

print()
print("=" * 120)
print("GLOBAL REMAINDER DISTRIBUTION")
print("=" * 120)

for remainder, count in sorted(global_remainders.items()):
    print(
        f"remainder={remainder} "
        f"count={count}"
    )
