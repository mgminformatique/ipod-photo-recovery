from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

for f in sorted(CACHE.rglob("*.ithmb")):
    parser = ITHMBRecordParser(f)
    records = parser.find_records()

    if not records:
        continue

    lows = []
    mids = []

    for r in records:
        v = r.fields()["field_88"]
        lows.append(v & 0xFF)
        mids.append((v >> 8) & 0xFFFF)

    print("=" * 80)
    print(f.relative_to(CACHE))
    print("records:", len(records))
    print("low8 unique:", sorted(set(lows)))
    print("mid min/max:", min(mids), max(mids))
    print("mid values:", mids)
