from pathlib import Path
from collections import Counter
import math

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

def entropy(data):
    if not data:
        return 0
    c = Counter(data)
    total = len(data)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

def ascii_preview(data):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in data)

def main():
    print("=" * 100)
    print("CACHE FILE INVENTORY")
    print("=" * 100)
    print(f"root: {ROOT}")
    print()

    files = sorted([p for p in ROOT.rglob("*") if p.is_file()])

    for p in files:
        data = p.read_bytes()
        first = data[:32]
        rel = p.relative_to(ROOT)

        print("-" * 100)
        print(f"file: {rel}")
        print(f"size: {len(data)}")
        print(f"entropy: {entropy(data):.4f}")
        print("first32 hex:", " ".join(f"{x:02x}" for x in first))
        print("first32 ascii:", ascii_preview(first))

if __name__ == "__main__":
    main()
