from pathlib import Path
import struct
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
DB = CACHE / "Photo Database"
db = DB.read_bytes()

# Récupère les séquences low16 dans le même ordre que les records .ithmb
sequences = []

for p in sorted(CACHE.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(p).find_records()
    if not records:
        continue

    vals = []
    for r in records:
        if len(r.data) >= 92:
            v = struct.unpack_from("<I", r.data, 88)[0]
            vals.append(v & 0xffff)

    if vals:
        sequences.append((str(p.relative_to(CACHE)), vals))

print("=" * 100)
print("ORDERED FIELD88 LOW16 SEQUENCE SCAN")
print("=" * 100)
print("DB size:", len(db))
print("sequences:", len(sequences))
print()

def read_u16(off, endian):
    if off + 2 > len(db):
        return None
    return struct.unpack_from("<H" if endian == "LE" else ">H", db, off)[0]

for name, seq in sequences:
    print("=" * 100)
    print(name)
    print("seq len:", len(seq))
    print("seq first:", seq[:10])

    found_any = False

    for endian in ["LE", "BE"]:
        for stride in [2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 112, 128]:
            matches = []

            for start in range(0, len(db) - stride * min(len(seq), 8)):
                score = 0
                checked = min(len(seq), 16)

                for i in range(checked):
                    if read_u16(start + i * stride, endian) == seq[i]:
                        score += 1

                if score >= 4:
                    matches.append((score, start))

            if matches:
                found_any = True
                matches.sort(reverse=True)
                print(f"  endian={endian} stride={stride}")
                for score, start in matches[:10]:
                    vals = [read_u16(start + i * stride, endian) for i in range(min(len(seq), 10))]
                    print(f"    start=0x{start:06x} score={score} vals={vals}")

    if not found_any:
        print("  no ordered match")

print()
print("done")
