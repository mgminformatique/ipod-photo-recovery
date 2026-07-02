from pathlib import Path
from collections import Counter
import math

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")

BLOCK_SIZE = 256

def entropy(data):
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum((n / total) * math.log2(n / total) for n in counts.values())

def classify(ent, zeros):
    if ent > 7.8:
        return "HIGH_ENTROPY"
    if ent < 3.0:
        return "LOW_ENTROPY"
    if zeros > 180:
        return "ZERO_HEAVY"
    return "MIXED"

data = DB.read_bytes()

print("Photo Database Map")
print("=" * 80)
print("Size:", len(data))
print("Block size:", BLOCK_SIZE)
print()

for offset in range(0, len(data), BLOCK_SIZE):
    chunk = data[offset:offset + BLOCK_SIZE]
    ent = entropy(chunk)
    zeros = chunk.count(0)
    ff = chunk.count(255)
    kind = classify(ent, zeros)

    first16 = chunk[:16].hex(" ")

    print(
        f"0x{offset:08x} "
        f"entropy={ent:.3f} "
        f"zeros={zeros:<3} "
        f"ff={ff:<3} "
        f"{kind:<12} "
        f"{first16}"
    )
