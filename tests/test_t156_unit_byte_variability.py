from pathlib import Path
from collections import Counter

ROOT = Path("output/t156_units_13")
BLOCK_SIZE = 4092
UNIT_BLOCKS = 13

files = sorted(ROOT.glob("segment_*_unit_*.bin"))
units = [path.read_bytes() for path in files]

units = [
    unit for unit in units
    if len(unit) == BLOCK_SIZE * UNIT_BLOCKS
]

print("=" * 100)
print("T156 UNIT BYTE VARIABILITY")
print("=" * 100)
print(f"units: {len(units)}")
print()

for block_position in range(UNIT_BLOCKS):
    start = block_position * BLOCK_SIZE
    end = start + BLOCK_SIZE

    blocks = [unit[start:end] for unit in units]

    constant_positions = []
    near_constant_positions = []
    variable_positions = []

    for byte_index in range(BLOCK_SIZE):
        values = [block[byte_index] for block in blocks]
        counts = Counter(values)
        most_common_value, most_common_count = counts.most_common(1)[0]
        ratio = most_common_count / len(values)

        if ratio == 1.0:
            constant_positions.append((byte_index, most_common_value))
        elif ratio >= 0.80:
            near_constant_positions.append(
                (byte_index, most_common_value, ratio)
            )
        else:
            variable_positions.append(byte_index)

    print("-" * 100)
    print(f"BLOCK POSITION {block_position:02d}")
    print(
        f"constant={len(constant_positions):4d} "
        f"near_constant_80={len(near_constant_positions):4d} "
        f"variable={len(variable_positions):4d}"
    )

    if constant_positions:
        runs = []
        run_start = constant_positions[0][0]
        previous = run_start

        for byte_index, _ in constant_positions[1:]:
            if byte_index == previous + 1:
                previous = byte_index
            else:
                runs.append((run_start, previous))
                run_start = byte_index
                previous = byte_index

        runs.append((run_start, previous))

        print("constant runs:")
        for a, b in runs[:30]:
            if b - a + 1 >= 4:
                print(
                    f"  0x{a:03x}-0x{b:03x} "
                    f"len={b-a+1}"
                )

    print("first 64-byte majority template:")

    template = []
    confidence = []

    for byte_index in range(64):
        values = [block[byte_index] for block in blocks]
        value, count = Counter(values).most_common(1)[0]

        template.append(value)
        confidence.append(count / len(values))

    print("  " + " ".join(f"{value:02x}" for value in template))
    print("  " + " ".join(f"{ratio:4.2f}" for ratio in confidence))

print()
print("=" * 100)
print("PAIRWISE VARIABLE DATA SIZES")
print("=" * 100)

for unit_index, unit in enumerate(units):
    variable = bytearray()

    for block_position in range(1, 11):
        start = block_position * BLOCK_SIZE
        variable += unit[start:start + BLOCK_SIZE]

    print(
        f"unit={unit_index:02d} "
        f"variable_bytes={len(variable)} "
        f"first32={variable[:32].hex(' ')}"
    )
