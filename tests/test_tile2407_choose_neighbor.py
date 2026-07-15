from pathlib import Path
import struct

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F22/T171.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

REFERENCE_PAGE = 622
F56 = 2034

raw = SRC.read_bytes()

pages = []

for page_index, offset in enumerate(range(0, len(raw), PAGE_SIZE)):
    page = raw[offset:offset + PAGE_SIZE]

    if len(page) != PAGE_SIZE:
        continue

    pages.append({
        "index": page_index,
        "header": struct.unpack_from(">I", page, 0)[0],
        "payload": page[HEADER_SIZE:],
    })

FIRST_HEADER = pages[0]["header"]

objects = {
    "before": (570, 621),
    "after": (623, 674),
}

print("=" * 110)
print("TILE 2407 CHOOSE NEIGHBOR")
print("=" * 110)
print(f"first_header=0x{FIRST_HEADER:08x}")
print(f"reference_page={REFERENCE_PAGE}")
print(f"f56={F56}")
print()

for name, (start_page, end_page) in objects.items():
    first = pages[start_page]
    last = pages[end_page]

    logical_first = first["header"] - FIRST_HEADER
    logical_last = last["header"] - FIRST_HEADER

    print("-" * 110)
    print(name.upper())
    print(f"pages={start_page}-{end_page}")
    print(
        f"headers=0x{first['header']:08x}"
        f" -> 0x{last['header']:08x}"
    )
    print(
        f"logical headers={logical_first}"
        f" -> {logical_last}"
    )

    candidates = {
        "physical_start": start_page,
        "physical_end": end_page,
        "logical_start": logical_first,
        "logical_end": logical_last,
        "header_start_low16": first["header"] & 0xFFFF,
        "header_end_low16": last["header"] & 0xFFFF,
    }

    for label, value in candidates.items():
        print(
            f"  {label:20s}={value:5d} "
            f"f56-value={F56-value:+6d}"
        )

print()
print("=" * 110)
print("NEARBY PAGE TABLE")
print("=" * 110)

for page_index in range(565, 681):
    page = pages[page_index]
    logical = page["header"] - FIRST_HEADER

    marker = ""

    if page["header"] == 0x00000000:
        marker = "ZERO"
    elif page["header"] == 0x0D000000:
        marker = "0D"

    print(
        f"page={page_index:4d} "
        f"header=0x{page['header']:08x} "
        f"logical={logical:6d} "
        f"low16={page['header'] & 0xffff:5d} "
        f"{marker}"
    )
