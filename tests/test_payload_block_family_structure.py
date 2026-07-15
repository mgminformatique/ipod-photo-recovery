from pathlib import Path
import math
import struct
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4
PAYLOAD_SIZE = BLOCK_SIZE - HEADER_SIZE

# Famille précédemment classée comme POSSIBLE PAYLOAD.
T_NUMBERS = set(range(154, 175)) | {130}


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def find_file_t_number(path: Path):
    name = path.stem

    if not name.startswith("T"):
        return None

    try:
        return int(name[1:])
    except ValueError:
        return None


def longest_plus4_run(headers):
    best_start = 0
    best_length = 0

    current_start = 0
    current_length = 1

    for index in range(1, len(headers)):
        previous = headers[index - 1]
        current = headers[index]

        if previous != 0 and current == previous + 4:
            current_length += 1
        else:
            if current_length > best_length:
                best_start = current_start
                best_length = current_length

            current_start = index
            current_length = 1

    if current_length > best_length:
        best_start = current_start
        best_length = current_length

    return best_start, best_length


def phase_score(entropies, cycle, phase):
    positions = list(range(phase, len(entropies), cycle))

    if not positions:
        return None

    values = [entropies[index] for index in positions]
    average = sum(values) / len(values)
    low_count = sum(value < 1.0 for value in values)

    return average, low_count, positions


files = []

for path in CACHE.rglob("T*.ithmb"):
    t_number = find_file_t_number(path)

    if t_number in T_NUMBERS:
        files.append(path)

files.sort(key=lambda path: find_file_t_number(path) or -1)

print("=" * 110)
print("PAYLOAD BLOCK FAMILY STRUCTURE")
print("=" * 110)
print(f"files: {len(files)}")
print(f"block size: {BLOCK_SIZE}")
print(f"payload bytes per full block: {PAYLOAD_SIZE}")
print()

summary = []

for path in files:
    data = path.read_bytes()

    full_blocks = []

    for offset in range(0, len(data), BLOCK_SIZE):
        block = data[offset:offset + BLOCK_SIZE]

        if len(block) != BLOCK_SIZE:
            continue

        header = struct.unpack(">I", block[:HEADER_SIZE])[0]
        payload = block[HEADER_SIZE:]

        full_blocks.append({
            "offset": offset,
            "header": header,
            "payload": payload,
            "entropy": entropy(payload),
        })

    headers = [block["header"] for block in full_blocks]
    entropies = [block["entropy"] for block in full_blocks]

    zero_headers = [
        index
        for index, header in enumerate(headers)
        if header == 0
    ]

    start, length = longest_plus4_run(headers)

    plus4_pairs = sum(
        1
        for index in range(1, len(headers))
        if headers[index - 1] != 0
        and headers[index] == headers[index - 1] + 4
    )

    pair_total = max(0, len(headers) - 1)
    plus4_ratio = plus4_pairs / pair_total if pair_total else 0.0

    low_positions = [
        index
        for index, value in enumerate(entropies)
        if value < 1.0
    ]

    cycle_results = []

    for cycle in range(2, 33):
        best_for_cycle = None

        for phase in range(cycle):
            result = phase_score(entropies, cycle, phase)

            if result is None:
                continue

            average, low_count, positions = result

            # Favorise :
            # 1. un grand pourcentage de positions à faible entropie;
            # 2. une faible entropie moyenne;
            # 3. plusieurs répétitions.
            low_ratio = low_count / len(positions)

            candidate = (
                -low_ratio,
                average,
                -len(positions),
                phase,
                low_count,
                positions,
            )

            if best_for_cycle is None or candidate < best_for_cycle:
                best_for_cycle = candidate

        if best_for_cycle is not None:
            cycle_results.append((cycle, best_for_cycle))

    cycle_results.sort(
        key=lambda item: (
            item[1][0],
            item[1][1],
            item[1][2],
            item[0],
        )
    )

    best_cycles = cycle_results[:5]

    print("-" * 110)
    print(f"{path.relative_to(CACHE)}")
    print(
        f"size={len(data)} "
        f"full_blocks={len(full_blocks)} "
        f"remainder={len(data) % BLOCK_SIZE}"
    )

    if headers:
        print(
            f"first_header=0x{headers[0]:08x} "
            f"last_header=0x{headers[-1]:08x}"
        )

    print(
        f"+4 pairs={plus4_pairs}/{pair_total} "
        f"ratio={plus4_ratio * 100:.2f}%"
    )

    print(
        f"longest +4 run: "
        f"start_block={start} "
        f"length={length}"
    )

    print(
        f"zero-header blocks ({len(zero_headers)}): "
        f"{zero_headers[:80]}"
        + (" ..." if len(zero_headers) > 80 else "")
    )

    print(
        f"low-entropy blocks <1.0 ({len(low_positions)}): "
        f"{low_positions[:100]}"
        + (" ..." if len(low_positions) > 100 else "")
    )

    print("best periodic low-entropy candidates:")

    for cycle, candidate in best_cycles:
        (
            negative_low_ratio,
            average,
            negative_count,
            phase,
            low_count,
            positions,
        ) = candidate

        low_ratio = -negative_low_ratio

        print(
            f"  cycle={cycle:02d} "
            f"phase={phase:02d} "
            f"low={low_count}/{len(positions)} "
            f"ratio={low_ratio * 100:6.2f}% "
            f"avg_entropy={average:.4f} "
            f"positions={positions[:20]}"
            + (" ..." if len(positions) > 20 else "")
        )

    cycle13 = next(
        (
            candidate
            for cycle, candidate in cycle_results
            if cycle == 13
        ),
        None,
    )

    if cycle13 is not None:
        (
            negative_low_ratio,
            average,
            negative_count,
            phase,
            low_count,
            positions,
        ) = cycle13

        print(
            f"cycle 13 specifically: "
            f"phase={phase} "
            f"low={low_count}/{len(positions)} "
            f"ratio={-negative_low_ratio * 100:.2f}% "
            f"avg_entropy={average:.4f}"
        )

    summary.append({
        "file": str(path.relative_to(CACHE)),
        "blocks": len(full_blocks),
        "plus4_ratio": plus4_ratio,
        "longest_run": length,
        "zero_headers": len(zero_headers),
        "low_blocks": len(low_positions),
        "best_cycle": best_cycles[0][0] if best_cycles else None,
        "best_phase": best_cycles[0][1][3] if best_cycles else None,
        "cycle13_phase": cycle13[3] if cycle13 else None,
        "cycle13_ratio": -cycle13[0] if cycle13 else 0.0,
    })

print()
print("=" * 110)
print("FAMILY SUMMARY")
print("=" * 110)
print(
    "file".ljust(20),
    "blocks".rjust(7),
    "+4%".rjust(8),
    "run".rjust(6),
    "zero".rjust(6),
    "low".rjust(6),
    "best".rjust(8),
    "13phase".rjust(9),
    "13low%".rjust(9),
)

for item in summary:
    best = (
        f"{item['best_cycle']}:{item['best_phase']}"
        if item["best_cycle"] is not None
        else "-"
    )

    phase13 = (
        str(item["cycle13_phase"])
        if item["cycle13_phase"] is not None
        else "-"
    )

    print(
        item["file"].ljust(20),
        str(item["blocks"]).rjust(7),
        f"{item['plus4_ratio'] * 100:7.2f}",
        str(item["longest_run"]).rjust(6),
        str(item["zero_headers"]).rjust(6),
        str(item["low_blocks"]).rjust(6),
        best.rjust(8),
        phase13.rjust(9),
        f"{item['cycle13_ratio'] * 100:8.2f}",
    )
