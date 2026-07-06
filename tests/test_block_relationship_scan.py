from pathlib import Path
from collections import defaultdict, Counter
import hashlib
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/block_relationship_scan")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = sorted(CACHE.glob("F*/T*.ithmb"))

# On garde surtout les gros fichiers utiles
TARGETS = [
    p for p in TARGETS
    if int(p.stem[1:]) >= 154 or int(p.stem[1:]) in [144,145,146,147,148,157]
]

BLOCK_SIZES = [512, 1024, 2048, 4096]
MAX_SIMILAR_COMPARE = 300


def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())


def hamming_bytes(a, b):
    return sum(x != y for x, y in zip(a, b))


def xor_score(a, b):
    x = bytes(i ^ j for i, j in zip(a, b))
    c = Counter(x)
    common, count = c.most_common(1)[0]
    return common, count, count / len(x)


def not_equal_score(a, b):
    return sum(((x ^ 0xFF) == y) for x, y in zip(a, b)) / len(a)


print("=" * 100)
print("BLOCK RELATIONSHIP SCAN")
print("=" * 100)
print("files:", len(TARGETS))
for p in TARGETS:
    print(" ", p.relative_to(CACHE), p.stat().st_size)
print()

for block_size in BLOCK_SIZES:
    print("=" * 100)
    print("BLOCK SIZE:", block_size)

    blocks = []
    by_hash = defaultdict(list)

    for path in TARGETS:
        data = path.read_bytes()
        rel = str(path.relative_to(CACHE))

        for off in range(0, len(data), block_size):
            chunk = data[off:off + block_size]
            if len(chunk) != block_size:
                continue

            if chunk.count(0) == block_size:
                continue

            e = entropy(chunk)
            h = hashlib.sha1(chunk).hexdigest()

            item = {
                "file": rel,
                "off": off,
                "hash": h,
                "entropy": e,
                "data": chunk,
            }

            blocks.append(item)
            by_hash[h].append(item)

    print("usable blocks:", len(blocks))

    repeated = {h: v for h, v in by_hash.items() if len(v) > 1}
    print("exact repeated hashes:", len(repeated))

    for h, items in list(repeated.items())[:30]:
        print(" repeated", h)
        for it in items[:10]:
            print(f"   {it['file']} off=0x{it['off']:06x} entropy={it['entropy']:.3f}")

    print()
    print("low entropy blocks:")
    low = sorted(blocks, key=lambda x: x["entropy"])[:20]
    for it in low:
        print(f"  {it['file']} off=0x{it['off']:06x} entropy={it['entropy']:.3f} first={it['data'][:16].hex(' ')}")

    print()
    print("high entropy blocks:")
    high = sorted(blocks, key=lambda x: x["entropy"], reverse=True)[:20]
    for it in high:
        print(f"  {it['file']} off=0x{it['off']:06x} entropy={it['entropy']:.3f} first={it['data'][:16].hex(' ')}")

    print()
    print("similar block sample:")

    sample = blocks[:MAX_SIMILAR_COMPARE]
    best = []

    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            a = sample[i]
            b = sample[j]

            if a["file"] == b["file"] and abs(a["off"] - b["off"]) <= block_size:
                continue

            ham = hamming_bytes(a["data"], b["data"])
            same_ratio = 1 - (ham / block_size)

            if same_ratio > 0.85:
                best.append((same_ratio, a, b))

            xor_val, xor_count, xor_ratio = xor_score(a["data"], b["data"])
            if xor_ratio > 0.85:
                best.append((xor_ratio, a, b, xor_val))

            not_ratio = not_equal_score(a["data"], b["data"])
            if not_ratio > 0.85:
                best.append((not_ratio, a, b, "NOT"))

    best.sort(reverse=True, key=lambda x: x[0])

    for item in best[:40]:
        ratio = item[0]
        a = item[1]
        b = item[2]

        extra = ""
        if len(item) == 4:
            extra = f" transform={item[3]}"

        print(
            f"  ratio={ratio:.3f}{extra} "
            f"{a['file']}@0x{a['off']:06x} <-> "
            f"{b['file']}@0x{b['off']:06x}"
        )

    print()

print("done")
