from pathlib import Path
import struct
from collections import Counter, defaultdict

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def page_values(data, page):
    return [u16(data, page + i * 2) for i in range(128)]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 RECONSTRUCT MAPPING")
    print("=" * 100)

    pages = list(range(0x5700, 0x10000, 0x100))

    refs = defaultdict(list)
    all_values = []

    for page in pages:
        vals = page_values(data, page)
        for idx, v in enumerate(vals):
            all_values.append(v)
            if 0 <= v < len(data):
                refs[v].append((page, idx))

    print(f"pages scanned: {len(pages)}")
    print(f"values scanned: {len(all_values)}")
    print()

    print("MOST REFERENCED TARGETS")
    print("-" * 100)
    for target, hits in sorted(refs.items(), key=lambda x: len(x[1]), reverse=True)[:80]:
        if len(hits) < 2:
            continue
        print(f"target=0x{target:04x} hits={len(hits):4d} from=" + " ".join(f"0x{p:04x}[{i}]" for p, i in hits[:12]))

    print()
    print("SEQUENTIAL 0x100 RUNS INSIDE PAGES")
    print("-" * 100)

    for page in pages:
        vals = page_values(data, page)

        runs = []
        start = 0
        for i in range(1, len(vals)):
            if vals[i] - vals[i - 1] != 0x100:
                if i - start >= 6:
                    runs.append((start, i - 1, vals[start], vals[i - 1]))
                start = i

        if len(vals) - start >= 6:
            runs.append((start, len(vals) - 1, vals[start], vals[-1]))

        if runs:
            print(f"page=0x{page:04x}")
            for a, b, va, vb in runs[:10]:
                print(f"  idx {a:03d}->{b:03d} value 0x{va:04x}->0x{vb:04x} len={b-a+1}")

    print()
    print("TILE-ID LIKE VALUES 2304-2431")
    print("-" * 100)

    for tile in range(2304, 2432):
        hits = refs.get(tile, [])
        if hits:
            print(f"tile={tile} 0x{tile:04x} hits={len(hits)} " + " ".join(f"0x{p:04x}[{i}]" for p, i in hits[:20]))

    print()
    print("VALUES MOD 2304")
    print("-" * 100)

    mod_hits = []
    for v in all_values:
        if v and v % 2304 == 0:
            mod_hits.append(v)

    c = Counter(mod_hits)
    for v, n in c.most_common(80):
        print(f"value={v:5d} 0x{v:04x} hits={n}")

if __name__ == "__main__":
    main()
