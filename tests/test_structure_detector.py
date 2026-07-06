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
    print("STRUCTURE DETECTOR")
    print("=" * 100)
    print(f"database size: {len(data)}")
    print(f"tile hits: {len(hits)}")
    print()

    results = []

    for size in range(8, 257):
        mods = defaultdict(list)

        for off, tile_id in hits:
            mods[off % size].append((off, tile_id))

        best_mod, best_hits = max(mods.items(), key=lambda x: len(x[1]))
        count = len(best_hits)
        percent = (count / len(hits)) * 100

        # Bonus: check if tile ids in this mod form useful ordered clusters
        sorted_hits = sorted(best_hits)
        deltas = []
        for i in range(1, len(sorted_hits)):
            deltas.append(sorted_hits[i][0] - sorted_hits[i - 1][0])

        common_delta = None
        common_delta_count = 0
        if deltas:
            delta_counts = defaultdict(int)
            for d in deltas:
                delta_counts[d] += 1
            common_delta, common_delta_count = max(delta_counts.items(), key=lambda x: x[1])

        results.append({
            "size": size,
            "best_mod": best_mod,
            "count": count,
            "percent": percent,
            "common_delta": common_delta,
            "common_delta_count": common_delta_count,
        })

    results.sort(key=lambda r: (r["count"], r["common_delta_count"]), reverse=True)

    print("TOP STRUCTURE SIZE CANDIDATES")
    print("-" * 100)
    print("size | mod | hits | percent | common_delta | delta_hits")
    print("-" * 100)

    for r in results[:60]:
        print(
            f"{r['size']:4d} | "
            f"{r['best_mod']:3d} | "
            f"{r['count']:4d} | "
            f"{r['percent']:6.2f}% | "
            f"{str(r['common_delta']):>12} | "
            f"{r['common_delta_count']:10d}"
        )

    print()
    print("=" * 100)
    print("BEST CANDIDATE DETAILS")
    print("=" * 100)

    for r in results[:10]:
        size = r["size"]
        mod = r["best_mod"]

        selected = [(off, tile_id) for off, tile_id in hits if off % size == mod]
        selected = sorted(selected)

        print()
        print("-" * 100)
        print(f"size={size} mod={mod} hits={len(selected)} percent={r['percent']:.2f}%")
        print("first 40 matching offsets:")

        for off, tile_id in selected[:40]:
            record_start = off - mod
            index = record_start // size
            print(
                f"tile_id={tile_id:4d} "
                f"tile_hex=0x{tile_id:04x} "
                f"off=0x{off:08x} "
                f"record_start=0x{record_start:08x} "
                f"record_index={index}"
            )


if __name__ == "__main__":
    main()
