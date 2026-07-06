from pathlib import Path
from collections import Counter
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGETS = [
    CACHE / "F23" / "T172.ithmb",
    CACHE / "F12" / "T161.ithmb",
    CACHE / "F08" / "T157.ithmb",
    CACHE / "F46" / "T144.ithmb",
]

def entropy(data):
    if not data:
        return 0
    c = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

for path in TARGETS:
    if not path.exists():
        continue

    data = path.read_bytes()

    print("=" * 100)
    print(path.relative_to(CACHE))
    print("size:", len(data))
    print()

    for off in range(0, len(data), 4096):
        chunk = data[off:off+4096]
        e = entropy(chunk)
        zeros = chunk.count(0)
        ff = chunk.count(255)

        print(
            f"0x{off:08x} "
            f"entropy={e:.3f} "
            f"zeros={zeros:4d} "
            f"ff={ff:4d} "
            f"first16={chunk[:16].hex(' ')}"
        )
