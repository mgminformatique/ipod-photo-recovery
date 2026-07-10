from pathlib import Path
import struct
import math

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")
BLOCK_SIZE = 0x1000
HEADER_SIZE = 4
MAX_SHIFT = 128

data = SRC.read_bytes()

blocks = []
headers = []

for off in range(0, len(data), BLOCK_SIZE):
    block = data[off:off + BLOCK_SIZE]
    if len(block) != BLOCK_SIZE:
        continue

    headers.append(struct.unpack(">I", block[:4])[0])
    blocks.append(block[HEADER_SIZE:])

print("=" * 100)
print("T156 BLOCK SEQUENCE ANALYSIS")
print("=" * 100)
print(f"full blocks: {len(blocks)}")
print()

print("HEADER SEQUENCE")
print("-" * 100)

good = 0

for i, value in enumerate(headers):
    expected = headers[0] + i * 4
    ok = value == expected

    if ok:
        good += 1

    if i < 30 or not ok:
        print(
            f"block={i:03d} "
            f"header=0x{value:08x} "
            f"expected=0x{expected:08x} "
            f"{'OK' if ok else 'MISMATCH'}"
        )

print()
print(f"exact counter matches: {good}/{len(headers)}")
print()

def stats(buf):
    unique = len(set(buf))
    zeros = buf.count(0)
    small15 = sum(v <= 15 for v in buf)
    small31 = sum(v <= 31 for v in buf)
    small63 = sum(v <= 63 for v in buf)

    counts = [0] * 256
    for value in buf:
        counts[value] += 1

    entropy = 0.0
    total = len(buf)

    for count in counts:
        if count:
            p = count / total
            entropy -= p * math.log2(p)

    return unique, zeros, small15, small31, small63, entropy

print("BLOCK STATISTICS")
print("-" * 100)

for i, block in enumerate(blocks[:40]):
    unique, zeros, small15, small31, small63, entropy = stats(block)

    print(
        f"block={i:03d} "
        f"unique={unique:3d} "
        f"zero={zeros:4d} "
        f"<=15={small15:4d} "
        f"<=31={small31:4d} "
        f"<=63={small63:4d} "
        f"entropy={entropy:5.2f}"
    )

print()
print("BEST SHIFT BETWEEN ADJACENT BLOCKS")
print("-" * 100)

for i in range(min(40, len(blocks) - 1)):
    a = blocks[i]
    b = blocks[i + 1]

    best_matches = -1
    best_shift = 0
    best_total = 1

    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        if shift < 0:
            aa = a[-shift:]
            bb = b[:len(aa)]
        elif shift > 0:
            aa = a[:-shift]
            bb = b[shift:]
        else:
            aa = a
            bb = b

        total = min(len(aa), len(bb))
        if total <= 0:
            continue

        matches = sum(x == y for x, y in zip(aa[:total], bb[:total]))

        if matches > best_matches:
            best_matches = matches
            best_shift = shift
            best_total = total

    percent = best_matches / best_total * 100

    print(
        f"{i:03d}->{i+1:03d} "
        f"best_shift={best_shift:+4d} "
        f"matches={best_matches:4d}/{best_total:4d} "
        f"{percent:6.2f}%"
    )
