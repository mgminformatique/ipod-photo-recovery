from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

TILE_MIN = 2304
TILE_MAX = 2431

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 TILE CLUSTERS")
    print("=" * 100)

    hits = []

    for off in range(0, len(data) - 64, 2):
        vals = [u16le(data, off + i * 2) for i in range(32)]
        count = sum(TILE_MIN <= v <= TILE_MAX for v in vals)

        if count >= 8:
            hits.append((off, count, vals))

    print(f"clusters found: {len(hits)}")
    print()

    for off, count, vals in hits[:100]:
        print("-" * 100)
        print(f"off=0x{off:08x} tile_values={count}")
        print(" ".join(f"{v:04d}" if TILE_MIN <= v <= TILE_MAX else "----"
                       for v in vals))

if __name__ == "__main__":
    main()
