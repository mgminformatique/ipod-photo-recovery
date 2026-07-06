from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F00" / "T149.ithmb"

TILE_MIN = 2304
TILE_MAX = 2431

def u16le(data, off):
    if off + 2 > len(data):
        return None
    return struct.unpack_from("<H", data, off)[0]

def main():
    data = FILE.read_bytes()

    hits = []

    for off in range(len(data) - 2):
        v = u16le(data, off)
        if TILE_MIN <= v <= TILE_MAX:
            hits.append((off, v))

    print("=" * 80)
    print("TILE RECORD SPACING")
    print("=" * 80)
    print(f"hits: {len(hits)}")
    print()

    deltas = []

    for i in range(1, len(hits)):
        d = hits[i][0] - hits[i-1][0]
        deltas.append(d)

    counts = Counter(deltas)

    print("MOST COMMON SPACINGS")
    print("-" * 80)

    for spacing, count in counts.most_common(30):
        print(f"{spacing:6d} bytes : {count}")

    print()
    print("FIRST 100 HITS")
    print("-" * 80)

    for off, tile in hits[:100]:
        print(f"0x{off:08x} tile={tile}")

if __name__ == "__main__":
    main()
