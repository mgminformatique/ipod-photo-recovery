from pathlib import Path
from collections import defaultdict, Counter
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

by_file = defaultdict(list)

for f in sorted(CACHE.rglob("*.ithmb")):
    parser = ITHMBRecordParser(f)
    for r in parser.find_records():
        fields = r.fields()
        by_file[f.relative_to(CACHE)].append(fields["field_88"])

for file, values in by_file.items():
    deltas = [abs(a - b) for a, b in zip(values, values[1:])]
    print("=" * 80)
    print(file)
    print("records:", len(values))
    print("field_88 min:", min(values), "max:", max(values))
    print("deltas:", Counter(deltas).most_common(10))
