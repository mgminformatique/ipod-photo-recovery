from pathlib import Path
import math

ROOT = Path("output/t156_segments")
BLOCK_PAYLOAD = 4092

FILES = sorted(ROOT.glob("segment_*.bin"))

def entropy(buf):
    if not buf:
        return 0.0

    counts = [0] * 256
    for value in buf:
        counts[value] += 1

    result = 0.0
    total = len(buf)

    for count in counts:
        if count:
            p = count / total
            result -= p * math.log2(p)

    return result

def load_blocks(path):
    data = path.read_bytes()

    return [
        data[off:off + BLOCK_PAYLOAD]
        for off in range(0, len(data), BLOCK_PAYLOAD)
        if len(data[off:off + BLOCK_PAYLOAD]) == BLOCK_PAYLOAD
    ]

segments = [load_blocks(path) for path in FILES]

print("=" * 100)
print("T156 SEGMENT PAIR COMPARISON")
print("=" * 100)

for index, (path, blocks) in enumerate(zip(FILES, segments)):
    print(
        f"segment={index:02d} "
        f"blocks={len(blocks):3d} "
        f"file={path.name}"
    )

print()

pairs = [
    (1, 3),
    (2, 4),
]

for left_index, right_index in pairs:
    left = segments[left_index]
    right = segments[right_index]

    print("=" * 100)
    print(
        f"PAIR segment {left_index:02d} vs segment {right_index:02d} "
        f"({len(left)} blocks)"
    )
    print("=" * 100)

    total_matches = 0
    total_bytes = 0

    for block_index, (a, b) in enumerate(zip(left, right)):
        matches = sum(x == y for x, y in zip(a, b))
        percent = matches / len(a) * 100

        entropy_a = entropy(a)
        entropy_b = entropy(b)
        entropy_diff = abs(entropy_a - entropy_b)

        low_a = sum(value <= 15 for value in a) / len(a) * 100
        low_b = sum(value <= 15 for value in b) / len(b) * 100

        total_matches += matches
        total_bytes += len(a)

        print(
            f"block={block_index:03d} "
            f"same={matches:4d}/{len(a)} {percent:6.2f}% "
            f"entropy={entropy_a:5.2f}/{entropy_b:5.2f} "
            f"diff={entropy_diff:5.2f} "
            f"low15={low_a:6.2f}%/{low_b:6.2f}%"
        )

    print()
    print(
        f"overall exact similarity: "
        f"{total_matches}/{total_bytes} "
        f"{total_matches / total_bytes * 100:.3f}%"
    )
    print()

print("=" * 100)
print("LOW-ENTROPY BLOCK POSITIONS")
print("=" * 100)

for segment_index, blocks in enumerate(segments):
    positions = []

    for block_index, block in enumerate(blocks):
        value = entropy(block)

        if value < 1.0:
            positions.append((block_index, value))

    formatted = ", ".join(
        f"{index}:{value:.2f}"
        for index, value in positions
    )

    print(f"segment={segment_index:02d}: {formatted or 'none'}")
