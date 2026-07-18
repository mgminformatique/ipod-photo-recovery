from pathlib import Path
from collections import Counter
import math

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

data = DB.read_bytes()

BLOCK = 256

print("="*80)
print("BLOCK ANALYSIS")
print("="*80)

for i in range(0, len(data), BLOCK):

    block = data[i:i+BLOCK]

    counts = Counter(block)

    total = len(block)

    entropy = -sum(
        (c/total) * math.log2(c/total)
        for c in counts.values()
    )

    zeros = block.count(0)

    ff = block.count(255)

    print(
        f"{i:06d} "
        f"entropy={entropy:.4f} "
        f"zero={zeros:3d} "
        f"ff={ff:3d}"
    )

print()
print("Done.")
