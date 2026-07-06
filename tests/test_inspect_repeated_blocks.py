from pathlib import Path
from collections import Counter
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
TARGET = CACHE / "F08" / "T157.ithmb"

OFFSETS = [
    0x0e8000,
    0x0ef000,
    0x013c00,
    0x01e800,
]

def entropy(buf):
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values()) if total else 0

data = TARGET.read_bytes()

for off in OFFSETS:
    chunk = data[off:off+4096]
    if not chunk:
        continue

    print("=" * 80)
    print(f"offset=0x{off:06x} len={len(chunk)} entropy={entropy(chunk):.3f}")
    print("first64:", chunk[:64].hex(" "))

    top = Counter(chunk).most_common(10)
    print("top bytes:", top)
