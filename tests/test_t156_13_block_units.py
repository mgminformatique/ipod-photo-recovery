from pathlib import Path
import math
import re

ROOT = Path("output/t156_segments")
OUT = Path("output/t156_units_13")
OUT.mkdir(parents=True, exist_ok=True)

BLOCK_SIZE = 4092
UNIT_BLOCKS = 13
UNIT_SIZE = BLOCK_SIZE * UNIT_BLOCKS

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

files = sorted(ROOT.glob("segment_*.bin"))

all_units = []

print("=" * 100)
print("T156 13-BLOCK UNIT ANALYSIS")
print("=" * 100)
print(f"block payload size: {BLOCK_SIZE}")
print(f"unit blocks: {UNIT_BLOCKS}")
print(f"unit bytes: {UNIT_SIZE}")
print()

for segment_index, path in enumerate(files):
    data = path.read_bytes()

    blocks = [
        data[offset:offset + BLOCK_SIZE]
        for offset in range(0, len(data), BLOCK_SIZE)
        if len(data[offset:offset + BLOCK_SIZE]) == BLOCK_SIZE
    ]

    full_units = len(blocks) // UNIT_BLOCKS
    remainder = len(blocks) % UNIT_BLOCKS

    print("-" * 100)
    print(
        f"segment={segment_index:02d} "
        f"blocks={len(blocks):3d} "
        f"full_units={full_units} "
        f"remainder={remainder}"
    )

    for unit_index in range(full_units):
        first = unit_index * UNIT_BLOCKS
        unit_blocks = blocks[first:first + UNIT_BLOCKS]
        unit = b"".join(unit_blocks)

        output_path = OUT / (
            f"segment_{segment_index:02d}"
            f"_unit_{unit_index:02d}"
            f"_blocks_{first:03d}-{first + 12:03d}.bin"
        )
        output_path.write_bytes(unit)

        block_entropies = [entropy(block) for block in unit_blocks]

        print(
            f"  unit={unit_index:02d} "
            f"entropy={entropy(unit):.4f} "
            f"low_positions="
            + ",".join(
                str(index)
                for index, value in enumerate(block_entropies)
                if value < 1.0
            )
        )

        print(
            "    "
            + " ".join(
                f"{index:02d}:{value:4.2f}"
                for index, value in enumerate(block_entropies)
            )
        )

        all_units.append({
            "segment": segment_index,
            "unit": unit_index,
            "blocks": unit_blocks,
            "data": unit,
        })

print()
print("=" * 100)
print("AVERAGE ENTROPY BY POSITION INSIDE 13-BLOCK UNIT")
print("=" * 100)

for position in range(UNIT_BLOCKS):
    values = []

    for unit in all_units:
        values.append(entropy(unit["blocks"][position]))

    average = sum(values) / len(values)

    print(
        f"position={position:02d} "
        f"average_entropy={average:.4f} "
        f"min={min(values):.4f} "
        f"max={max(values):.4f}"
    )

print()
print("=" * 100)
print("SIMILARITY OF SAME POSITIONS ACROSS ADJACENT UNITS")
print("=" * 100)

for left_index in range(len(all_units) - 1):
    left = all_units[left_index]
    right = all_units[left_index + 1]

    print(
        f"unit "
        f"S{left['segment']:02d}U{left['unit']:02d} "
        f"vs "
        f"S{right['segment']:02d}U{right['unit']:02d}"
    )

    for position in range(UNIT_BLOCKS):
        a = left["blocks"][position]
        b = right["blocks"][position]

        matches = sum(x == y for x, y in zip(a, b))
        percent = matches / BLOCK_SIZE * 100

        if percent >= 50 or position >= 10:
            print(
                f"  position={position:02d} "
                f"same={matches:4d}/{BLOCK_SIZE} "
                f"{percent:6.2f}%"
            )
