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
            reference = struct.unpack_from(">I", record, 0x6C)[0]

            rows_by_file[str(path.relative_to(CACHE))].append({
                "page": page_index,
                "record": record_index,
                "tile_id": tile_id,
                "f56": f56,
                "reference": reference,
                "constant": f56 - 9 * tile_id,
            })


print("=" * 120)
print("PAYLOAD F56 VS TILE ID RELATION")
print("=" * 120)

all_constants = Counter()

for filename, rows in sorted(rows_by_file.items()):
    rows.sort(key=lambda row: row["tile_id"])

    constants = Counter(row["constant"] for row in rows)
    best_constant, best_count = constants.most_common(1)[0]

    all_constants.update(constants)

    print()
    print("-" * 120)
    print(filename)
    print(
        f"records={len(rows)} "
        f"tiles={rows[0]['tile_id']}-{rows[-1]['tile_id']} "
        f"best_constant={best_constant} "
        f"matches={best_count}/{len(rows)} "
        f"{best_count / len(rows) * 100:.2f}%"
    )

    print(
        "tile  f56  predicted  residual  constant  page  rec  reference"
    )

    for row in rows:
        predicted = 9 * row["tile_id"] + best_constant
        residual = row["f56"] - predicted

        marker = "" if residual == 0 else "  <--"

        print(
            f"{row['tile_id']:4d} "
            f"{row['f56']:5d} "
            f"{predicted:9d} "
            f"{residual:+8d} "
            f"{row['constant']:9d} "
            f"{row['page']:5d} "
            f"{row['record']:3d} "
            f"0x{row['reference']:08x}"
            f"{marker}"
        )

    print()
    print("constant distribution:")

    for constant, count in constants.most_common():
        print(
            f"  constant={constant:7d} "
            f"count={count:3d}"
        )

print()
print("=" * 120)
print("GLOBAL CONSTANT DISTRIBUTION")
print("=" * 120)

for constant, count in all_constants.most_common():
    print(
        f"constant={constant:7d} "
        f"count={count:4d}"
    )
