from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

for f in sorted(CACHE.rglob("*.ithmb")):

    parser = ITHMBRecordParser(f)
    records = parser.find_records()

    if not records:
        continue

    print("=" * 90)
    print(f.relative_to(CACHE))

    for r in records:

        value = r.fields()["field_88"]

        print(
            f"{value:10d}  "
            f"0x{value:08X}  "
            f"low8={value & 0xFF:3d}  "
            f"low12={value & 0xFFF:4d}  "
            f"low16={value & 0xFFFF:5d}  "
            f"high16={value >> 16:5d}"
        )
