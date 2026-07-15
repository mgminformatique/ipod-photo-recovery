from pathlib import Path
import struct
import math
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

MARKER_HEADERS = {
    0x00000000: "ZERO_MARKER",
    0x0D000000: "0D_MARKER",
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


files = []

for path in CACHE.rglob("T*.ithmb"):
    number = get_t_number(path)

    if number in T_NUMBERS and number not in EXCLUDED:
        files.append(path)

files.sort(key=lambda path: get_t_number(path) or -1)

length_distribution = Counter()
marker_distribution = Counter()

print("=" * 110)
print("PAYLOAD MARKER PARSER")
print("=" * 110)

for path in files:
    data = path.read_bytes()
    blocks = []

    for index, offset in enumerate(range(0, len(data), BLOCK_SIZE)):
        raw = data[offset:offset + BLOCK_SIZE]

        if len(raw) != BLOCK_SIZE:
            continue

        header = struct.unpack(">I", raw[:HEADER_SIZE])[0]
        payload = raw[HEADER_SIZE:]

        blocks.append({
            "index": index,
            "offset": offset,
            "header": header,
            "payload": payload,
            "entropy": entropy(payload),
        })

    marker_indexes = [
        index
        for index, block in enumerate(blocks)
        if block["header"] in MARKER_HEADERS
    ]

    boundaries = [-1] + marker_indexes + [len(blocks)]

    objects = []

    for boundary_index in range(len(boundaries) - 1):
        left = boundaries[boundary_index]
        right = boundaries[boundary_index + 1]

        first = left + 1
        last = right - 1
        count = right - left - 1

        if count <= 0:
            continue

        object_blocks = blocks[first:right]

        plus4_good = sum(
            object_blocks[index]["header"]
            == object_blocks[index - 1]["header"] + 4
            for index in range(1, len(object_blocks))
        )

        plus4_total = max(0, len(object_blocks) - 1)

        low_positions = [
            local_index
            for local_index, block in enumerate(object_blocks)
            if block["entropy"] < 1.0
        ]

        if count == 52:
            object_type = "TYPE_A_52"
        elif count == 39:
            object_type = "TYPE_B_39"
        else:
            object_type = "PARTIAL"

        objects.append({
            "first": first,
            "last": last,
            "count": count,
            "type": object_type,
            "plus4_good": plus4_good,
            "plus4_total": plus4_total,
            "low_positions": low_positions,
        })

        length_distribution[count] += 1

    print()
    print("-" * 110)
    print(path.relative_to(CACHE))
    print(
        f"full_blocks={len(blocks)} "
        f"markers={len(marker_indexes)} "
        f"objects={len(objects)}"
    )

    print("markers:")

    for marker_index in marker_indexes:
        block = blocks[marker_index]
        marker_name = MARKER_HEADERS[block["header"]]

        previous_header = (
            blocks[marker_index - 1]["header"]
            if marker_index > 0
            else None
        )

        next_header = (
            blocks[marker_index + 1]["header"]
            if marker_index + 1 < len(blocks)
            else None
        )

        bridge = (
            previous_header is not None
            and next_header is not None
            and next_header == previous_header + 8
        )

        dominant_value, dominant_count = Counter(
            block["payload"]
        ).most_common(1)[0]

        print(
            f"  block={marker_index:03d} "
            f"type={marker_name:11s} "
            f"header=0x{block['header']:08x} "
            f"entropy={block['entropy']:.4f} "
            f"dominant=0x{dominant_value:02x} "
            f"{dominant_count / len(block['payload']) * 100:6.2f}% "
            f"bridge_plus8={bridge}"
        )

        marker_distribution[marker_name] += 1

    print("objects:")

    for object_index, obj in enumerate(objects):
        ratio = (
            obj["plus4_good"] / obj["plus4_total"] * 100
            if obj["plus4_total"]
            else 0.0
        )

        print(
            f"  object={object_index:02d} "
            f"blocks={obj['first']:03d}-{obj['last']:03d} "
            f"count={obj['count']:3d} "
            f"type={obj['type']:9s} "
            f"+4={obj['plus4_good']:2d}/{obj['plus4_total']:2d} "
            f"{ratio:6.2f}%"
        )

        print(
            "    low positions: "
            + (
                ",".join(str(position) for position in obj["low_positions"])
                if obj["low_positions"]
                else "none"
            )
        )

print()
print("=" * 110)
print("MARKER DISTRIBUTION")
print("=" * 110)

for marker_name, count in sorted(marker_distribution.items()):
    print(f"{marker_name:12s}: {count}")

print()
print("=" * 110)
print("CORRECTED OBJECT LENGTH DISTRIBUTION")
print("=" * 110)

for length, count in sorted(length_distribution.items()):
    label = (
        "TYPE_A"
        if length == 52
        else "TYPE_B"
        if length == 39
        else "PARTIAL"
    )

    print(
        f"length={length:3d} "
        f"objects={count:3d} "
        f"{label}"
    )
