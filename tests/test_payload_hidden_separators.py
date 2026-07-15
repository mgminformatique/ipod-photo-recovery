from pathlib import Path
import math
import struct
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

EXPECTED_OBJECT_LENGTHS = {39, 52}


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


def similarity_to_constant(payload: bytes, value: int) -> float:
    if not payload:
        return 0.0

    return payload.count(value) / len(payload)


def separator_score(block):
    payload = block["payload"]

    e = block["entropy"]
    zero_ratio = similarity_to_constant(payload, 0)
    one_ratio = similarity_to_constant(payload, 1)

    dominant_count = Counter(payload).most_common(1)[0][1]
    dominant_ratio = dominant_count / len(payload)

    score = 0

    if block["header"] == 0:
        score += 100

    if e < 0.25:
        score += 50
    elif e < 0.75:
        score += 30
    elif e < 1.25:
        score += 15

    if dominant_ratio >= 0.98:
        score += 40
    elif dominant_ratio >= 0.90:
        score += 25
    elif dominant_ratio >= 0.75:
        score += 10

    if zero_ratio >= 0.90 or one_ratio >= 0.90:
        score += 20

    return score


def object_split_candidates(length):
    candidates = []

    # Deux objets avec un bloc séparateur entre les deux.
    for left in EXPECTED_OBJECT_LENGTHS:
        for right in EXPECTED_OBJECT_LENGTHS:
            expected = left + 1 + right

            if length == expected:
                candidates.append((left, left, right))

    return candidates


files = []

for path in CACHE.rglob("T*.ithmb"):
    number = get_t_number(path)

    if number in T_NUMBERS and number not in EXCLUDED:
        files.append(path)

files.sort(key=lambda path: get_t_number(path) or -1)

print("=" * 110)
print("PAYLOAD HIDDEN SEPARATOR ANALYSIS")
print("=" * 110)

for path in files:
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
            "offset": offset,
            "header": header,
            "payload": payload,
            "entropy": entropy(payload),
        })

    known_separators = [
        index
        for index, block in enumerate(blocks)
        if block["header"] == 0
    ]

    boundaries = [-1] + known_separators + [len(blocks)]

    suspicious_objects = []

    for object_index in range(len(boundaries) - 1):
        left_boundary = boundaries[object_index]
        right_boundary = boundaries[object_index + 1]

        first = left_boundary + 1
        last = right_boundary - 1
        length = right_boundary - left_boundary - 1

        if length in EXPECTED_OBJECT_LENGTHS:
            continue

        candidates = object_split_candidates(length)

        if not candidates and length < 53:
            continue

        suspicious_objects.append({
            "object_index": object_index,
            "first": first,
            "last": last,
            "length": length,
            "split_patterns": candidates,
        })

    if not suspicious_objects:
        continue

    print()
    print("-" * 110)
    print(path.relative_to(CACHE))
    print(f"full_blocks={len(blocks)} known_zero_headers={known_separators}")

    for obj in suspicious_objects:
        first = obj["first"]
        length = obj["length"]

        print()
        print(
            f"object={obj['object_index']:02d} "
            f"global_blocks={obj['first']:03d}-{obj['last']:03d} "
            f"length={length}"
        )

        if obj["split_patterns"]:
            print(f"exact split patterns: {obj['split_patterns']}")
        else:
            print("exact split patterns: none")

        local_blocks = blocks[first:first + length]

        ranked = []

        for local_index, block in enumerate(local_blocks):
            score = separator_score(block)

            previous_header = (
                local_blocks[local_index - 1]["header"]
                if local_index > 0
                else None
            )

            next_header = (
                local_blocks[local_index + 1]["header"]
                if local_index + 1 < len(local_blocks)
                else None
            )

            plus4_before = (
                previous_header is not None
                and block["header"] == previous_header + 4
            )

            plus4_after = (
                next_header is not None
                and next_header == block["header"] + 4
            )

            bridge_plus4 = (
                previous_header is not None
                and next_header is not None
                and next_header == previous_header + 8
            )

            if not plus4_before:
                score += 15

            if not plus4_after:
                score += 15

            if bridge_plus4:
                score += 10

            ranked.append({
                "local_index": local_index,
                "global_index": block["index"],
                "header": block["header"],
                "entropy": block["entropy"],
                "score": score,
                "dominant": Counter(block["payload"]).most_common(1)[0],
                "plus4_before": plus4_before,
                "plus4_after": plus4_after,
                "bridge_plus4": bridge_plus4,
            })

        ranked.sort(
            key=lambda item: (
                -item["score"],
                item["entropy"],
                item["local_index"],
            )
        )

        print("top hidden-separator candidates:")

        for item in ranked[:12]:
            dominant_value, dominant_count = item["dominant"]
            dominant_ratio = dominant_count / (BLOCK_SIZE - HEADER_SIZE)

            expected_boundary = (
                item["local_index"] in {39, 52}
            )

            print(
                f"  local={item['local_index']:03d} "
                f"global={item['global_index']:03d} "
                f"header=0x{item['header']:08x} "
                f"entropy={item['entropy']:.4f} "
                f"dominant=0x{dominant_value:02x} "
                f"{dominant_ratio * 100:6.2f}% "
                f"score={item['score']:3d} "
                f"before+4={item['plus4_before']} "
                f"after+4={item['plus4_after']} "
                f"bridge={item['bridge_plus4']} "
                f"{'EXPECTED_SPLIT' if expected_boundary else ''}"
            )

        print("specific expected split positions:")

        for split_local in sorted({39, 52}):
            if split_local >= len(local_blocks):
                continue

            block = local_blocks[split_local]
            dominant_value, dominant_count = Counter(
                block["payload"]
            ).most_common(1)[0]

            print(
                f"  local={split_local:03d} "
                f"global={block['index']:03d} "
                f"header=0x{block['header']:08x} "
                f"entropy={block['entropy']:.4f} "
                f"dominant=0x{dominant_value:02x} "
                f"{dominant_count / len(block['payload']) * 100:.2f}%"
            )
