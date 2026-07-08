from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    START = 0x7200
    END = len(data)

    print("=" * 100)
    print("T149 DENSE ZONE PROBE")
    print("=" * 100)
    print(f"range: 0x{START:08x}-0x{END:08x}")
    print(f"len: {END - START}")
    print()

    print("FIRST 512 BYTES AS U16")
    print("-" * 100)
    for off in range(START, START + 512, 16):
        vals = [u16le(data, p) for p in range(off, off + 16, 2)]
        print(f"0x{off:08x}: " + " ".join(f"{v:04x}" for v in vals))

    print()
    print("TOP U16 VALUES IN DENSE ZONE")
    print("-" * 100)
    vals = [u16le(data, off) for off in range(START, END - 1, 2)]
    for v, c in Counter(vals).most_common(40):
        print(f"0x{v:04x} {v:5d} count={c}")

if __name__ == "__main__":
    main()
