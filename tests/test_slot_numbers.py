from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

for f in sorted(CACHE.rglob("*.ithmb")):

    parser = ITHMBRecordParser(f)
    records = parser.find_records()

    if not records:
        continue

    slots = [r.data[6] for r in records]

    print(f"{f.relative_to(CACHE)}")
    print(slots)
    print()
