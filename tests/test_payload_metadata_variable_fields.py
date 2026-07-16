from pathlib import Path
import struct
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4
PAYLOAD_SIZE = BLOCK_SIZE - HEADER_SIZE

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}
MARKERS = {0x00000000, 0x0D000000}
VALID_LENGTHS = {39, 52}

# Les positions les plus structurées.
TARGET_POSITIONS = {
    39: [11, 12, 13, 25, 26, 38],
    52: [11, 12, 13, 25, 26, 38, 39, 51],
}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


objects = defaultdict(list)

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

        blocks.append({
            "index": index,
            "header": struct.unpack(">I", raw[:4])[0],
            "payload": raw[4:],
        })

    marker_indexes = [
        index
        for index, block in enumerate(blocks)
        if block["header"] in MARKERS
    ]

    boundaries = [-1] + marker_indexes + [len(blocks)]

    for object_index in range(len(boundaries) - 1):
        left = boundaries[object_index]
        right = boundaries[object_index + 1]

        first = left + 1
        length = right - left - 1

        if length not in VALID_LENGTHS:
            continue

        object_blocks = blocks[first:right]

        objects[length].append({
            "file": str(path.relative_to(CACHE)),
            "t_number": t_number,
            "object_index": object_index,
            "first_block": first,
            "first_header": object_blocks[0]["header"],
            "last_header": object_blocks[-1]["header"],
            "blocks": object_blocks,
        })


def monotonic_score(values):
    if len(values) < 2:
        return 0, 0

    increasing = sum(
        values[index] >= values[index - 1]
        for index in range(1, len(values))
    )

    decreasing = sum(
        values[index] <= values[index - 1]
        for index in range(1, len(values))
    )

    return increasing, decreasing


def correlation_like(values, references):
    """
    Simple score sans numpy :
    compte combien de différences consécutives ont le même signe.
    """
    if len(values) < 2:
        return 0.0

    matches = 0
    usable = 0

    for index in range(1, len(values)):
        delta_value = values[index] - values[index - 1]
        delta_ref = references[index] - references[index - 1]

        if delta_value == 0 or delta_ref == 0:
            continue

        usable += 1

        if (delta_value > 0) == (delta_ref > 0):
            matches += 1

    return matches / usable if usable else 0.0


print("=" * 120)
print("PAYLOAD METADATA VARIABLE FIELD ANALYSIS")
print("=" * 120)

