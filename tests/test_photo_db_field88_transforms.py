from pathlib import Path
import struct
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
DB = CACHE / "Photo Database"
db = DB.read_bytes()

values = []

for p in sorted(CACHE.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(p).find_records()
    for r in records:
        if len(r.data) >= 92:
            v = struct.unpack_from("<I", r.data, 88)[0] & 0xffff
            values.append(v)

variants = {
    "original": values,
    "reversed": list(reversed(values)),
    "sorted": sorted(values),
    "sorted_reverse": sorted(values, reverse=True),
}

print("FIELD88 TRANSFORM SCAN")
print("DB size:", len(db))
print("values:", len(values))

def read_u16(off, endian):
    if off + 2 > len(db):
        return None
    return struct.unpack_from("<H" if endian == "LE" else ">H", db, off)[0]

for name, seq in variants.items():
    print("=" * 80)
    print(name)

    for endian in ["LE", "BE"]:
        for stride in [2,4,8,12,16,24,32,48,64,112,128]:
            best = []

            for start in range(0, len(db) - stride * 16):
                score = 0
                for i in range(32):
                    if i >= len(seq):
                        break
                    if read_u16(start + i * stride, endian) == seq[i]:
                        score += 1

                if score >= 4:
                    best.append((score, start))

            if best:
                best.sort(reverse=True)
                print(" endian", endian, "stride", stride)
                for score, start in best[:10]:
                    print(f"  start=0x{start:06x} score={score}")

print("done")
