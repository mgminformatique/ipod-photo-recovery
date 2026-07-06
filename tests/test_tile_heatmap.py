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

def main():
    data = DB.read_bytes()

    hits = []
    for off in range(0, len(data) - 2):
        v = u16le(data, off)
        if v is not None and TILE_MIN <= v <= TILE_MAX:
            hits.append((off, v))

    print("=" * 100)
    print("TILE HEATMAP")
    print("=" * 100)
    print(f"database size: {len(data)}")
    print(f"tile hits: {len(hits)}")
    print()

    for block_size in [256, 512, 1024, 2048, 4096]:
        print("=" * 100)
        print(f"BLOCK SIZE {block_size}")
        print("=" * 100)

        blocks = defaultdict(list)

        for off, tile_id in hits:
            block_start = (off // block_size) * block_size
            blocks[block_start].append((off, tile_id))

        hot_blocks = sorted(blocks.items(), key=lambda x: len(x[1]), reverse=True)

        print("top hot blocks:")
        print("-" * 100)

        for block_start, items in hot_blocks[:30]:
            block_end = min(len(data), block_start + block_size)
            unique_ids = sorted(set(t for _, t in items))

            print(
                f"0x{block_start:08x}-0x{block_end:08x} "
                f"hits={len(items):3d} "
                f"unique={len(unique_ids):3d} "
                f"ids={unique_ids[:20]}"
            )

        print()

    print("=" * 100)
    print("ORDERED TILE HIT MAP")
    print("=" * 100)

    for off, tile_id in hits:
        print(f"0x{off:08x} tile_id={tile_id} hex=0x{tile_id:04x}")


if __name__ == "__main__":
    main()
