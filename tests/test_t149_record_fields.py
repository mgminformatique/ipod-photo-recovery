from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F00" / "T149.ithmb"

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 RECORD FIELD ANALYSIS")
    print("=" * 100)

    fields = [[] for _ in range(12)]

    for i in range(COUNT):
        off = START + i * RECORD_SIZE
        chunk = data[off:off + RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        vals = [u16le(chunk, j) for j in range(0, RECORD_SIZE, 2)]

        for idx, v in enumerate(vals):
            fields[idx].append(v)

    for idx, values in enumerate(fields):
        c = Counter(values)
        unique = sorted(c.keys())

        print()
        print("-" * 100)
        print(f"FIELD +{idx*2:02d}")
        print(f"count={len(values)} unique={len(unique)}")
        print(f"min={min(values)} max={max(values)}")
        print("top values:", c.most_common(20))
        print("first 60:", values[:60])

    print()
    print("=" * 100)
    print("FIRST 120 RECORDS COMPACT")
    print("=" * 100)

    for i in range(120):
        off = START + i * RECORD_SIZE
        chunk = data[off:off + RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        v = [u16le(chunk, j) for j in range(0, RECORD_SIZE, 2)]

        print(
            f"#{i:03d} off=0x{off:08x} "
            f"id={v[0]} idx={v[1]} "
            f"A=({v[2]},{v[3]}) "
            f"B=({v[4]},{v[5]}) "
            f"C=({v[6]},{v[7]}) "
            f"D=({v[8]},{v[9]}) "
            f"E=({v[10]},{v[11]})"
        )

if __name__ == "__main__":
    main()
