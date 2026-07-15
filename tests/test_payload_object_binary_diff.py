from pathlib import Path
import struct
from collections import defaultdict, Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4
PAYLOAD_SIZE = BLOCK_SIZE - HEADER_SIZE

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

MARKERS = {
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


def contiguous_runs(offsets):
    if not offsets:
        return []

    runs = []
    start = offsets[0]
    previous = offsets[0]

    for value in offsets[1:]:
        if value == previous + 1:
            previous = value
            continue

        runs.append((start, previous))
        start = value
        previous = value

    runs.append((start, previous))
    return runs


def hexdump_slice(data, start, end):
    chunk = data[start:end + 1]
    return " ".join(f"{value:02x}" for value in chunk)


objects = defaultdict(list)

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw_file = path.read_bytes()
    blocks = []

    for block_index, offset in enumerate(range(0, len(raw_file), BLOCK_SIZE)):
        raw = raw_file[offset:offset + BLOCK_SIZE]

        if len(raw) != BLOCK_SIZE:
            continue

        blocks.append({
            "global_block": block_index,
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


print("=" * 120)
print("PAYLOAD OBJECT BINARY DIFF")
print("=" * 120)

for object_length in [39, 52]:
    group = objects[object_length]

    print()
    print("=" * 120)
    print(f"{VALID_LENGTHS[object_length]}")
    print("=" * 120)
    print(f"objects={len(group)}")

    for pair_index in range(len(group) - 1):
        left = group[pair_index]
        right = group[pair_index + 1]

        print()
        print("-" * 120)
        print(
            f"PAIR {pair_index:02d}: "
            f"{left['file']} object={left['object_index']:02d} "
            f"header=0x{left['first_header']:08x} "
            f"vs "
            f"{right['file']} object={right['object_index']:02d} "
            f"header=0x{right['first_header']:08x}"
        )

        total_changed = 0
        changed_blocks = []

        for position in range(object_length):
            a = left["blocks"][position]["payload"]
            b = right["blocks"][position]["payload"]

            changed_offsets = [
                offset
                for offset, (x, y) in enumerate(zip(a, b))
                if x != y
            ]

            if not changed_offsets:
                continue

            total_changed += len(changed_offsets)
            changed_blocks.append(position)

            runs = contiguous_runs(changed_offsets)

            print(
                f"BLOCK position={position:02d} "
                f"changed={len(changed_offsets):4d}/{PAYLOAD_SIZE} "
                f"{len(changed_offsets) / PAYLOAD_SIZE * 100:6.2f}% "
                f"runs={len(runs)}"
            )

            for run_start, run_end in runs[:20]:
                run_length = run_end - run_start + 1

                print(
                    f"  run=0x{run_start:03x}-0x{run_end:03x} "
                    f"len={run_length:4d}"
                )

                if run_length <= 32:
                    print(
                        f"    A: {hexdump_slice(a, run_start, run_end)}"
                    )
                    print(
                        f"    B: {hexdump_slice(b, run_start, run_end)}"
                    )

            # Inspecte explicitement les mini-footers soupçonnés.
            for footer_offset in [0x3FC, 0x7FC, 0xBFC]:
                if footer_offset + 4 <= PAYLOAD_SIZE:
                    a_value_be = struct.unpack_from(">I", a, footer_offset)[0]
                    b_value_be = struct.unpack_from(">I", b, footer_offset)[0]

                    a_value_le = struct.unpack_from("<I", a, footer_offset)[0]
                    b_value_le = struct.unpack_from("<I", b, footer_offset)[0]

                    if a_value_be != b_value_be:
                        print(
                            f"  footer off=0x{footer_offset:03x} "
                            f"BE 0x{a_value_be:08x} -> 0x{b_value_be:08x} "
                            f"LE 0x{a_value_le:08x} -> 0x{b_value_le:08x}"
                        )

        print(
            f"SUMMARY changed_blocks={changed_blocks} "
            f"total_changed_bytes={total_changed}"
        )

print()
print("=" * 120)
print("FOOTER VALUE TABLE")
print("=" * 120)

for object_length in [39, 52]:
    print()
    print(f"{VALID_LENGTHS[object_length]}")

    for object_index, obj in enumerate(objects[object_length]):
        print(
            f"object={object_index:02d} "
            f"file={obj['file']:16s} "
            f"obj={obj['object_index']:02d} "
            f"first_header=0x{obj['first_header']:08x}"
        )

        for position in range(object_length):
            payload = obj["blocks"][position]["payload"]

            values = []

            for footer_offset in [0x3FC, 0x7FC, 0xBFC]:
                if footer_offset + 4 <= PAYLOAD_SIZE:
                    value = struct.unpack_from(">I", payload, footer_offset)[0]
                    values.append(
                        f"0x{footer_offset:03x}=0x{value:08x}"
                    )

            if any(
                struct.unpack_from(">I", payload, footer_offset)[0] != 0
                for footer_offset in [0x3FC, 0x7FC, 0xBFC]
                if footer_offset + 4 <= PAYLOAD_SIZE
            ):
                print(
                    f"  pos={position:02d} "
                    + " ".join(values)
                )
