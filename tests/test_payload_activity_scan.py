from pathlib import Path
from collections import Counter
import math

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    ROOT / "F05" / "T154.ithmb",
    ROOT / "F06" / "T155.ithmb",
    ROOT / "F07" / "T156.ithmb",
    ROOT / "F08" / "T157.ithmb",
    ROOT / "F09" / "T158.ithmb",
]

def score(chunk):
    if not chunk:
        return 0, 0, 0

    c = Counter(chunk)
    zero = c[0] / len(chunk) * 100
    ff = c[255] / len(chunk) * 100
    unique = len(c)

    return zero, ff, unique

def main():
    print("=" * 100)
    print("PAYLOAD ACTIVITY SCAN")
    print("=" * 100)

    block = 4096

    for path in FILES:
        data = path.read_bytes()
        print()
        print("=" * 100)
        print(path.relative_to(ROOT), "size", len(data))
        print("-" * 100)

        rows = []
        for off in range(0, len(data), block):
            chunk = data[off:off+block]
            zero, ff, unique = score(chunk)
            rows.append((unique, zero, ff, off))

        rows.sort(reverse=True)

        print("MOST ACTIVE BLOCKS")
        for unique, zero, ff, off in rows[:30]:
            print(
                f"off=0x{off:08x} "
                f"unique={unique:3d} "
                f"zero={zero:6.2f}% "
                f"ff={ff:6.2f}%"
            )

if __name__ == "__main__":
    main()
