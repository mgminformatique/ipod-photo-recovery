from pathlib import Path
import re
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

print("file,t_number,records,low8_unique,mid_min,mid_max")

for f in sorted(CACHE.rglob("*.ithmb")):
    m = re.search(r"T(\d+)\.ithmb$", f.name)
    if not m:
        continue

    tnum = int(m.group(1))

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

    print(
        f"{f.relative_to(CACHE)},"
        f"{tnum},"
        f"{len(records)},"
        f"{sorted(set(lows))},"
        f"{min(mids)},"
        f"{max(mids)}"
    )
