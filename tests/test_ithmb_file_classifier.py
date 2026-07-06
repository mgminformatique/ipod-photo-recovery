from pathlib import Path
from collections import Counter
import math
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

def entropy(data):
    if not data:
        return 0
    c = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

def u16_values(data, limit=200000):
    size = min(len(data), limit)
    vals = []
    for off in range(0, size - 1, 2):
        vals.append(struct.unpack_from("<H", data, off)[0])
    return vals

def main():
    print("=" * 120)
    print("ITHMB FILE CLASSIFIER")
    print("=" * 120)

    rows = []

    for p in sorted(ROOT.rglob("*.ithmb")):
        data = p.read_bytes()
        vals = u16_values(data)
        c = Counter(vals)

        zero_pct = (data.count(0) / len(data)) * 100 if data else 0
        ent = entropy(data[:min(len(data), 200000)])

        top = c.most_common(8)

        # Score table-like if many repeated u16s and many low/structured values
        repeat_score = sum(count for _, count in top) / len(vals) * 100 if vals else 0
        sequential_hits = 0

        s = set(vals)
        for v in range(0, 65535):
            if v in s and (v + 1) in s and (v + 2) in s:
                sequential_hits += 1
                if sequential_hits > 200:
                    break

        if ent > 7.7:
            kind = "random/compressed/encrypted-like"
        elif repeat_score > 10 or sequential_hits > 100:
            kind = "index/table-like"
        elif ent < 4.5:
            kind = "pixel-like low entropy"
        else:
            kind = "mixed/unknown"

        rows.append((kind, ent, zero_pct, repeat_score, sequential_hits, p, len(data), top))

    for kind, ent, zero_pct, repeat_score, seq, p, size, top in rows:
        print("-" * 120)
        print(f"file: {p.relative_to(ROOT)}")
        print(f"size: {size}")
        print(f"class: {kind}")
        print(f"entropy(first200k): {ent:.4f}")
        print(f"zero_pct: {zero_pct:.2f}%")
        print(f"repeat_score_top8: {repeat_score:.2f}%")
        print(f"sequential_u16_runs_score: {seq}")
        print("top u16 values:", [(hex(v), c) for v, c in top])

if __name__ == "__main__":
    main()
