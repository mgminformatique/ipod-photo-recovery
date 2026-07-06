from pathlib import Path
import struct
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    CACHE/"F05"/"T154.ithmb",
    CACHE/"F06"/"T155.ithmb",
    CACHE/"F07"/"T156.ithmb",
    CACHE/"F09"/"T158.ithmb",
    CACHE/"F12"/"T161.ithmb",
    CACHE/"F23"/"T172.ithmb",
]

print("=" * 100)
print("RECORD FIELD PATTERNS")
print("=" * 100)

for path in FILES:
    records = ITHMBRecordParser(path).find_records()
    if not records:
        continue

    print("=" * 100)
    print(path.relative_to(CACHE), "records", len(records))

    # Analyse u16
    print("\nU16 fields:")
    for off in range(0, 112 - 2 + 1, 2):
        vals = []
        for r in records:
            if len(r.data) >= off + 2:
                vals.append(struct.unpack_from("<H", r.data, off)[0])

        if len(vals) != len(records):
            continue

        diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]

        if len(set(vals)) <= 3 or len(set(diffs)) <= 3:
            print(
                f"off={off:03d} "
                f"vals={vals[:16]} "
                f"diffs={diffs[:15]}"
            )

    # Analyse u32
    print("\nU32 fields:")
    for off in range(0, 112 - 4 + 1, 4):
        vals = []
        for r in records:
            if len(r.data) >= off + 4:
                vals.append(struct.unpack_from("<I", r.data, off)[0])

        if len(vals) != len(records):
            continue

        diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]

        if len(set(vals)) <= 3 or len(set(diffs)) <= 3:
            print(
                f"off={off:03d} "
                f"vals={vals[:16]} "
                f"diffs={diffs[:15]}"
            )

print("done")
