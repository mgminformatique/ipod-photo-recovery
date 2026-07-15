from pathlib import Path
import struct
import math
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4
PAYLOAD_SIZE = BLOCK_SIZE - HEADER_SIZE

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

MARKER_HEADERS = {
    0x00000000,
    0x0D000000,
}

VALID_LENGTHS = {
    39: "TYPE_B_39",
    52: "TYPE_A_52",
}


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


def block_stats(payload: bytes):
    counts = Counter(payload)
    dominant_value, dominant_count = counts.most_common(1)[0]

    return {
        "entropy": entropy(payload),
        "zeros": payload.count(0),
        "ones": payload.count(1),
        "low15": sum(value <= 15 for value in payload),
        "low31": sum(value <= 31 for value in payload),
        "dominant_value": dominant_value,
        "dominant_ratio": dominant_count / len(payload),
        "unique": len(counts),
    }


objects_by_type = defaultdict(list)

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    data = path.read_bytes()
    blocks = []

    for index, offset in enumerate(range(0, len(data), BLOCK_SIZE)):
        raw = data[offset:offset + BLOCK_SIZE]

        if len(raw) != BLOCK_SIZE:
            continue

        header = struct.unpack(">I", raw[:4])[0]
        payload = raw[4:]

        blocks.append({
            "index": index,
            "header": header,
            "payload": payload,
        })

    markers = [
        index
        for index, block in enumerate(blocks)
        if block["header"] in MARKER_HEADERS
    ]

    boundaries = [-1] + markers + [len(blocks)]

    for object_index in range(len(boundaries) - 1):
        left = boundaries[object_index]
        right = boundaries[object_index + 1]

        first = left + 1
        count = right - left - 1

        if count not in VALID_LENGTHS:
            continue

        object_blocks = blocks[first:right]

        objects_by_type[count].append({
            "file": str(path.relative_to(CACHE)),
            "t_number": t_number,
            "object_index": object_index,
            "first_block": first,
            "blocks": object_blocks,
        })

print("=" * 110)
print("PAYLOAD OBJECT TYPE COMPARISON")
print("=" * 110)

for object_length in sorted(objects_by_type):
    object_type = VALID_LENGTHS[object_length]
    objects = objects_by_type[object_length]

    print()
    print("=" * 110)
    print(f"{object_type}")
    print("=" * 110)
    print(f"objects: {len(objects)}")
    print(f"blocks per object: {object_length}")
    print()

    for position in range(object_length):
        position_blocks = [
            obj["blocks"][position]["payload"]
            for obj in objects
        ]

        entropies = [entropy(block) for block in position_blocks]
        zero_ratios = [
            block.count(0) / PAYLOAD_SIZE
            for block in position_blocks
        ]
        one_ratios = [
            block.count(1) / PAYLOAD_SIZE
            for block in position_blocks
        ]
        low15_ratios = [
            sum(value <= 15 for value in block) / PAYLOAD_SIZE
            for block in position_blocks
        ]

        pair_similarities = []

        for index in range(len(position_blocks) - 1):
            left = position_blocks[index]
            right = position_blocks[index + 1]

            matches = sum(
                a == b
                for a, b in zip(left, right)
            )

            pair_similarities.append(matches / PAYLOAD_SIZE)

        average_similarity = (
            sum(pair_similarities) / len(pair_similarities)
            if pair_similarities
            else 0.0
        )

        majority_constant = 0
        majority_80 = 0

        for byte_index in range(PAYLOAD_SIZE):
            counts = Counter(
                block[byte_index]
                for block in position_blocks
            )

            _, count = counts.most_common(1)[0]
            ratio = count / len(position_blocks)

            if ratio == 1.0:
                majority_constant += 1

            if ratio >= 0.80:
                majority_80 += 1

        print(
            f"position={position:02d} "
            f"entropy_avg={sum(entropies)/len(entropies):5.2f} "
            f"entropy_min={min(entropies):5.2f} "
            f"entropy_max={max(entropies):5.2f} "
            f"zero_avg={sum(zero_ratios)/len(zero_ratios)*100:6.2f}% "
            f"one_avg={sum(one_ratios)/len(one_ratios)*100:6.2f}% "
            f"low15_avg={sum(low15_ratios)/len(low15_ratios)*100:6.2f}% "
            f"adjacent_similarity={average_similarity*100:6.2f}% "
            f"constant={majority_constant:4d} "
            f"majority80={majority_80:4d}"
        )

    print()
    print("OBJECT HEADERS")
    print("-" * 110)

    for obj in objects[:20]:
        headers = [
            block["header"]
            for block in obj["blocks"]
        ]

        print(
            f"{obj['file']} "
            f"object={obj['object_index']:02d} "
            f"blocks={obj['first_block']:03d}-"
            f"{obj['first_block'] + object_length - 1:03d} "
            f"first=0x{headers[0]:08x} "
            f"last=0x{headers[-1]:08x} "
            f"span={headers[-1] - headers[0]}"
        )

print()
print("=" * 110)
print("TYPE A / TYPE B SHAPE SUMMARY")
print("=" * 110)

for object_length in [39, 52]:
    objects = objects_by_type[object_length]

    average_entropies = []

    for position in range(object_length):
        values = [
            entropy(obj["blocks"][position]["payload"])
            for obj in objects
        ]

        average_entropies.append(
            sum(values) / len(values)
        )

    low_positions = [
        index
        for index, value in enumerate(average_entropies)
        if value < 1.0
    ]

    print(
        f"{VALID_LENGTHS[object_length]} "
        f"average low-entropy positions: "
        f"{low_positions}"
    )

    print(
        "  "
        + " ".join(
            f"{index:02d}:{value:4.2f}"
            for index, value in enumerate(average_entropies)
        )
    )
