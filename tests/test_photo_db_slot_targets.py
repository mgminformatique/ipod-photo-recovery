from pathlib import Path
from collections import defaultdict
import struct

from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
DB = CACHE / "Photo Database"

db = DB.read_bytes()

# 1) Ramasser tous les field88 connus depuis les .ithmb
field88_values = set()
field88_low16 = set()
slots = set()

for ithmb in sorted(CACHE.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(ithmb).find_records()

    for r in records:
        f88 = r.fields()["field_88"]
        field88_values.add(f88)
        field88_low16.add(f88 & 0xFFFF)
        slots.add(r.data[6])

print("=" * 100)
print("PHOTO DATABASE SLOT TARGET SCAN")
print("=" * 100)
print("DB size:", len(db))
print("field88 count:", len(field88_values))
print("field88 low16 count:", len(field88_low16))
print("slots count:", len(slots))
print()

# 2) Chercher field88 complets en u32 little-endian / big-endian
print("Searching full field88 values as u32...")
hits32 = []

for off in range(0, len(db) - 4):
    le = struct.unpack_from("<I", db, off)[0]
    be = struct.unpack_from(">I", db, off)[0]

    if le in field88_values:
        hits32.append((off, "LE", le))

    if be in field88_values:
        hits32.append((off, "BE", be))

print("u32 hits:", len(hits32))
for h in hits32[:100]:
    print(f"offset=0x{h[0]:08x} endian={h[1]} value={h[2]}")

print()

# 3) Chercher les low16 de field88
print("Searching field88 low16 values as u16...")
hits16 = []

for off in range(0, len(db) - 2):
    le = struct.unpack_from("<H", db, off)[0]
    be = struct.unpack_from(">H", db, off)[0]

    if le in field88_low16:
        hits16.append((off, "LE", le))

    if be in field88_low16:
        hits16.append((off, "BE", be))

print("u16 hits:", len(hits16))
for h in hits16[:200]:
    print(f"offset=0x{h[0]:08x} endian={h[1]} value={h[2]}")

print()

# 4) Chercher zones riches en hits low16
print("Dense regions for low16 hits:")
bucket = defaultdict(int)

for off, endian, val in hits16:
    bucket[off // 256 * 256] += 1

for region, count in sorted(bucket.items(), key=lambda x: x[1], reverse=True)[:30]:
    print(f"region=0x{region:08x}-0x{region+255:08x} hits={count}")

print()

# 5) Chercher les offsets où value % 2304 == 0
print("Scanning values divisible by 2304...")
mod_hits = []

for off in range(0, len(db) - 2):
    v = struct.unpack_from("<H", db, off)[0]

    if v != 0 and v % 2304 == 0:
        mod_hits.append((off, v))

print("mod 2304 hits:", len(mod_hits))
for off, v in mod_hits[:200]:
    print(f"offset=0x{off:08x} value={v}")

print()

# 6) Chercher les bytes slot 0-127 en régions denses
print("Dense regions for bytes 0..127:")
slot_byte_regions = defaultdict(int)

for off, b in enumerate(db):
    if 0 <= b <= 127:
        slot_byte_regions[off // 256 * 256] += 1

for region, count in sorted(slot_byte_regions.items(), key=lambda x: x[1], reverse=True)[:30]:
    print(f"region=0x{region:08x}-0x{region+255:08x} count={count}")

print()
print("done")
