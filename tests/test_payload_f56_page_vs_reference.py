from pathlib import Path
import struct
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

MARKERS = {
    0x00000000: "ZERO",
    0x0D000000: "0D",
}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


relations = Counter()
rows = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    pages = []

    for page_index in range(full_pages):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        pages.append(
            struct.unpack_from(">I", page, 0)[0]
        )

    if not pages:
        continue

    first_header = pages[0]

    for table_page in range(full_pages):
        page = raw[
            table_page * PAGE_SIZE:
            (table_page + 1) * PAGE_SIZE
        ]

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

            if not (0 <= data_page < full_pages):
                data_type = "OUTSIDE"
            else:
                data_type = MARKERS.get(
                    pages[data_page],
                    "NORMAL",
                )

            if 0 <= reference_page < full_pages:
                reference_type = MARKERS.get(
                    pages[reference_page],
                    "NORMAL",
                )
            else:
                reference_type = "OUTSIDE"

            delta = data_page - reference_page

            if delta < 0:
                relation = "BEFORE_REFERENCE"
            elif delta > 0:
                relation = "AFTER_REFERENCE"
            else:
                relation = "ON_REFERENCE"

            relations[
                (
                    relation,
                    delta,
                    data_type,
                    reference_type,
                )
            ] += 1

            rows.append({
                "file": str(path.relative_to(CACHE)),
                "tile_id": tile_id,
                "table_page": table_page,
                "record": record_index,
                "f56": f56,
                "data_page": data_page,
                "data_type": data_type,
                "reference": reference,
                "reference_page": reference_page,
                "reference_type": reference_type,
                "delta": delta,
                "relation": relation,
            })


print("=" * 135)
print("PAYLOAD F56 PAGE VS REFERENCE")
print("=" * 135)
print(f"records={len(rows)}")
print()

print("=" * 135)
print("DELTA DISTRIBUTION")
print("=" * 135)

delta_counts = Counter(row["delta"] for row in rows)

for delta, count in delta_counts.most_common():
    print(
        f"delta={delta:+6d} "
        f"count={count:3d}"
    )

print()
print("=" * 135)
print("RELATION DISTRIBUTION")
print("=" * 135)

relation_counts = Counter(row["relation"] for row in rows)

for relation, count in relation_counts.most_common():
    print(
        f"{relation:18s} "
        f"{count:3d}/{len(rows):3d} "
        f"{count / len(rows) * 100:6.2f}%"
    )

print()
print("=" * 135)
print("ROWS")
print("=" * 135)

for row in sorted(
    rows,
    key=lambda value: (
        value["file"],
        value["tile_id"],
    ),
):
    print(
        f"file={row['file']:18s} "
        f"tile={row['tile_id']:4d} "
        f"table={row['table_page']:4d} "
        f"rec={row['record']} "
        f"data_page={row['data_page']:4d} "
        f"data_type={row['data_type']:7s} "
        f"ref_page={row['reference_page']:5d} "
        f"ref_type={row['reference_type']:7s} "
        f"delta={row['delta']:+6d} "
        f"{row['relation']}"
    )
