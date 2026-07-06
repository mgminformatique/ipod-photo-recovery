from pathlib import Path
from collections import Counter
import math

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

def entropy(chunk):
    if not chunk:
        return 0
    c = Counter(chunk)
    total = len(chunk)
    return -sum((n/total) * math.log2(n/total) for n in c.values())

def main():
    data = DB.read_bytes()

    print("=" * 80)
    print("ENTROPY AND XOR CHECK")
    print("=" * 80)
    print(f"size: {len(data)}")
    print(f"global entropy: {entropy(data):.4f}")
    print()

    for block_size in [256, 512, 1024, 4096]:
        print("=" * 80)
        print(f"BLOCK SIZE {block_size}")
        print("=" * 80)

        rows = []
        for off in range(0, len(data), block_size):
            chunk = data[off:off+block_size]
            rows.append((entropy(chunk), off, len(chunk)))

        rows.sort(reverse=True)

        print("highest entropy blocks:")
        for e, off, ln in rows[:10]:
            print(f"0x{off:08x} len={ln:4d} entropy={e:.4f}")

        print()
        print("lowest entropy blocks:")
        for e, off, ln in rows[-10:]:
            print(f"0x{off:08x} len={ln:4d} entropy={e:.4f}")

        print()

    print("=" * 80)
    print("SIMPLE XOR HEADER TEST")
    print("=" * 80)

    known = [b"mhfd", b"mhli", b"mhii", b"mhod", b"SQLite", b"bplist", b"iPod", b"Photo"]

    first = data[:64]

    for sig in known:
        print()
        print(f"testing signature: {sig!r}")
        for pos in range(0, min(32, len(first) - len(sig))):
            key = first[pos] ^ sig[0]
            decoded = bytes(x ^ key for x in first[pos:pos+len(sig)])
            if decoded == sig:
                print(f"possible xor key=0x{key:02x} at offset 0x{pos:08x}")

    print()
    print("=" * 80)
    print("BYTE FREQUENCY TOP 30")
    print("=" * 80)

    c = Counter(data)
    for byte, count in c.most_common(30):
        print(f"0x{byte:02x} count={count}")


if __name__ == "__main__":
    main()
