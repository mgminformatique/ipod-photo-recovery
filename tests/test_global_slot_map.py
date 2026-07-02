from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

cache = Path("/home/murph/Desktop/iPod Photo Cache")

print("=" * 100)
print("GLOBAL SLOT MAP")
print("=" * 100)

mapping = {}

for ithmb in sorted(cache.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(ithmb).find_records()

    for r in records:
        slot = r.data[6]

        mapping[slot] = {
            "file": ithmb.relative_to(cache),
            "field_88": r.fields()["field_88"],
        }

for slot in sorted(mapping):
    print(
        f"slot {slot:3d} -> "
        f"{mapping[slot]['file']} -> "
        f"field_88={mapping[slot]['field_88']}"
    )
