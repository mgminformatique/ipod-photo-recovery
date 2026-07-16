from pathlib import Path
import math

ROOT = Path("output/t156_segments")
BLOCK_SIZE = 4092
CYCLE = 13

def entropy(data):
    if not data:
        return 0.0

    counts = [0] * 256
    for value in data:
        counts[value] += 1

    result = 0.0
    total = len(data)

    for count in counts:
        if count:
            p = count / total
            result -= p * math.log2(p)

    return result

print("=" * 100)
print("T156 FIND 13-BLOCK PHASE")
print("=" * 100)

for segment_index, path in enumerate(sorted(ROOT.glob("segment_*.bin"))):
    data = path.read_bytes()

    blocks = [
        data[offset:offset + BLOCK_SIZE]
        for offset in range(0, len(data), BLOCK_SIZE)
        if len(data[offset:offset + BLOCK_SIZE]) == BLOCK_SIZE
    ]

    entropies = [entropy(block) for block in blocks]

    print()
    print("-" * 100)
    print(
        f"segment={segment_index:02d} "
        f"blocks={len(blocks)} "
        f"file={path.name}"
    )

    candidates = []

    for phase in range(CYCLE):
        footer_positions = list(range(phase, len(blocks), CYCLE))

        footer_entropy = (
            sum(entropies[index] for index in footer_positions)
            / len(footer_positions)
            if footer_positions
            else 999.0
        )

        low_count = sum(
            entropies[index] < 1.0
            for index in footer_positions
        )

        candidates.append(
            (
                footer_entropy,
                -low_count,
                phase,
                footer_positions,
            )
        )

        print(
            f"phase={phase:02d} "
            f"avg_entropy={footer_entropy:6.3f} "
            f"low_count={low_count:2d}/{len(footer_positions):2d} "
            f"positions={footer_positions}"
        )

    best_entropy, negative_low, best_phase, positions = min(candidates)

    print()
    print(
        f"BEST PHASE={best_phase:02d} "
        f"avg_entropy={best_entropy:.4f} "
        f"low_count={-negative_low}/{len(positions)}"
    )

    print("block entropy map:")
    print(
        "  "
        + " ".join(
            f"{index:02d}:{value:4.2f}"
            for index, value in enumerate(entropies)
        )
    )
