from pathlib import Path
import struct
import math
import hashlib

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")
OUT = Path("output/t156_segments")
OUT.mkdir(parents=True, exist_ok=True)

BLOCK_SIZE = 0x1000
HEADER_SIZE = 4

data = SRC.read_bytes()

blocks = []
for index, off in enumerate(range(0, len(data), BLOCK_SIZE)):
    block = data[off:off + BLOCK_SIZE]

    if len(block) != BLOCK_SIZE:
        continue

    header = struct.unpack(">I", block[:4])[0]
    payload = block[HEADER_SIZE:]

    blocks.append({
        "index": index,
        "offset": off,
        "header": header,
        "payload": payload,
    })

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

separator_indexes = [
    block["index"]
    for block in blocks
    if block["header"] == 0
]

print("=" * 100)
print("T156 SEGMENT MAP")
print("=" * 100)
print(f"full blocks: {len(blocks)}")
print(f"zero-header separators: {separator_indexes}")
print()

segments = []
current = []

for block in blocks:
    if block["header"] == 0:
        if current:
            segments.append(current)
            current = []
        continue

    current.append(block)

if current:
    segments.append(current)

print(f"segments: {len(segments)}")
print()

for segment_index, segment in enumerate(segments):
    payload = b"".join(block["payload"] for block in segment)

    first_block = segment[0]["index"]
    last_block = segment[-1]["index"]

    first_header = segment[0]["header"]
    last_header = segment[-1]["header"]

    unique = len(set(payload))
    zero_count = payload.count(0)
    low15 = sum(value <= 15 for value in payload)
    low31 = sum(value <= 31 for value in payload)
    low63 = sum(value <= 63 for value in payload)

    sha1 = hashlib.sha1(payload).hexdigest()

    output_file = OUT / (
        f"segment_{segment_index:02d}"
        f"_blocks_{first_block:03d}-{last_block:03d}.bin"
    )
    output_file.write_bytes(payload)

    print("-" * 100)
    print(
        f"segment={segment_index:02d} "
        f"blocks={first_block:03d}-{last_block:03d} "
        f"count={len(segment):3d}"
    )
    print(
        f"headers=0x{first_header:08x}->0x{last_header:08x} "
        f"bytes={len(payload)}"
    )
    print(
        f"unique={unique} "
        f"zeros={zero_count} "
        f"<=15={low15} "
        f"<=31={low31} "
        f"<=63={low63} "
        f"entropy={entropy(payload):.4f}"
    )
    print(f"sha1={sha1}")
    print(f"saved={output_file}")

print()
print("=" * 100)
print("SEPARATOR BLOCK DETAILS")
print("=" * 100)

for block in blocks:
    if block["header"] != 0:
        continue

    payload = block["payload"]

    print(
        f"block={block['index']:03d} "
        f"offset=0x{block['offset']:08x} "
        f"unique={len(set(payload)):3d} "
        f"zeros={payload.count(0):4d} "
        f"entropy={entropy(payload):.4f} "
        f"first32={payload[:32].hex(' ')}"
    )
