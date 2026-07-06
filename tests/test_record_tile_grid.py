from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

for p in sorted(CACHE.glob("F??/T1*.ithmb")):

    recs = ITHMBRecordParser(p).find_records()

    if not recs:
        continue

    print("="*80)
    print(p.relative_to(CACHE))

    for i,r in enumerate(recs):

        raw = r.data

        print(
            i,
            raw[6:8].hex(),
            int.from_bytes(raw[6:8],"little")
        )
