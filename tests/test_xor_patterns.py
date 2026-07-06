from pathlib import Path
from collections import Counter
import math

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

TARGETS = [b"mhfd", b"mhli", b"mhii", b"mhod", b"SQLite", b"bplist", b"Photo", b"iPod"]

def entropy(data):
    if not data:
        return 0
    c = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

def ascii_preview(data):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in data[:128])

def main():
    data = DB.read_bytes()

    print("=" * 100)
    print("XOR PATTERN TEST")
    print("=" * 100)
    print(f"size: {len(data)}")
    print(f"entropy: {entropy(data):.4f}")
    print()

    print("TEST SINGLE-BYTE XOR FOR KNOWN HEADERS AT OFFSET 0")
    print("-" * 100)

    for key in range(256):
        decoded = bytes(x ^ key for x in data[:256])
        for target in TARGETS:
            if target in decoded:
                print(f"key=0x{key:02x} contains {target!r}")
                print(ascii_preview(decoded))
                print()

    print("=" * 100)
    print("TEST REPEATING XOR KEY LENGTHS 2-16 USING ENTROPY")
    print("=" * 100)

    # If XOR with repeating key, byte distributions by key position may differ.
    for key_len in range(2, 17):
        entropies = []
        for pos in range(key_len):
            stream = data[pos::key_len]
            entropies.append(entropy(stream))
        avg = sum(entropies) / len(entropies)
        spread = max(entropies) - min(entropies)
        print(f"key_len={key_len:2d} avg_entropy={avg:.4f} spread={spread:.4f}")

    print()
    print("=" * 100)
    print("AUTOCORRELATION / REPEATED BLOCK CHECK")
    print("=" * 100)

    for shift in [1,2,3,4,5,6,7,8,12,16,24,32,64,128,256,512,1024]:
        same = 0
        total = len(data) - shift
        for i in range(total):
            if data[i] == data[i + shift]:
                same += 1
        pct = same / total * 100
        print(f"shift={shift:4d} same_byte={pct:.3f}%")

if __name__ == "__main__":
    main()
