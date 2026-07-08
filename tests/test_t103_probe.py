from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F05" / "T103.ithmb"

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T103 PROBE")
    print("=" * 100)
    print(f"size: {len(data)}")
    print()

    print("FIRST 512 BYTES")
    print("-" * 100)
    for off in range(0, 512, 16):
        chunk = data[off:off+16]
        hx = " ".join(f"{x:02x}" for x in chunk)
        print(f"0x{off:08x}: {hx}")

    print()
    print("U16 PATTERN FIRST 256 BYTES")
    print("-" * 100)
    for off in range(0, 256, 2):
        print(f"0x{off:08x}: {u16le(data, off):5d} 0x{u16le(data, off):04x}")

    print()
    print("ZERO RUNS")
    print("-" * 100)

    runs = []
    i = 0
    while i < len(data):
        if data[i] == 0:
            start = i
            while i < len(data) and data[i] == 0:
                i += 1
            runs.append((start, i - start))
        else:
            i += 1

    for start, ln in sorted(runs, key=lambda x: x[1], reverse=True)[:40]:
        print(f"0x{start:08x} len={ln}")

    print()
    print("TOP U16 VALUES")
    print("-" * 100)
    vals = [u16le(data, off) for off in range(0, len(data)-1, 2)]
    for v, c in Counter(vals).most_common(30):
        print(f"0x{v:04x} {v:6d} count={c}")

if __name__ == "__main__":
    main()
