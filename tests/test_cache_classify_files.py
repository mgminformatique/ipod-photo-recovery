from pathlib import Path
from collections import Counter
import math

from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

print("file,size,entropy,records,kind,notes")

for p in sorted(CACHE.glob("F*/T*.ithmb")):
    data = p.read_bytes()
    e = entropy(data[: min(len(data), 65536)])

    try:
        records = ITHMBRecordParser(p).find_records()
    except Exception:
        records = []

    notes = []

    if records:
        notes.append(f"slots={len(records)}")

    if data[:4] in [b"\x00\x00\x00\x00", b"\x00\x01\x18\x32"]:
        notes.append("structured-start")

    low_values = sum(1 for b in data[:65536] if b <= 5)
    high_entropy = e > 7.3
    many_low = low_values > 20000

    if records:
        kind = "record-indexed"
    elif high_entropy:
        kind = "high-entropy-data"
    elif many_low:
        kind = "low-value-table"
    else:
        kind = "unknown"

    rel = str(p.relative_to(CACHE))
    print(f"{rel},{len(data)},{e:.3f},{len(records)},{kind},{'|'.join(notes)}")