for object_length in [39, 52]:
    group = objects[object_length]

    print()
    print("=" * 120)
    print(f"OBJECT LENGTH {object_length}")
    print("=" * 120)
    print(f"objects={len(group)}")

    first_headers = [obj["first_header"] for obj in group]
    t_numbers = [obj["t_number"] for obj in group]
    first_blocks = [obj["first_block"] for obj in group]

    for position in TARGET_POSITIONS[object_length]:
        payloads = [
            obj["blocks"][position]["payload"]
            for obj in group
        ]

        print()
        print("-" * 120)
        print(f"POSITION {position:02d}")

        variable_offsets = []

        for offset in range(PAYLOAD_SIZE):
            values = [payload[offset] for payload in payloads]

            if len(set(values)) > 1:
                majority_count = Counter(values).most_common(1)[0][1]
                majority_ratio = majority_count / len(values)

                variable_offsets.append({
                    "offset": offset,
                    "unique": len(set(values)),
                    "majority_ratio": majority_ratio,
                    "values": values,
                })

        print(f"variable byte offsets: {len(variable_offsets)}")

        # Garde les offsets les plus structurés :
        # peu de valeurs uniques, ou majorité très forte.
        candidates = [
            item
            for item in variable_offsets
            if item["unique"] <= 16
            or item["majority_ratio"] >= 0.75
        ]

        candidates.sort(
            key=lambda item: (
                item["unique"],
                -item["majority_ratio"],
                item["offset"],
            )
        )

        print("TOP BYTE CANDIDATES")

        for item in candidates[:120]:
            counts = Counter(item["values"])

            print(
                f"  off=0x{item['offset']:03x} "
                f"unique={item['unique']:2d} "
                f"majority={item['majority_ratio'] * 100:6.2f}% "
                f"top={counts.most_common(8)}"
            )

        print()
        print("U16 FIELD CANDIDATES")

        u16_candidates = []

        for offset in range(0, PAYLOAD_SIZE - 1, 2):
            le_values = [
                struct.unpack_from("<H", payload, offset)[0]
                for payload in payloads
            ]

            be_values = [
                struct.unpack_from(">H", payload, offset)[0]
                for payload in payloads
            ]

            for endian, values in [("LE", le_values), ("BE", be_values)]:
                unique = len(set(values))
                majority_count = Counter(values).most_common(1)[0][1]
                majority_ratio = majority_count / len(values)

                increasing, decreasing = monotonic_score(values)

                header_score = correlation_like(values, first_headers)
                t_score = correlation_like(values, t_numbers)
                block_score = correlation_like(values, first_blocks)

                if (
                    unique <= 16
                    or majority_ratio >= 0.75
                    or header_score >= 0.75
                    or t_score >= 0.75
                    or block_score >= 0.75
                ):
                    u16_candidates.append({
                        "offset": offset,
                        "endian": endian,
                        "values": values,
                        "unique": unique,
                        "majority_ratio": majority_ratio,
                        "increasing": increasing,
                        "decreasing": decreasing,
                        "header_score": header_score,
                        "t_score": t_score,
                        "block_score": block_score,
                    })

        u16_candidates.sort(
            key=lambda item: (
                -max(
                    item["header_score"],
                    item["t_score"],
                    item["block_score"],
                ),
                item["unique"],
                -item["majority_ratio"],
                item["offset"],
            )
        )

        for item in u16_candidates[:100]:
            values = item["values"]
            counts = Counter(values)

            print(
                f"  off=0x{item['offset']:03x} "
                f"{item['endian']} "
                f"unique={item['unique']:2d} "
                f"majority={item['majority_ratio'] * 100:6.2f}% "
                f"inc={item['increasing']:2d} "
                f"dec={item['decreasing']:2d} "
                f"corr_header={item['header_score']:.2f} "
                f"corr_t={item['t_score']:.2f} "
                f"corr_block={item['block_score']:.2f} "
                f"min={min(values):5d} "
                f"max={max(values):5d} "
                f"top={counts.most_common(6)}"
            )

        print()
        print("U32 FIELD CANDIDATES")

        u32_candidates = []

        for offset in range(0, PAYLOAD_SIZE - 3, 4):
            le_values = [
                struct.unpack_from("<I", payload, offset)[0]
                for payload in payloads
            ]

            be_values = [
                struct.unpack_from(">I", payload, offset)[0]
                for payload in payloads
            ]

            for endian, values in [("LE", le_values), ("BE", be_values)]:
                unique = len(set(values))
                majority_count = Counter(values).most_common(1)[0][1]
                majority_ratio = majority_count / len(values)

                increasing, decreasing = monotonic_score(values)

                header_score = correlation_like(values, first_headers)
                t_score = correlation_like(values, t_numbers)
                block_score = correlation_like(values, first_blocks)

                if (
                    unique <= 16
                    or majority_ratio >= 0.75
                    or header_score >= 0.75
                    or t_score >= 0.75
                    or block_score >= 0.75
                ):
                    u32_candidates.append({
                        "offset": offset,
                        "endian": endian,
                        "values": values,
                        "unique": unique,
                        "majority_ratio": majority_ratio,
                        "increasing": increasing,
                        "decreasing": decreasing,
                        "header_score": header_score,
                        "t_score": t_score,
                        "block_score": block_score,
                    })

        u32_candidates.sort(
            key=lambda item: (
                -max(
                    item["header_score"],
                    item["t_score"],
                    item["block_score"],
                ),
                item["unique"],
                -item["majority_ratio"],
                item["offset"],
            )
        )

        for item in u32_candidates[:80]:
            values = item["values"]
            counts = Counter(values)

            print(
                f"  off=0x{item['offset']:03x} "
                f"{item['endian']} "
                f"unique={item['unique']:2d} "
                f"majority={item['majority_ratio'] * 100:6.2f}% "
                f"inc={item['increasing']:2d} "
                f"dec={item['decreasing']:2d} "
                f"corr_header={item['header_score']:.2f} "
                f"corr_t={item['t_score']:.2f} "
                f"corr_block={item['block_score']:.2f} "
                f"min={min(values):10d} "
                f"max={max(values):10d} "
                f"top={counts.most_common(5)}"
            )

print()
print("=" * 120)
print("OBJECT REFERENCE TABLE")
print("=" * 120)

for object_length in [39, 52]:
    print()
    print(f"TYPE {object_length}")

    for index, obj in enumerate(objects[object_length]):
        print(
            f"index={index:02d} "
            f"file={obj['file']:16s} "
            f"t={obj['t_number']:3d} "
            f"object={obj['object_index']:02d} "
            f"first_block={obj['first_block']:03d} "
            f"first_header=0x{obj['first_header']:08x} "
            f"last_header=0x{obj['last_header']:08x}"
        )
