from pathlib import Path
import struct
from collections import defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
DB = CACHE / "Photo Database"

PAGE_SIZE = 0x400
HEADER_SIZE = 4

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8
ENTRY_SIZE = 9


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


db = DB.read_bytes()

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

            if f56 % ENTRY_SIZE:
                continue

            index9 = f56 // ENTRY_SIZE

            rows.append({
                "tile_id": tile_id,
                "index9": index9,
                "file": str(path.relative_to(CACHE)),
                "page": page_index,
                "record": record_index,
            })


print("=" * 140)
print("PHOTO DATABASE 9-BYTE ENTRY TEST")
print("=" * 140)
print(f"database bytes={len(db)}")
print(f"candidate rows={len(rows)}")
print()

seen = set()

for row in sorted(rows, key=lambda value: (value["index9"], value["tile_id"])):
    key = (row["index9"], row["tile_id"])

    if key in seen:
        continue

    seen.add(key)

    offset = row["index9"] * ENTRY_SIZE
    entry = db[offset:offset + ENTRY_SIZE]

    print(
        f"tile={row['tile_id']:4d} "
        f"index9={row['index9']:4d} "
        f"offset=0x{offset:06x} "
        f"file={row['file']} "
        f"page={row['page']:4d} "
        f"rec={row['record']}"
    )

    if len(entry) != ENTRY_SIZE:
        print("  OUTSIDE DATABASE")
        continue

    print(
        "  bytes="
        + " ".join(f"{value:02x}" for value in entry)
    )

    u8 = list(entry)

    print(
        "  u8="
        + " ".join(f"{value:3d}" for value in u8)
    )

    for start in range(0, ENTRY_SIZE - 1):
        if start + 2 <= ENTRY_SIZE:
            le16 = struct.unpack_from("<H", entry, start)[0]
            be16 = struct.unpack_from(">H", entry, start)[0]

            if 2304 <= le16 <= 2431 or 2304 <= be16 <= 2431:
                print(
                    f"  possible tile at +{start}: "
                    f"LE={le16} BE={be16}"
                )

    print()

print("=" * 140)
print("SAME TILE ACROSS PARALLEL INDEXES")
print("=" * 140)

by_tile = defaultdict(list)

for row in rows:
    by_tile[row["tile_id"]].append(row)

for tile_id in sorted(by_tile):
    indexes = sorted(set(row["index9"] for row in by_tile[tile_id]))

    if len(indexes) < 2:
        continue

    print(f"tile={tile_id} indexes={indexes}")

    for index9 in indexes:
        offset = index9 * ENTRY_SIZE
        entry = db[offset:offset + ENTRY_SIZE]

        print(
            f"  index9={index9:4d} "
            f"offset=0x{offset:06x} "
            f"bytes={entry.hex(' ')}"
        )
