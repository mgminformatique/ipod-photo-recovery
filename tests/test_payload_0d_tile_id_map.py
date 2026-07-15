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
tile_locations = defaultdict(list)

print("=" * 120)
print("PAYLOAD 0D TILE ID MAP")
print("=" * 120)

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()

    full_pages = len(raw) // PAGE_SIZE

    marker_count = 0

    for page_index in range(full_pages):
        start = page_index * PAGE_SIZE
        page = raw[start:start + PAGE_SIZE]

        header = struct.unpack_from(">I", page, 0)[0]

        if header != 0x0D000000:
            continue

        marker_count += 1
        payload = page[HEADER_SIZE:]

        tile_ids = []
        references = []
        f56_values = []

        for record_index in range(RECORD_COUNT):
            record_start = RECORD_START + record_index * RECORD_SIZE
            record = payload[
                record_start:
                record_start + RECORD_SIZE
            ]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]
            f56 = struct.unpack_from(">H", record, 0x56)[0]
            reference = struct.unpack_from(">I", record, 0x6C)[0]

            tile_ids.append(tile_id)
            f56_values.append(f56)
            references.append(reference)

            tile_locations[tile_id].append({
                "file": str(path.relative_to(CACHE)),
                "page": page_index,
                "record": record_index,
                "f56": f56,
                "reference": reference,
            })

        rows.append({
            "file": str(path.relative_to(CACHE)),
            "page": page_index,
            "tile_ids": tile_ids,
            "f56": f56_values,
            "references": references,
        })

    print(
        f"{path.relative_to(CACHE)!s:18s} "
        f"pages={full_pages:4d} "
        f"0D_markers={marker_count:2d}"
    )

print()
print("=" * 120)
print("0D TABLES")
print("=" * 120)

for row in rows:
    tile_ids = row["tile_ids"]
    references = row["references"]
    f56_values = row["f56"]

    ascending = sorted(tile_ids)

    print("-" * 120)
    print(
        f"file={row['file']} "
        f"page={row['page']:4d} "
        f"tiles_raw={tile_ids} "
        f"tiles_sorted={ascending}"
    )

    for index, (tile_id, f56, reference) in enumerate(
        zip(tile_ids, f56_values, references)
    ):
        print(
            f"  rec={index:02d} "
            f"tile_id={tile_id:4d} "
            f"f56={f56:5d} "
            f"reference=0x{reference:08x}"
        )

print()
print("=" * 120)
print("TILE ID SUMMARY")
print("=" * 120)

all_tile_ids = sorted(tile_locations)

print(f"unique tile IDs: {len(all_tile_ids)}")

if all_tile_ids:
    print(f"minimum: {all_tile_ids[0]}")
    print(f"maximum: {all_tile_ids[-1]}")

print(
    "tile IDs: "
    + " ".join(str(value) for value in all_tile_ids)
)

print()
print("missing IDs inside 2304-2431:")

missing = [
    tile_id
    for tile_id in range(2304, 2432)
    if tile_id not in tile_locations
]

print(
    "none"
    if not missing
    else " ".join(str(value) for value in missing)
)

print()
print("duplicate tile IDs:")

duplicates = {
    tile_id: locations
    for tile_id, locations in tile_locations.items()
    if len(locations) > 1
}

if not duplicates:
    print("none")
else:
    for tile_id, locations in sorted(duplicates.items()):
        print(f"tile_id={tile_id}")

        for location in locations:
            print(
                f"  file={location['file']} "
                f"page={location['page']} "
                f"record={location['record']} "
                f"f56={location['f56']} "
                f"reference=0x{location['reference']:08x}"
            )

print()
print("=" * 120)
print("CONTIGUOUS TILE RUNS")
print("=" * 120)

if all_tile_ids:
    run_start = all_tile_ids[0]
    previous = all_tile_ids[0]

    for tile_id in all_tile_ids[1:]:
        if tile_id == previous + 1:
            previous = tile_id
            continue

        print(
            f"{run_start}-{previous} "
            f"count={previous - run_start + 1}"
        )

        run_start = tile_id
        previous = tile_id

    print(
        f"{run_start}-{previous} "
        f"count={previous - run_start + 1}"
    )
