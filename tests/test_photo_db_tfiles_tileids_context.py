from pathlib import Path
import struct

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")

TFILES = list(range(154, 166))
TILES = list(range(2304, 2432))

def u16le(b, o): return struct.unpack_from("<H", b, o)[0]
def u16be(b, o): return struct.unpack_from(">H", b, o)[0]
def u32le(b, o): return struct.unpack_from("<I", b, o)[0]
def u32be(b, o): return struct.unpack_from(">I", b, o)[0]

def dump(data, off, radius=32):
    a = max(0, off - radius)
    z = min(len(data), off + radius)
    print(f"  context 0x{a:08x}-0x{z:08x}:")
    print("  " + " ".join(f"{x:02x}" for x in data[a:z]))

def scan_values(data, values, label):
    print()
    print("=" * 100)
    print(label)
    print("=" * 100)

    hits = []

    for off in range(0, len(data) - 4):
        if off <= len(data) - 2:
            le16 = u16le(data, off)
            be16 = u16be(data, off)
            if le16 in values:
                hits.append((off, "u16LE", le16))
            if be16 in values:
                hits.append((off, "u16BE", be16))

        le32 = u32le(data, off)
        be32 = u32be(data, off)
        if le32 in values:
            hits.append((off, "u32LE", le32))
        if be32 in values:
            hits.append((off, "u32BE", be32))

    print(f"hits: {len(hits)}")

    for off, kind, val in hits[:200]:
        print()
        print(f"hit off=0x{off:08x} kind={kind} value={val}")
        dump(data, off)

    if len(hits) > 200:
        print(f"\n... truncated, total hits={len(hits)}")

def main():
    data = DB.read_bytes()

    print("=" * 100)
    print("PHOTO DB TFILES + TILEIDS CONTEXT")
    print("=" * 100)
    print(f"DB size: {len(data)}")

    scan_values(data, set(TFILES), "TFILE NUMBERS 154-165")
    scan_values(data, set(TILES), "TILE IDS 2304-2431")

if __name__ == "__main__":
    main()
