from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0x7200

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 DENSE RECORD SCAN")
    print("=" * 100)

    for size in [4, 6, 8, 10, 12, 16, 20, 24, 32]:
        print()
        print("-" * 100)
        print(f"record size {size}")

        for align in range(size):
            count_0008 = 0
            total = 0

            for off in range(START + align, len(data) - size, size):
                chunk = data[off:off+size]
                vals = [u16le(chunk, j) for j in range(0, size, 2)]
                total += 1
                if 8 in vals:
                    count_0008 += 1

            pct = count_0008 / total * 100 if total else 0
            if pct > 20:
                print(f"align={align:2d} records={total:5d} contains_0008={count_0008:5d} {pct:6.2f}%")

if __name__ == "__main__":
    main()
