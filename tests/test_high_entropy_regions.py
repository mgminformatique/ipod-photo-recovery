from pathlib import Path
from collections import Counter
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGETS = [
    CACHE / "F08" / "T157.ithmb",
    CACHE / "F46" / "T144.ithmb",
    CACHE / "F47" / "T145.ithmb",
    CACHE / "F48" / "T146.ithmb",
    CACHE / "F49" / "T147.ithmb",
    CACHE / "F50" / "T148.ithmb",
]

def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

for path in TARGETS:
    data = path.read_bytes()
    print("=" * 100)
    print(path.relative_to(CACHE), "size", len(data))

    in_region = False
    start = None

    for off in range(0, len(data), 4096):
        chunk = data[off:off+4096]
        e = entropy(chunk)
        is_data = e > 7.5 and chunk.count(0) < 200

        if is_data and not in_region:
            start = off
            in_region = True

        if not is_data and in_region:
            print(f"data region 0x{start:06x}-0x{off-1:06x} size={off-start}")
            in_region = False

    if in_region:
        print(f"data region 0x{start:06x}-0x{len(data)-1:06x} size={len(data)-start}")
