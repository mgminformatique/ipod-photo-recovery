from pathlib import Path
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

def score_24(data):
    if len(data) < 240:
        return 0, 0

    chunks = [data[i:i+24] for i in range(0, min(len(data), 24000), 24)]
    zero_tail = sum(c[12:24].count(0) >= 8 for c in chunks if len(c) == 24)
    repeated = len(chunks) - len(set(chunks))

    return zero_tail, repeated

def main():
    print("=" * 100)
    print("ITHMB RECORD VS PAYLOAD CLASSIFIER")
    print("=" * 100)

    for path in sorted(ROOT.rglob("*.ithmb")):
        data = path.read_bytes()
        zero_tail, repeated = score_24(data)
        size = len(data)

        label = "UNKNOWN"
        if zero_tail > 100 and repeated > 100:
            label = "24-BYTE RECORD/TABLE"
        elif size > 500000:
            label = "POSSIBLE PAYLOAD"
        else:
            label = "UNKNOWN/SMALL"

        print(
            f"{path.relative_to(ROOT)} "
            f"size={size:8d} "
            f"zero_tail={zero_tail:5d} "
            f"repeated={repeated:5d} "
            f"{label}"
        )

if __name__ == "__main__":
    main()
