from pathlib import Path
from collections import Counter
import math

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F08/T157.ithmb",
]

BLOCK_SIZES = [
    16, 32, 64, 88, 120, 128, 176, 220, 240, 256,
    320, 376, 512, 608, 768, 928, 1024, 2048,
    4096, 8192, 14400, 21600, 28800, 43200,
]

def entropy(data):
    if not data:
        return 0
    c = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

def analyze_file(path):
    p = Path(path)
    data = p.read_bytes()

    print("=" * 80)
    print(p)
    print("Size:", len(data))
    print("Entropy:", round(entropy(data), 3))
    print()

    print("Block-size candidates:")
    for bs in BLOCK_SIZES:
        blocks = len(data) // bs
        rem = len(data) % bs

        if blocks == 0:
            continue

        sample = [data[i * bs:(i + 1) * bs][:16] for i in range(min(blocks, 200))]
        repeated = Counter(sample).most_common(3)

        repeat_score = sum(count for _, count in repeated if count > 1)

        if rem < 2048 or repeat_score > 5:
            print(
                f"  block={bs:<6} blocks={blocks:<5} "
                f"remainder={rem:<6} repeat_score={repeat_score}"
            )

    print()
    print("Top repeated 16-byte sequences:")
    chunks = [data[i:i+16] for i in range(0, len(data) - 16, 16)]
    for chunk, count in Counter(chunks).most_common(10):
        if count > 1:
            print(f"  count={count:<5} {chunk.hex(' ')}")

    print()

for f in FILES:
    analyze_file(f)
