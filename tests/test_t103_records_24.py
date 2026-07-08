from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F05" / "T103.ithmb"

RECORD_SIZE = 24

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T103 24-BYTE RECORDS")
    print("=" * 100)
    print(f"size: {len(data)}")
    print(f"size % 24 = {len(data) % RECORD_SIZE}")
    print(f"records floor: {len(data) // RECORD_SIZE}")
    print()

    print("FIRST 80 RECORDS")
    print("-" * 100)

    for i in range(80):
        off = i * RECORD_SIZE
        chunk = data[off:off + RECORD_SIZE]
        vals = [u16le(chunk, j) for j in range(0, RECORD_SIZE, 2)]
        print(f"#{i:04d} off=0x{off:08x} u16={vals}")

    print()
    print("RECORD SIGNATURE COUNTS FIRST 500")
    print("-" * 100)

    sigs = Counter()
    for i in range(min(500, len(data) // RECORD_SIZE)):
        off = i * RECORD_SIZE
        chunk = data[off:off + RECORD_SIZE]
        sigs[chunk[:12]] += 1

    for sig, count in sigs.most_common(20):
        print(f"count={count:4d} sig={sig.hex()}")

if __name__ == "__main__":
    main()
