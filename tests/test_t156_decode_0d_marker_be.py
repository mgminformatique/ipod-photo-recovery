from pathlib import Path
import struct

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
MARKER_PAGES = [358, 783]

raw = SRC.read_bytes()
buffers = []

print("=" * 100)
print("T156 0D MARKER BIG-ENDIAN ANALYSIS")
print("=" * 100)

for page_index in MARKER_PAGES:
    offset = page_index * PAGE_SIZE
    page = raw[offset:offset + PAGE_SIZE]

    header = struct.unpack_from(">I", page, 0)[0]
    payload = page[HEADER_SIZE:]

    buffers.append(payload)

    values = [
        struct.unpack_from(">H", payload, off)[0]
        for off in range(0, len(payload) - 1, 2)
    ]

    nonzero = [
        (index * 2, value)
        for index, value in enumerate(values)
        if value != 0
    ]

    print()
    print("-" * 100)
    print(
        f"page={page_index} "
        f"file_offset=0x{offset:08x} "
        f"header=0x{header:08x}"
    )
    print(f"payload bytes={len(payload)}")
    print(f"nonzero u16 values={len(nonzero)}")
    print()

    print("NONZERO BIG-ENDIAN U16 VALUES")
    for off, value in nonzero:
        print(
            f"off=0x{off:03x} "
            f"value={value:5d} "
            f"hex=0x{value:04x}"
        )

    print()
    print("DELTAS BETWEEN CONSECUTIVE NONZERO VALUES")

    for index in range(1, len(nonzero)):
        previous_off, previous_value = nonzero[index - 1]
        current_off, current_value = nonzero[index]

        print(
            f"0x{previous_off:03x}->0x{current_off:03x} "
            f"{previous_value:5d}->{current_value:5d} "
            f"delta={current_value - previous_value:+6d}"
        )

print()
print("=" * 100)
print("MARKER COMPARISON")
print("=" * 100)

if len(buffers) == 2:
    changed = [
        index
        for index, (left, right) in enumerate(zip(buffers[0], buffers[1]))
        if left != right
    ]

    print(f"identical={buffers[0] == buffers[1]}")
    print(f"changed bytes={len(changed)}")

    if changed:
        print(
            "changed offsets: "
            + " ".join(f"0x{offset:03x}" for offset in changed[:100])
        )
