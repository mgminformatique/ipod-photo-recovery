from pathlib import Path
from collections import Counter

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

RECORD_SIZES = [
    8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64,
    72, 80, 88, 96, 104, 112, 120, 128, 160, 192, 224, 256
]

print("Photo Database record-size scan")
print("Size:", len(data))
print("=" * 80)

for size in RECORD_SIZES:
    blocks = [data[i:i+size] for i in range(0, len(data) - size, size)]

    first8 = [b[:8] for b in blocks]
    first16 = [b[:16] for b in blocks if len(b) >= 16]

    c8 = Counter(first8).most_common(5)
    c16 = Counter(first16).most_common(5)

    repeat8 = sum(count for _, count in c8 if count > 1)
    repeat16 = sum(count for _, count in c16 if count > 1)

    if repeat8 > 2 or repeat16 > 2:
        print()
        print(f"record_size={size}")
        print("repeat8 :", repeat8, c8)
        print("repeat16:", repeat16, c16)
