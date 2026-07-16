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


rows = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    if full_pages == 0:
        continue

    first_header = struct.unpack_from(">I", raw, 0)[0]

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
            f56 = struct.unpack_from(">H", record, 0x56)[0]
            reference = struct.unpack_from(">I", record, 0x6C)[0]

            if f56 % 9:
                continue

            data_page = f56 // 9
            reference_page = reference - first_header
            delta = data_page - reference_page

            rows.append({
                "file": str(path.relative_to(CACHE)),
                "tile_id": tile_id,
                "table_page": table_page,
                "record": record_index,
                "data_page": data_page,
                "reference_page": reference_page,
                "delta": delta,
                "mod52": delta % 52,
                "mod53": delta % 53,
            })


print("=" * 130)
print("PAYLOAD F56/REFERENCE MODULO ANALYSIS")
print("=" * 130)
print(f"records={len(rows)}")
print()

for modulus in (52, 53):
    counts = Counter(row[f"mod{modulus}"] for row in rows)

    print("=" * 130)
    print(f"DELTA MODULO {modulus}")
    print("=" * 130)

    for remainder, count in counts.most_common():
        print(
            f"remainder={remainder:2d} "
            f"count={count:3d}/{len(rows):3d} "
            f"{count / len(rows) * 100:6.2f}%"
        )

    print()


print("=" * 130)
print("MODULO 52 BY RECORD POSITION")
print("=" * 130)

by_record = defaultdict(Counter)

for row in rows:
    by_record[row["record"]][row["mod52"]] += 1

for record_index in sorted(by_record):
    counts = by_record[record_index]
    best_remainder, best_count = counts.most_common(1)[0]

    print(
        f"record={record_index} "
        f"best_remainder={best_remainder:2d} "
        f"matches={best_count}/{sum(counts.values())} "
        f"distribution={dict(sorted(counts.items()))}"
    )


print()
print("=" * 130)
print("MODULO 52 BY TILE ID")
print("=" * 130)

by_tile = defaultdict(Counter)

for row in rows:
    by_tile[row["tile_id"]][row["mod52"]] += 1

for tile_id in sorted(by_tile):
    counts = by_tile[tile_id]
    best_remainder, best_count = counts.most_common(1)[0]

    print(
        f"tile={tile_id:4d} "
        f"best_remainder={best_remainder:2d} "
        f"matches={best_count}/{sum(counts.values())} "
        f"remainders={dict(sorted(counts.items()))}"
    )


print()
print("=" * 130)
print("EXACT 52-UNIT DECOMPOSITION")
print("=" * 130)

for row in sorted(
    rows,
    key=lambda value: (
        value["file"],
        value["tile_id"],
    ),
):
    quotient, remainder = divmod(row["delta"], 52)

    print(
        f"file={row['file']:18s} "
        f"tile={row['tile_id']:4d} "
        f"rec={row['record']} "
        f"data={row['data_page']:4d} "
        f"ref={row['reference_page']:5d} "
        f"delta={row['delta']:+6d} "
        f"52q={quotient:+4d} "
        f"52r={remainder:2d}"
    )
