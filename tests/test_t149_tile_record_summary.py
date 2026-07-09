from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 TILE RECORD SUMMARY")
    print("=" * 100)

    tiles = []

    for i in range(COUNT):
        off = START + i * RECORD_SIZE
        v = [u16le(data, off + j) for j in range(0, RECORD_SIZE, 2)]
        tiles.append((i, off, v[0], v[1], v))

    print("tile counts:")
    for tile, count in Counter(t for _, _, t, _, _ in tiles).most_common():
        print(f"tile={tile} count={count}")

    print()
    print("records grouped:")
    current = None
    for i, off, tile, idx, v in tiles:
        if tile != current:
            print()
            print(f"tile {tile} starts at record {i}, off=0x{off:08x}")
            current = tile
        print(f"  rec={i:03d} idx={idx:4d} vals={v}")

if __name__ == "__main__":
    main()
