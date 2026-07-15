from pathlib import Path
from collections import Counter
import math

OBJECT = Path("output/t156_1k_objects/object_01_pages_0040-0091_count_52.bin")

PAGE_SIZE = 1020


def entropy(data):
    total = len(data)
    c = Counter(data)
    return -sum((n/total) * math.log2(n/total) for n in c.values())


raw = OBJECT.read_bytes()

pages = [
    raw[i:i+PAGE_SIZE]
    for i in range(0, len(raw), PAGE_SIZE)
]

print("=" * 100)
print("T156 PAGE-TO-PAGE SIMILARITY")
print("=" * 100)
print()

print(f"pages : {len(pages)}")
print()

for i in range(len(pages)-1):

    a = pages[i]
    b = pages[i+1]

    same = sum(x == y for x, y in zip(a, b))

    print(
        f"{i:02d}->{i+1:02d}  "
        f"same={same:4d}/{PAGE_SIZE} "
        f"{same/PAGE_SIZE*100:6.2f}%   "
        f"entropy={entropy(a):5.2f}/{entropy(b):5.2f}"
    )

print()
print("=" * 100)
print("LONG-RANGE COMPARISON")
print("=" * 100)

pairs = [
    (0,26),
    (0,51),
    (10,11),
    (20,21),
    (25,26),
    (30,31),
    (40,41),
]

print()

for a,b in pairs:

    same = sum(
        x==y
        for x,y in zip(pages[a], pages[b])
    )

    print(
        f"{a:02d}<->{b:02d} "
        f"{same/PAGE_SIZE*100:6.2f}%"
    )
