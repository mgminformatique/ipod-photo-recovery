from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

print("file,record_start,field_88,field_92,field_96,field_100,field_104,field_108")

for f in sorted(CACHE.rglob("*.ithmb")):
    parser = ITHMBRecordParser(f)
    records = parser.find_records()

    for r in records:
        fields = r.fields()
        print(
            f"{f.relative_to(CACHE)},"
            f"{fields['record_start']},"
            f"{fields['field_88']},"
            f"{fields['field_92']},"
            f"{fields['field_96']},"
            f"{fields['field_100']},"
            f"{fields['field_104']},"
            f"{fields['field_108']}"
        )
