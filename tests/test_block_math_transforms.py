from pathlib import Path
from collections import Counter
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    CACHE/"F05"/"T154.ithmb",
    CACHE/"F06"/"T155.ithmb",
    CACHE/"F07"/"T156.ithmb",
    CACHE/"F09"/"T158.ithmb",
    CACHE/"F10"/"T159.ithmb",
    CACHE/"F11"/"T160.ithmb",
    CACHE/"F12"/"T161.ithmb",
    CACHE/"F13"/"T162.ithmb",
]

BLOCK = 4096
MAX_BLOCKS = 80

def entropy(b):
    if not b:
        return 0
    c = Counter(b)
    n = len(b)
    return -sum((v/n) * math.log2(v/n) for v in c.values())

def xor_constant(a, b):
    x = bytes(i ^ j for i, j in zip(a, b))
    common, count = Counter(x).most_common(1)[0]
    return common, count / len(x)

def add_constant(a, b):
    d = bytes((j - i) & 0xff for i, j in zip(a, b))
    common, count = Counter(d).most_common(1)[0]
    return common, count / len(d)

def sub_constant(a, b):
    d = bytes((i - j) & 0xff for i, j in zip(a, b))
    common, count = Counter(d).most_common(1)[0]
    return common, count / len(d)

def bit_not_match(a, b):
    return sum(((i ^ 0xff) == j) for i, j in zip(a, b)) / len(a)

def byte_swap16(buf):
    out = bytearray()
    for i in range(0, len(buf)-1, 2):
        out.append(buf[i+1])
        out.append(buf[i])
    return bytes(out)

def compare(label, a, b):
    same = sum(i == j for i, j in zip(a, b)) / len(a)
    xv, xr = xor_constant(a, b)
    av, ar = add_constant(a, b)
    sv, sr = sub_constant(a, b)
    nr = bit_not_match(a, b)

    if max(same, xr, ar, sr, nr) >= 0.70:
        print(label)
        print(f"  same={same:.3f}")
        print(f"  xor_const=0x{xv:02x} ratio={xr:.3f}")
        print(f"  add_const=0x{av:02x} ratio={ar:.3f}")
        print(f"  sub_const=0x{sv:02x} ratio={sr:.3f}")
        print(f"  not_ratio={nr:.3f}")

print("="*100)
print("BLOCK MATH TRANSFORM SCAN")
print("="*100)

blocks = []

for p in FILES:
    data = p.read_bytes()
    rel = str(p.relative_to(CACHE))

    for off in range(0, min(len(data), BLOCK * MAX_BLOCKS), BLOCK):
        chunk = data[off:off+BLOCK]
        if len(chunk) != BLOCK:
            continue
        if chunk.count(0) == BLOCK or chunk.count(1) == BLOCK:
            continue

        e = entropy(chunk)
        blocks.append((rel, off, chunk, e))

print("blocks:", len(blocks))

for i in range(len(blocks)):
    fa, oa, a, ea = blocks[i]

    for j in range(i+1, len(blocks)):
        fb, ob, b, eb = blocks[j]

        if fa == fb and abs(oa - ob) <= BLOCK:
            continue

        label = f"{fa}@0x{oa:06x} <-> {fb}@0x{ob:06x} ent={ea:.2f}/{eb:.2f}"
        compare(label, a, b)

        bs = byte_swap16(b)
        compare(label + " BYTE_SWAP16_B", a, bs)

print("done")
