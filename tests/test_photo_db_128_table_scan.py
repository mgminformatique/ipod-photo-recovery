from pathlib import Path
import struct
import math
from collections import Counter

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

print("=" * 100)
print("PHOTO DATABASE 128-TABLE SCAN")
print("=" * 100)
print("size:", len(data))
print()


def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())


ENTRY_SIZES = [1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 112, 128]

for entry_size in ENTRY_SIZES:
    table_size = entry_size * 128

    if table_size > len(data):
        continue

    print("=" * 100)
    print(f"entry_size={entry_size} table_size={table_size}")

    candidates = []

    for start in range(0, len(data) - table_size, 1):
        table = data[start:start + table_size]

        e = entropy(table)
        zeros = table.count(0)

        score = 0

        # Beaucoup de 0 ou basse entropie = possiblement table
        if e < 6.5:
            score += int((6.5 - e) * 10)

        if zeros > table_size * 0.05:
            score += int((zeros / table_size) * 20)

        # Test champs u16/u32 qui restent petits
        small_u16 = 0
        small_u32 = 0

        for i in range(128):
            pos = start + i * entry_size

            if pos + 2 <= len(data):
                v16 = struct.unpack_from("<H", data, pos)[0]
                if v16 < 512:
                    small_u16 += 1

            if pos + 4 <= len(data):
                v32 = struct.unpack_from("<I", data, pos)[0]
                if v32 < len(data):
                    small_u32 += 1

        if small_u16 > 16:
            score += small_u16

        if small_u32 > 8:
            score += small_u32 * 2

        if score > 40:
            candidates.append((score, start, e, zeros, small_u16, small_u32))

    candidates.sort(reverse=True)

    for score, start, e, zeros, small_u16, small_u32 in candidates[:20]:
        print(
            f"start=0x{start:08x} "
            f"score={score:4d} "
            f"entropy={e:.3f} "
            f"zeros={zeros:4d} "
            f"small_u16={small_u16:3d} "
            f"small_u32={small_u32:3d}"
        )

print()
print("done")
