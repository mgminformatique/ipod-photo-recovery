from pathlib import Path
import struct
from collections import Counter

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")

def u16le(b,o): return struct.unpack_from("<H", b, o)[0]
def u32le(b,o): return struct.unpack_from("<I", b, o)[0]

def main():
    data = DB.read_bytes()

    print("=" * 100)
    print("PHOTO DB RECORD STRUCTURE ANALYZER")
    print("=" * 100)
    print(f"size={len(data)}")

    for rec_size in [16, 20, 24, 32, 40, 48, 64, 88, 96, 128]:
        print()
        print("-" * 100)
        print(f"RECORD SIZE {rec_size}")

        best = []
        for start in range(rec_size):
            records = (len(data) - start) // rec_size
            zero_tail = 0
            low_unique = []

            for i in range(min(records, 500)):
                off = start + i * rec_size
                r = data[off:off+rec_size]
                if r[-4:] == b"\x00\x00\x00\x00":
                    zero_tail += 1
                low_unique.append(len(set(r)))

            avg_unique = sum(low_unique) / len(low_unique) if low_unique else 0
            best.append((zero_tail, -avg_unique, start, records, avg_unique))

        for zero_tail, neg_avg, start, records, avg_unique in sorted(best, reverse=True)[:8]:
            print(f"start={start:3d} records={records:5d} zero_tail={zero_tail:4d} avg_unique={avg_unique:6.2f}")

    print()
    print("=" * 100)
    print("U32 OFFSET-LIKE VALUES")
    print("=" * 100)

    hits = []
    for off in range(0, len(data)-4):
        v = u32le(data, off)
        if 0 < v < len(data):
            hits.append((off, v))

    print(f"hits={len(hits)}")
    for off, v in hits[:300]:
        print(f"off=0x{off:08x} value=0x{v:08x} {v}")

if __name__ == "__main__":
    main()
