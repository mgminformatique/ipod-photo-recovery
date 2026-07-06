from pathlib import Path
import struct

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
DB = CACHE / "Photo Database"
data = DB.read_bytes()

targets = []

# Numéros Txxx et tailles de fichiers
for p in sorted(CACHE.glob("F*/T*.ithmb")):
    tnum = int(p.stem[1:])
    size = p.stat().st_size
    folder = int(p.parent.name[1:])

    targets.append((f"{p.parent.name}/{p.name} tnum", tnum))
    targets.append((f"{p.parent.name}/{p.name} size", size))
    targets.append((f"{p.parent.name}/{p.name} folder", folder))

print("=" * 100)
print("PHOTO DATABASE CROSS REFERENCES")
print("=" * 100)
print("DB size:", len(data))
print("targets:", len(targets))
print()

def find_u16(value):
    hits = []
    le = struct.pack("<H", value & 0xffff)
    be = struct.pack(">H", value & 0xffff)

    for off in range(len(data)-1):
        b = data[off:off+2]
        if b == le:
            hits.append((off, "u16LE"))
        if b == be:
            hits.append((off, "u16BE"))
    return hits

def find_u32(value):
    hits = []
    le = struct.pack("<I", value & 0xffffffff)
    be = struct.pack(">I", value & 0xffffffff)

    for off in range(len(data)-3):
        b = data[off:off+4]
        if b == le:
            hits.append((off, "u32LE"))
        if b == be:
            hits.append((off, "u32BE"))
    return hits

for name, value in targets:
    hits16 = find_u16(value)
    hits32 = find_u32(value)

    if hits16 or hits32:
        print("=" * 100)
        print(name, "value", value)

        for off, typ in hits16[:20]:
            print(f"  {typ} at 0x{off:06x}")

        for off, typ in hits32[:20]:
            print(f"  {typ} at 0x{off:06x}")

print()
print("done")
