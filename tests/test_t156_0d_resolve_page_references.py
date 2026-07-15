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

pages = []

for index, offset in enumerate(range(0, len(raw), PAGE_SIZE)):
    page = raw[offset:offset + PAGE_SIZE]

    if len(page) != PAGE_SIZE:
        continue

    pages.append({
        "index": index,
        "header": struct.unpack_from(">I", page, 0)[0],
    })

header_to_pages = {}

for page in pages:
    header_to_pages.setdefault(page["header"], []).append(page["index"])

print("=" * 110)
print("T156 0D RESOLVE PAGE REFERENCES")
print("=" * 110)
print(f"pages={len(pages)}")
print()

for marker_page_index in MARKER_PAGES:
    marker = raw[
        marker_page_index * PAGE_SIZE:
        (marker_page_index + 1) * PAGE_SIZE
    ]

    payload = marker[HEADER_SIZE:]

    print("-" * 110)
    print(f"0D PAGE {marker_page_index}")
    print("-" * 110)

    for record_index in range(RECORD_COUNT):
        start = RECORD_START + record_index * RECORD_SIZE
        record = payload[start:start + RECORD_SIZE]

        f04_le16 = struct.unpack_from("<H", record, 0x04)[0]
        f56_be16 = struct.unpack_from(">H", record, 0x56)[0]
        page_reference = struct.unpack_from(">I", record, 0x6C)[0]

        exact_pages = header_to_pages.get(page_reference, [])

        # Le compteur idéal de T156 commence avec le header de la page 0.
        first_header = pages[0]["header"]
        calculated_index = page_reference - first_header

        actual_header = None
        marker_type = None

        if 0 <= calculated_index < len(pages):
            actual_header = pages[calculated_index]["header"]

            if actual_header == 0x00000000:
                marker_type = "ZERO"
            elif actual_header == 0x0D000000:
                marker_type = "0D"
            else:
                marker_type = "NORMAL"

        print(
            f"record={record_index:02d} "
            f"f04_le16={f04_le16:4d} "
            f"f56_be16={f56_be16:4d} "
            f"reference=0x{page_reference:08x} "
            f"calculated_page={calculated_index:4d} "
            f"actual_header="
            f"{f'0x{actual_header:08x}' if actual_header is not None else 'OUTSIDE'} "
            f"type={marker_type or 'OUTSIDE'} "
            f"exact_header_hits={exact_pages}"
        )

    print()
