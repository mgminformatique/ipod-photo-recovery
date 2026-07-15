from pathlib import Path
import struct
import math
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4

# T157 et T168 exclus : aucune progression +4.
EXCLUDED = {157, 168}

T_NUMBERS = set(range(154, 175)) | {130}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


files = []

for path in CACHE.rglob("T*.ithmb"):
    number = get_t_number(path)

    if number in T_NUMBERS and number not in EXCLUDED:
        files.append(path)

files.sort(key=lambda p: get_t_number(p) or -1)

print("=" * 110)
print("PAYLOAD OBJECT BOUNDARIES")
print("=" * 110)
print()

family_lengths = Counter()

for path in files:
    data = path.read_bytes()

    blocks = []

    for index, offset in enumerate(range(0, len(data), BLOCK_SIZE)):
        block = data[offset:offset + BLOCK_SIZE]

        if len(block) != BLOCK_SIZE:
            continue

        header = struct.unpack(">I", block[:4])[0]
        payload = block[4:]

        blocks.append({
            "index": index,
            "header": header,
            "payload": payload,
            "entropy": entropy(payload),
        })

    zero_indexes = [
        block["index"]
        for block in blocks
        if block["header"] == 0
    ]

    boundaries = [-1] + zero_indexes + [len(blocks)]

    objects = []

    for boundary_index in range(len(boundaries) - 1):
        left = boundaries[boundary_index]
        right = boundaries[boundary_index + 1]

        first = left + 1
        last = right - 1
        count = max(0, right - left - 1)

        if count == 0:
            continue

        object_blocks = blocks[first:right]

        plus4_good = 0
        plus4_total = max(0, len(object_blocks) - 1)

        for i in range(1, len(object_blocks)):
            previous = object_blocks[i - 1]["header"]
            current = object_blocks[i]["header"]

            if previous != 0 and current == previous + 4:
                plus4_good += 1

        average_entropy = (
            sum(block["entropy"] for block in object_blocks)
            / len(object_blocks)
        )

        low_positions = [
            local_index
            for local_index, block in enumerate(object_blocks)
            if block["entropy"] < 1.0
        ]

        objects.append({
            "first": first,
            "last": last,
            "count": count,
            "plus4_good": plus4_good,
            "plus4_total": plus4_total,
            "average_entropy": average_entropy,
            "low_positions": low_positions,
        })

        family_lengths[count] += 1

    print("-" * 110)
    print(path.relative_to(CACHE))
    print(
        f"full_blocks={len(blocks)} "
        f"zero_headers={zero_indexes} "
        f"objects={len(objects)}"
    )

    for object_index, obj in enumerate(objects):
        object_type = (
            "TYPE_A_52"
            if obj["count"] == 52
            else "TYPE_B_39"
            if obj["count"] == 39
            else "PARTIAL/OTHER"
        )

        ratio = (
            obj["plus4_good"] / obj["plus4_total"] * 100
            if obj["plus4_total"]
            else 0.0
        )

        print(
            f"  object={object_index:02d} "
            f"blocks={obj['first']:03d}-{obj['last']:03d} "
            f"count={obj['count']:3d} "
            f"type={object_type:13s} "
            f"+4={obj['plus4_good']:2d}/{obj['plus4_total']:2d} "
            f"{ratio:6.2f}% "
            f"entropy={obj['average_entropy']:.4f}"
        )

        print(
            "    low positions: "
            + (
                ",".join(str(x) for x in obj["low_positions"])
                if obj["low_positions"]
                else "none"
            )
        )

    if zero_indexes:
        deltas = [
            zero_indexes[i] - zero_indexes[i - 1]
            for i in range(1, len(zero_indexes))
        ]

        print(f"  separator deltas: {deltas}")

    print()

print("=" * 110)
print("OBJECT LENGTH DISTRIBUTION")
print("=" * 110)

for length, count in sorted(family_lengths.items()):
    label = (
        "TYPE_A"
        if length == 52
        else "TYPE_B"
        if length == 39
        else "PARTIAL/OTHER"
    )

    print(
        f"length={length:3d} "
        f"objects={count:3d} "
        f"{label}"
    )
