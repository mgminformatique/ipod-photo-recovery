from pathlib import Path
import struct

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

BLOCKS = [
    0x7700,
    0x7800,
    0x7900,
    0x7A00,
    0x7B00,
    0x7C00,
    0x7D00,
]

data = FILE.read_bytes()

print("=" * 100)
print("BLOCK EXPAND")
print("=" * 100)

for off in BLOCKS:

    print()
    print("-" * 100)
    print(f"BLOCK {off:#08x}")

    block = data[off:off + 0x100]

    values = []

    for i in range(0, len(block), 2):
        v = struct.unpack_from("<H", block, i)[0]
        values.append(v)

    for i, v in enumerate(values):

        if v != 0:
            print(f"{i:03d} : {v:5d} 0x{v:04x}")
