from pathlib import Path
import struct
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGET_FILES = [
    CACHE / "F08" / "T157.ithmb",
    CACHE / "F46" / "T144.ithmb",
    CACHE / "F47" / "T145.ithmb",
    CACHE / "F48" / "T146.ithmb",
    CACHE / "F49" / "T147.ithmb",
    CACHE / "F50" / "T148.ithmb",
]

sizes = {p.name: p.stat().st_size for p in TARGET_FILES if p.exists()}

print("RECORD POINTER CANDIDATES")
print("target sizes:", sizes)
print()

for p in sorted(CACHE.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(p).find_records()
    if not records:
        continue

    print("=" * 100)
    print(p.relative_to(CACHE), "records", len(records))

    for idx, r in enumerate(records):
        d = r.data
        candidates = []

        for off in range(0, len(d) - 4):
            le = struct.unpack_from("<I", d, off)[0]
            be = struct.unpack_from(">I", d, off)[0]

            for name, size in sizes.items():
                if 0 <= le < size:
                    candidates.append((off, "LE", le, name))
                if 0 <= be < size:
                    candidates.append((off, "BE", be, name))

        print(f"record {idx:02d}: candidates={len(candidates)}")
        for off, endian, val, name in candidates[:20]:
            print(f"  field_off={off:03d} {endian} value=0x{val:06x} target={name}")
