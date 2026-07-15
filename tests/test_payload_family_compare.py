from pathlib import Path
from collections import Counter
import hashlib

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

PAYLOADS = []
for n in range(154, 175):
    for p in ROOT.rglob(f"T{n}.ithmb"):
        PAYLOADS.append(p)

def entropy_like(chunk):
    if not chunk:
        return 0
    c = Counter(chunk)
    return len(c)

def main():
    print("=" * 100)
    print("PAYLOAD FAMILY COMPARE")
    print("=" * 100)

    files = sorted(PAYLOADS)
    for p in files:
        data = p.read_bytes()
        rel = p.relative_to(ROOT)
        print()
        print("-" * 100)
        print(f"{rel} size={len(data)} sha1={hashlib.sha1(data).hexdigest()[:12]}")

        print("first 64:")
        print(" ".join(f"{b:02x}" for b in data[:64]))

        print("block stats:")
        for off in range(0, min(len(data), 0x20000), 0x1000):
            chunk = data[off:off+0x1000]
            zeros = chunk.count(0)
            ff = chunk.count(0xff)
            unique = entropy_like(chunk)
            print(f"  off=0x{off:08x} unique={unique:3d} zero={zeros:4d} ff={ff:4d}")

    print()
    print("=" * 100)
    print("COMMON 16-BYTE PREFIXES")
    print("=" * 100)

    prefixes = Counter()
    for p in files:
        data = p.read_bytes()
        for off in range(0, len(data) - 16, 16):
            prefixes[data[off:off+16]] += 1

    for block, count in prefixes.most_common(40):
        if count < 4:
            break
        print(f"count={count:5d} hex={block.hex()}")

if __name__ == "__main__":
    main()

