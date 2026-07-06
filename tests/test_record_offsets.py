from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    CACHE/"F05"/"T154.ithmb",
    CACHE/"F06"/"T155.ithmb",
    CACHE/"F07"/"T156.ithmb",
    CACHE/"F23"/"T172.ithmb",
]

for path in FILES:

    print("="*80)
    print(path.relative_to(CACHE))

    recs = ITHMBRecordParser(path).find_records()

    for i,r in enumerate(recs):

        print(
            f"{i:02d}",
            f"record_off=0x{r.offset:08x}",
            f"payload_off=0x{r.payload_offset:08x}",
            f"payload={r.payload_size}"
        )
