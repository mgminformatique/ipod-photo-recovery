from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

cache = Path("/home/murph/Desktop/iPod Photo Cache")

for ithmb in sorted(cache.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(ithmb).find_records()

    if not records:
        continue

    print("=" * 80)
    print(ithmb.relative_to(cache))

    for i, r in enumerate(records):
        slot = r.data[6]
        print(
            f"record={i:2d} "
            f"slot={slot:3d} "
            f"field88={r.fields()['field_88']}"
        )
