from pathlib import Path
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

target = CACHE / "F12" / "T161.ithmb"

parser = ITHMBRecordParser(target)
records = parser.find_records()

print("records:", len(records))

raw = target.read_bytes()

base_start = records[0].record_start
base = raw[base_start:base_start + 112]

for i, r in enumerate(records[1:], 1):
    cur = raw[r.record_start:r.record_start + 112]

    changed = []

    for off in range(112):
        if base[off] != cur[off]:
            changed.append(off)

    print(f"record {i}:")
    print(changed)
