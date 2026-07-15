from pathlib import Path
import struct
from collections import Counter

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
MARKER_PAGES = [358, 783]

raw = SRC.read_bytes()
payloads = []

for page_index in MARKER_PAGES:
    offset = page_index * PAGE_SIZE
    page = raw[offset:offset + PAGE_SIZE]

    header = struct.unpack_from(">I", page, 0)[0]

    if header != 0x0D000000:
        raise SystemExit(
            f"Page {page_index}: mauvais header 0x{header:08x}"
        )

    payloads.append(page[HEADER_SIZE:])

left, right = payloads

print("=" * 110)
print("T156 COMPARE 0D RECORDS")
print("=" * 110)
print(f"payload bytes: {len(left)}")
print(f"identical: {left == right}")

changed = [
    offset
    for offset, (a, b) in enumerate(zip(left, right))
    if a != b
]

print(f"changed bytes: {len(changed)}")
print()

print("CHANGED BYTE OFFSETS")
print("-" * 110)

for offset in changed:
    print(
        f"off=0x{offset:03x} "
        f"A=0x{left[offset]:02x} "
        f"B=0x{right[offset]:02x} "
        f"delta={right[offset] - left[offset]:+4d}"
    )

print()
print("DISTANCES BETWEEN CHANGED OFFSETS")
print("-" * 110)

distances = []

for index in range(1, len(changed)):
    distance = changed[index] - changed[index - 1]
    distances.append(distance)

    print(
        f"0x{changed[index - 1]:03x} -> "
        f"0x{changed[index]:03x} "
        f"distance=0x{distance:x} ({distance})"
    )

print()
print("DISTANCE DISTRIBUTION")
print("-" * 110)

for distance, count in Counter(distances).most_common():
    print(
        f"distance=0x{distance:x} "
        f"decimal={distance:3d} "
        f"count={count}"
    )

print()
print("RECORD-SIZE CANDIDATES")
print("-" * 110)

# Teste différentes tailles possibles de records.
for record_size in range(0x20, 0x101, 2):
    residues = Counter(
        offset % record_size
        for offset in changed
    )

    best_residue, best_count = residues.most_common(1)[0]
    ratio = best_count / len(changed) if changed else 0

    if ratio >= 0.50:
        print(
            f"record_size=0x{record_size:02x} "
            f"({record_size:3d}) "
            f"best_field=0x{best_residue:02x} "
            f"matches={best_count}/{len(changed)} "
            f"{ratio * 100:6.2f}%"
        )

print()
print("0x70-BYTE RECORD VIEW")
print("-" * 110)

RECORD_START = 0x7c
RECORD_SIZE = 0x70

record_index = 0

for start in range(RECORD_START, len(left), RECORD_SIZE):
    end = min(start + RECORD_SIZE, len(left))

    a = left[start:end]
    b = right[start:end]

    local_changes = [
        index
        for index, (x, y) in enumerate(zip(a, b))
        if x != y
    ]

    print(
        f"record={record_index:02d} "
        f"range=0x{start:03x}-0x{end - 1:03x} "
        f"changed={len(local_changes)}"
    )

    for local_offset in local_changes:
        absolute = start + local_offset

        print(
            f"  field=0x{local_offset:02x} "
            f"absolute=0x{absolute:03x} "
            f"A=0x{a[local_offset]:02x} "
            f"B=0x{b[local_offset]:02x}"
        )

    record_index += 1
