from pathlib import Path
import struct

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
MARKER_PAGES = [358, 783]

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

raw = SRC.read_bytes()

first_page = raw[:PAGE_SIZE]
FIRST_HEADER = struct.unpack_from(">I", first_page, 0)[0]

print("=" * 120)
print("T156 0D FIELD RELATIONS")
print("=" * 120)
print(f"first logical header: 0x{FIRST_HEADER:08x}")
print()

for marker_page_index in MARKER_PAGES:
    page = raw[
        marker_page_index * PAGE_SIZE:
        (marker_page_index + 1) * PAGE_SIZE
    ]
    payload = page[HEADER_SIZE:]

    print("-" * 120)
    print(f"0D PAGE {marker_page_index}")
    print("-" * 120)

    rows = []

    for record_index in range(RECORD_COUNT):
        start = RECORD_START + record_index * RECORD_SIZE
        record = payload[start:start + RECORD_SIZE]

        f04 = struct.unpack_from("<H", record, 0x04)[0]
        f56 = struct.unpack_from(">H", record, 0x56)[0]
        ref = struct.unpack_from(">I", record, 0x6C)[0]
        logical_page = ref - FIRST_HEADER

        rows.append((record_index, f04, f56, ref, logical_page))

    print(
        "rec  logical_page  f04   f56   "
        "f04-page  f56-page  "
        "f56-f04  "
        "page%53  page//53"
    )

    for rec, f04, f56, ref, logical_page in rows:
        print(
            f"{rec:02d}   "
            f"{logical_page:11d} "
            f"{f04:5d} "
            f"{f56:5d} "
            f"{f04-logical_page:8d} "
            f"{f56-logical_page:8d} "
            f"{f56-f04:8d} "
            f"{logical_page % 53:7d} "
            f"{logical_page // 53:8d}"
        )

    print()
    print("DELTAS BETWEEN RECORDS")
    print(
        "rec pair   d_page   d_f04   d_f56   "
        "d(f04-page)   d(f56-page)"
    )

    for index in range(1, len(rows)):
        prev = rows[index - 1]
        cur = rows[index]

        prev_page = prev[4]
        cur_page = cur[4]

        print(
            f"{index-1:02d}->{index:02d}   "
            f"{cur_page-prev_page:+6d} "
            f"{cur[1]-prev[1]:+7d} "
            f"{cur[2]-prev[2]:+7d} "
            f"{(cur[1]-cur_page)-(prev[1]-prev_page):+13d} "
            f"{(cur[2]-cur_page)-(prev[2]-prev_page):+13d}"
        )

    print()
