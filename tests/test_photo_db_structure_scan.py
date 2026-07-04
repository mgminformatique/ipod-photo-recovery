from pathlib import Path
from collections import Counter
import struct
import math

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

print("=" * 100)
print("PHOTO DATABASE STRUCTURE SCAN")
print("=" * 100)
print("size:", len(data))
print()

def entropy(chunk):
    if not chunk:
        return 0
    c = Counter(chunk)
    total = len(chunk)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

print("Entropy by 512-byte blocks:")
for off in range(0, len(data), 512):
    chunk = data[off:off+512]
    e = entropy(chunk)
    zeros = chunk.count(0)
    ff = chunk.count(255)
    if e < 6.5 or zeros > 30 or ff > 30:
        print(f"0x{off:08x} entropy={e:.3f} zeros={zeros} ff={ff}")

print()
print("Possible repeated 16-byte blocks:")
blocks = Counter(data[i:i+16] for i in range(0, len(data)-16, 16))
for block, count in blocks.most_common(30):
    if count > 1:
        print(f"count={count:3d} {block.hex(' ')}")

print()
print("Possible u32 offsets into file:")
hits = []
for off in range(0, len(data)-4):
    le = struct.unpack_from("<I", data, off)[0]
    if 0 <= le < len(data):
        hits.append((off, le))

print("u32 offset-like hits:", len(hits))
for off, val in hits[:200]:
    print(f"at=0x{off:08x} value=0x{val:08x}")

print()
print("Possible record sizes with repeating patterns:")
for rec_size in [16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 512]:
    scores = []
    for start in range(0, min(4096, len(data) - rec_size * 4), 16):
        vals = []
        for i in range(8):
            pos = start + i * rec_size
            if pos + 4 <= len(data):
                vals.append(data[pos:pos+4])
        repeats = len(vals) - len(set(vals))
        if repeats:
            scores.append((repeats, start))
    if scores:
        best = max(scores)
        print(f"record_size={rec_size:3d} best_repeat={best[0]} start=0x{best[1]:x}")

print()
print("done")
