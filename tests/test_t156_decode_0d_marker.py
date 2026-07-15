from pathlib import Path
import struct

SRC = Path("output/T156_strip1k.bin")

PAGE_SIZE = 1020

data = SRC.read_bytes()

# Les deux pages 0D trouvées précédemment
marker_pages = [358, 783]

print("=" * 100)
print("T156 0D MARKER DECODER")
print("=" * 100)

for page in marker_pages:

    start = page * PAGE_SIZE
    buf = data[start:start + PAGE_SIZE]

    print()
    print("-" * 100)
    print(f"PAGE {page}")
    print("-" * 100)

    print("first 64 bytes:")
    print(" ".join(f"{b:02x}" for b in buf[:64]))
    print()

    print("u16 little endian:")
    for i in range(0, 64, 2):
        value = struct.unpack_from("<H", buf, i)[0]
        print(f"{i:04x}: {value:5d} (0x{value:04x})")

    print()
    print("u32 little endian:")
    for i in range(0, 64, 4):
        value = struct.unpack_from("<I", buf, i)[0]
        print(f"{i:04x}: {value:10d} (0x{value:08x})")

    print()
    print("delta u16:")
    values = [
        struct.unpack_from("<H", buf, i)[0]
        for i in range(0, 64, 2)
    ]

    for i in range(len(values) - 1):
        delta = values[i + 1] - values[i]
        print(
            f"{i:02d}: "
            f"{values[i]:5d} -> {values[i+1]:5d}   "
            f"delta={delta:+6d}"
        )

