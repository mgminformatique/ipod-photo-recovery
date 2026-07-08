from pathlib import Path
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F05" / "T103.ithmb"
RECORD_SIZE = 24

def score_alignment(data, start):
    chunks = []
    zero_prefix = 0

    for off in range(start, len(data) - RECORD_SIZE, RECORD_SIZE):
        chunk = data[off:off+RECORD_SIZE]
        chunks.append(chunk)

        if chunk[:12] == b"\x00" * 12:
            zero_prefix += 1

    c = Counter(chunks)
    repeats = sum(v for v in c.values() if v > 1)

    return len(chunks), zero_prefix, repeats, c.most_common(5)

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T103 ALIGNMENT SCORE")
    print("=" * 100)
    print(f"size: {len(data)}")
    print()

    for start in range(24):
        total, zero_prefix, repeats, common = score_alignment(data, start)
        print(
            f"start={start:2d} "
            f"records={total:5d} "
            f"zero_prefix={zero_prefix:5d} "
            f"repeat_records={repeats:5d}"
        )

    print()
    print("=" * 100)
    print("BEST ALIGNMENT DETAILS")
    print("=" * 100)

    best = None
    for start in range(24):
        total, zero_prefix, repeats, common = score_alignment(data, start)
        key = (zero_prefix, repeats)
        if best is None or key > best[0]:
            best = (key, start, total, zero_prefix, repeats, common)

    _, start, total, zero_prefix, repeats, common = best
    print(f"best start={start}")
    print(f"records={total}")
    print(f"zero_prefix={zero_prefix}")
    print(f"repeat_records={repeats}")
    print()

    print("common records:")
    for chunk, count in common:
        print(f"count={count} hex={chunk.hex()}")

if __name__ == "__main__":
    main()
