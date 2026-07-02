from pathlib import Path
from collections import Counter
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

GUID = "00262001-0002-0010-FBB3-AB02A8125552".encode("utf-16le")


def entropy(data):
    if not data:
        return 0.0

    c = Counter(data)
    total = len(data)

    return -sum((n / total) * math.log2(n / total) for n in c.values())


print("=" * 120)
print("GLOBAL IPOD PHOTO CACHE INVENTORY")
print("=" * 120)
print()

for f in sorted(CACHE.rglob("*")):

    if not f.is_file():
        continue

    data = f.read_bytes()

    ent = entropy(data)

    guid_hits = data.count(GUID)

    bmp = data.find(b"BM")
    jfif = data.find(b"JFIF")
    exif = data.find(b"Exif")

    print(
        f"{f.relative_to(CACHE)!s:<25}"
        f" size={len(data):<9}"
        f" entropy={ent:5.3f}"
        f" guid={guid_hits:<2}"
        f" bmp={bmp:<8}"
        f" jfif={jfif:<8}"
        f" exif={exif:<8}"
    )
