from pathlib import Path
import struct

from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
DB = CACHE / "Photo Database"
db = DB.read_bytes()

print("=" * 100)
print("PHOTO DATABASE FIELD88 SEQUENCE SCAN")
print("=" * 100)
print("DB size:", len(db))

field88_values = []

for p in sorted(CACHE.glob("F*/T*.ithmb")):

    try:
        parser = ITHMBRecordParser(p)
        records = parser.find_records()
    except Exception:
        continue

    for r in records:

        if not hasattr(r, "data"):
            continue

        if len(r.data) < 92:
            continue

        value = struct.unpack_from("<I", r.data, 88)[0]

        field88_values.append(value)

print("field88 values:", len(field88_values))
print()

print("Searching exact u32 values...")

hits = []

for value in field88_values:

    for endian, pattern in [
        ("LE", struct.pack("<I", value)),
        ("BE", struct.pack(">I", value)),
    ]:

        start = 0

        while True:

            pos = db.find(pattern, start)

            if pos == -1:
                break

            hits.append((pos, endian, value))

            start = pos + 1

print("u32 hits:", len(hits))

for pos, endian, value in hits[:100]:
    print(
        f"offset=0x{pos:06x} "
        f"{endian} "
        f"value={value} "
        f"hex=0x{value:08x}"
    )

print()

print("Searching low16 values...")

hits16 = []

for value in field88_values:

    low = value & 0xffff

    for endian, pattern in [
        ("LE", struct.pack("<H", low)),
        ("BE", struct.pack(">H", low)),
    ]:

        start = 0

        while True:

            pos = db.find(pattern, start)

            if pos == -1:
                break

            hits16.append((pos, endian, low))

            start = pos + 1

print("low16 hits:", len(hits16))

regions = {}

for pos, endian, low in hits16:

    region = (pos // 256) * 256

    regions.setdefault(region, 0)

    regions[region] += 1

print()

print("Top dense regions:")

for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True)[:40]:

    print(
        f"0x{region:06x}-0x{region+255:06x} "
        f"hits={count}"
    )

print()
print("done")
