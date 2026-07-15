from pathlib import Path
import struct
from collections import Counter

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")
OUT = Path("output/t156_1k_objects")
OUT.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 0x400
HEADER_SIZE = 4

MARKERS = {
    0x00000000: "ZERO",
    0x0D000000: "0D",
}

raw = SRC.read_bytes()
pages = []

for page_index, off in enumerate(range(0, len(raw), PAGE_SIZE)):
    page = raw[off:off + PAGE_SIZE]

    if len(page) != PAGE_SIZE:
        continue

    pages.append({
        "index": page_index,
        "offset": off,
        "header": struct.unpack(">I", page[:4])[0],
        "data": page[4:],
    })

marker_indexes = [
    index
    for index, page in enumerate(pages)
    if page["header"] in MARKERS
]

boundaries = [-1] + marker_indexes + [len(pages)]
lengths = Counter()

print("=" * 100)
print("T156 1K PAGE OBJECTS")
print("=" * 100)
print(f"full pages: {len(pages)}")
print(f"markers: {len(marker_indexes)}")
print()

object_number = 0

for boundary_index in range(len(boundaries) - 1):
    left = boundaries[boundary_index]
    right = boundaries[boundary_index + 1]

    first = left + 1
    count = right - left - 1

    if count <= 0:
        print(
            f"empty region between marker pages "
            f"{left} and {right}"
        )
        continue

    object_pages = pages[first:right]
    data = b"".join(page["data"] for page in object_pages)

    lengths[count] += 1

    output_path = OUT / (
        f"object_{object_number:02d}_"
        f"pages_{first:04d}-{right - 1:04d}_"
        f"count_{count}.bin"
    )
    output_path.write_bytes(data)

    plus1 = sum(
        object_pages[index]["header"]
        == object_pages[index - 1]["header"] + 1
        for index in range(1, len(object_pages))
    )

    total = max(0, len(object_pages) - 1)

    print("-" * 100)
    print(
        f"object={object_number:02d} "
        f"pages={first:04d}-{right - 1:04d} "
        f"count={count:3d} "
        f"data_bytes={len(data)}"
    )

    print(
        f"headers=0x{object_pages[0]['header']:08x}"
        f" -> 0x{object_pages[-1]['header']:08x}"
    )

    print(
        f"+1={plus1}/{total} "
        f"{plus1 / total * 100:.2f}%"
        if total
        else "+1=none"
    )

    print(f"saved={output_path}")

    object_number += 1

print()
print("=" * 100)
print("MARKERS")
print("=" * 100)

for index in marker_indexes:
    page = pages[index]

    print(
        f"page={index:04d} "
        f"type={MARKERS[page['header']]:4s} "
        f"offset=0x{page['offset']:08x} "
        f"first16={page['data'][:16].hex(' ')}"
    )

print()
print("=" * 100)
print("OBJECT LENGTH DISTRIBUTION")
print("=" * 100)

for length, count in sorted(lengths.items()):
    print(
        f"pages={length:3d} "
        f"objects={count:2d} "
        f"data_bytes={length * (PAGE_SIZE - HEADER_SIZE)}"
    )
