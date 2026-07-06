from pathlib import Path
import struct
from collections import defaultdict

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

TILE_MIN = 2304
TILE_MAX = 2431

def u16le(b, off):
    if off + 2 > len(b):
        return None
    return struct.unpack_from("<H", b, off)[0]

def hexline(data, base_off):
    parts = []
    for i, x in enumerate(data):
        parts.append(f"{x:02x}")
    return f"0x{base_off:08x}: " + " ".join(parts)

def ascii_preview(data):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in data)

def main():
    data = DB.read_bytes()

    hits = []
    for off in range(0, len(data) - 2):
        v = u16le(data, off)
        if v is not None and TILE_MIN <= v <= TILE_MAX:
            hits.append((off, v))

    print("=" * 100)
    print("TILE CONTEXT")
    print("=" * 100)
    print(f"database size: {len(data)}")
    print(f"tile hits: {len(hits)}")
    print()

    # Group by byte position modulo common block sizes
    for size in [8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 256]:
        groups = defaultdict(int)
        for off, _ in hits:
            groups[off % size] += 1

        best_mod, best_count = max(groups.items(), key=lambda x: x[1])
        print(f"mod {size:3d}: best offset {best_mod:3d} = {best_count} hits")

    print()
    print("=" * 100)
    print("FIRST 80 TILE CONTEXTS")
    print("=" * 100)

    for idx, (off, tile_id) in enumerate(hits[:80], 1):
        start = max(0, off - 32)
        end = min(len(data), off + 34)
        ctx = data[start:end]

        print()
        print("-" * 100)
        print(f"#{idx} tile_id={tile_id} at 0x{off:08x}")
        print(f"context start 0x{start:08x} end 0x{end:08x}")
        print(hexline(ctx, start))
        print("ascii:", ascii_preview(ctx))

        # Decode small numbers around hit
        print("nearby u16LE:")
        nearby = []
        for p in range(max(0, off - 16), min(len(data) - 2, off + 18), 2):
            val = u16le(data, p)
            marker = "<-- tile" if p == off else ""
            nearby.append(f"+{p-off:+03d}=0x{val:04x}/{val}{marker}")
        print(" ".join(nearby))

    print()
    print("=" * 100)
    print("TILE IDS FOUND")
    print("=" * 100)
    unique = sorted(set(v for _, v in hits))
    print(unique)
    print(f"unique count: {len(unique)}")


if __name__ == "__main__":
    main()
