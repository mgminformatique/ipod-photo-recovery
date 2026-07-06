from pathlib import Path
import struct

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

targets = list(range(149, 175))

print("PHOTO DATABASE T-NUMBER SEQUENCE SCAN")
print("DB size:", len(data))

def read_u16(off, endian):
    if off + 2 > len(data):
        return None
    return struct.unpack_from("<H" if endian == "le" else ">H", data, off)[0]

for endian in ["le", "be"]:
    for stride in [2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64]:
        hits = []

        for start in range(0, len(data) - stride * 10):
            vals = [read_u16(start + i * stride, endian) for i in range(20)]

            score = sum(1 for v in vals if v in targets)

            if score >= 4:
                hits.append((score, start, vals))

        hits.sort(reverse=True)

        if hits:
            print("=" * 80)
            print("endian", endian, "stride", stride)

            for score, start, vals in hits[:20]:
                print(f"start=0x{start:06x} score={score} vals={vals}")
