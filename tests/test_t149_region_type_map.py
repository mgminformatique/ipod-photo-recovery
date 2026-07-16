from pathlib import Path
import struct
from collections import Counter

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def classify_block(data, off, size=0x100):
    vals = []
    for i in range(0, size, 2):
        if off + i + 2 <= len(data):
            vals.append(u16(data, off + i))

    if not vals:
        return "EMPTY"

    zeros = vals.count(0)
    unique = len(set(vals))

    ptr_like = sum(1 for v in vals if 0x0100 <= v < len(data) and v % 0x100 == 0)
    hi_ptr_like = sum(1 for v in vals if 0x0100 <= v < len(data))
    ascending_100 = sum(1 for a, b in zip(vals, vals[1:]) if b - a == 0x100)
    ascending_1 = sum(1 for a, b in zip(vals, vals[1:]) if b - a == 1)
    zero_every_other = sum(1 for i in range(1, len(vals), 2) if vals[i] == 0)

    if zeros > 100:
        kind = "MOSTLY_ZERO"
    elif ascending_100 > 40:
        kind = "PTR_PAGE_ASC_0x100"
    elif ptr_like > 40:
        kind = "PTR_PAGE_MIXED_0x100"
    elif zero_every_other > 40:
        kind = "U16_ZERO_INTERLEAVED"
    elif ascending_1 > 40:
        kind = "ASCENDING_CODES"
    elif unique > 100:
        kind = "DENSE_CODES"
    else:
        kind = "MIXED"

    return kind, {
        "zeros": zeros,
        "unique": unique,
        "ptr100": ptr_like,
        "ptrAny": hi_ptr_like,
        "asc100": ascending_100,
        "asc1": ascending_1,
        "zeroOdd": zero_every_other,
    }

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 REGION TYPE MAP")
    print("=" * 100)
    print(f"file size: {len(data)}")

    counts = Counter()

    for off in range(0, len(data), 0x100):
        res = classify_block(data, off)
        if isinstance(res, str):
            kind, stats = res, {}
        else:
            kind, stats = res

        counts[kind] += 1

        print(
            f"0x{off:08x} {kind:22s} "
            f"zeros={stats.get('zeros',0):3d} "
            f"unique={stats.get('unique',0):3d} "
            f"ptr100={stats.get('ptr100',0):3d} "
            f"ptrAny={stats.get('ptrAny',0):3d} "
            f"asc100={stats.get('asc100',0):3d} "
            f"asc1={stats.get('asc1',0):3d} "
            f"zeroOdd={stats.get('zeroOdd',0):3d}"
        )

    print()
    print("=" * 100)
    print("COUNTS")
    print("=" * 100)
    for k, v in counts.most_common():
        print(f"{k:22s} {v}")

if __name__ == "__main__":
    main()
