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

# Positions qui semblent contenir surtout des structures fixes.
META_POSITIONS = {
    39: [0, 11, 12, 13, 24, 25, 26, 37, 38],
    52: [0, 11, 12, 13, 24, 25, 26, 37, 38, 39, 40, 50, 51],
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

    markers = [
        i for i, block in enumerate(blocks)
        if block["header"] in MARKERS
    ]

    boundaries = [-1] + markers + [len(blocks)]

    for object_index in range(len(boundaries) - 1):
        left = boundaries[object_index]
        right = boundaries[object_index + 1]

        first = left + 1
        length = right - left - 1

        if length not in VALID_LENGTHS:
            continue

        objects[length].append({
            "file": str(path.relative_to(CACHE)),
            "object_index": object_index,
            "first_block": first,
            "blocks": blocks[first:right],
        })


print("=" * 110)
print("PAYLOAD METADATA BLOCK FIELD ANALYSIS")
print("=" * 110)

for object_length in [39, 52]:
    group = objects[object_length]

    print()
    print("=" * 110)
    print(f"OBJECT LENGTH {object_length}")
    print("=" * 110)
    print(f"objects={len(group)}")

    for position in META_POSITIONS[object_length]:
        payloads = [
            obj["blocks"][position]["payload"]
            for obj in group
        ]

        print()
        print("-" * 110)
        print(f"POSITION {position:02d}")

        variable_offsets = []
        constant_offsets = []
        near_constant_offsets = []

        for offset in range(PAYLOAD_SIZE):
            values = [payload[offset] for payload in payloads]
            counts = Counter(values)
            value, count = counts.most_common(1)[0]
            ratio = count / len(values)

            if ratio == 1.0:
                constant_offsets.append((offset, value))
            elif ratio >= 0.80:
                near_constant_offsets.append((offset, value, ratio))
            else:
                variable_offsets.append(offset)

        print(
            f"constant={len(constant_offsets)} "
            f"near_constant_80={len(near_constant_offsets)} "
            f"variable={len(variable_offsets)}"
        )

        print("first variable offsets:")
        print(
            "  "
            + " ".join(
                f"0x{offset:03x}"
                for offset in variable_offsets[:120]
            )
        )

        print("first near-constant offsets:")
        for offset, value, ratio in near_constant_offsets[:80]:
            print(
                f"  off=0x{offset:03x} "
                f"majority=0x{value:02x} "
                f"ratio={ratio*100:6.2f}%"
            )

        print("u16/u32 candidate fields in first 256 bytes:")

        for offset in range(0, 256, 2):
            u16le_values = [
                struct.unpack_from("<H", payload, offset)[0]
                for payload in payloads
            ]
            u16be_values = [
                struct.unpack_from(">H", payload, offset)[0]
                for payload in payloads
            ]

            unique_le = len(set(u16le_values))
            unique_be = len(set(u16be_values))

            # Affiche seulement les champs ayant peu de valeurs distinctes
            # ou une progression potentiellement structurée.
            if unique_le <= 12 or unique_be <= 12:
                print(
                    f"  u16 off=0x{offset:03x} "
                    f"LE unique={unique_le:2d} "
                    f"min={min(u16le_values):5d} "
                    f"max={max(u16le_values):5d} "
                    f"top={Counter(u16le_values).most_common(5)} "
                    f"| BE unique={unique_be:2d} "
                    f"min={min(u16be_values):5d} "
                    f"max={max(u16be_values):5d}"
                )

        print("u32 candidates in first 256 bytes:")

        for offset in range(0, 256, 4):
            le_values = [
                struct.unpack_from("<I", payload, offset)[0]
                for payload in payloads
            ]
            be_values = [
                struct.unpack_from(">I", payload, offset)[0]
                for payload in payloads
            ]

            unique_le = len(set(le_values))
            unique_be = len(set(be_values))

            if unique_le <= 12 or unique_be <= 12:
                print(
                    f"  u32 off=0x{offset:03x} "
                    f"LE unique={unique_le:2d} "
                    f"min={min(le_values):10d} "
                    f"max={max(le_values):10d} "
                    f"top={Counter(le_values).most_common(5)} "
                    f"| BE unique={unique_be:2d} "
                    f"min={min(be_values):10d} "
                    f"max={max(be_values):10d}"
                )

print()
print("=" * 110)
print("CROSS-TYPE POSITION COMPARISON")
print("=" * 110)

common_positions = sorted(
    set(META_POSITIONS[39]) & set(META_POSITIONS[52])
)

for position in common_positions:
    a_payloads = [
        obj["blocks"][position]["payload"]
        for obj in objects[39]
    ]
    b_payloads = [
        obj["blocks"][position]["payload"]
        for obj in objects[52]
    ]

    a_template = bytes(
        Counter(payload[offset] for payload in a_payloads).most_common(1)[0][0]
        for offset in range(PAYLOAD_SIZE)
    )

    b_template = bytes(
        Counter(payload[offset] for payload in b_payloads).most_common(1)[0][0]
        for offset in range(PAYLOAD_SIZE)
    )

    matches = sum(x == y for x, y in zip(a_template, b_template))

    print(
        f"position={position:02d} "
        f"majority-template similarity="
        f"{matches}/{PAYLOAD_SIZE} "
        f"{matches/PAYLOAD_SIZE*100:6.2f}%"
    )
