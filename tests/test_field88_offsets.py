from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

cache = Path("/home/murph/Desktop/iPod Photo Cache")

for ithmb in sorted(cache.glob("F*/T1*.ithmb")):
    records = ITHMBRecordParser(ithmb).find_records()

    if not records:
        continue

    values = [r.fields()["field_88"] for r in records]
    base = min(values)

    print("=" * 80)
    print(ithmb.parent.name + "/" + ithmb.name)
    print("base =", base)

    for i, r in enumerate(records):
        field88 = r.fields()["field_88"]
        offset = field88 - base

        print(
            f"record {i:02d} "
            f"slot={r.data[6]:3d} "
            f"field88={field88} "
            f"offset={offset}"
        )
