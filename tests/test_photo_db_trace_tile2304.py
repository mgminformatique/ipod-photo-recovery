from pathlib import Path
import struct

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
T149 = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

TILE = 2304

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def u16be(b, off):
    return struct.unpack_from(">H", b, off)[0]

def dump_context(data, off, radius=48):
    a = max(0, off - radius)
    z = min(len(data), off + radius)
    chunk = data[a:z]
    print(f"context 0x{a:08x}-0x{z:08x}")
    print(" ".join(f"{x:02x}" for x in chunk))

def main():
    db = DB.read_bytes()
    t149 = T149.read_bytes()

    print("=" * 100)
    print("PHOTO DB TRACE TILE 2304")
    print("=" * 100)
    print(f"DB size={len(db)} T149 size={len(t149)}")

    hits = []

    for off in range(0, len(db) - 2):
        le = u16le(db, off)
        be = u16be(db, off)

        if le == TILE:
            hits.append((off, "LE"))
        if be == TILE:
            hits.append((off, "BE"))

    print()
    print(f"tile {TILE} hits in Photo Database: {len(hits)}")

    for off, endian in hits:
        print()
        print("-" * 100)
        print(f"HIT off=0x{off:08x} endian={endian}")

        dump_context(db, off)

        print("nearby u16 LE:")
        for p in range(max(0, off - 32), min(len(db) - 2, off + 34), 2):
            print(f"  +{p-off:+04d} off=0x{p:08x} le={u16le(db,p):5d} 0x{u16le(db,p):04x}")

        print("nearby u16 BE:")
        for p in range(max(0, off - 32), min(len(db) - 2, off + 34), 2):
            print(f"  +{p-off:+04d} off=0x{p:08x} be={u16be(db,p):5d} 0x{u16be(db,p):04x}")

    print()
    print("=" * 100)
    print("T149 refs to tile 2304")
    print("=" * 100)

    for off in range(0, len(t149) - 2):
        if u16le(t149, off) == TILE:
            print(f"T149 LE off=0x{off:08x}")
        if u16be(t149, off) == TILE:
            print(f"T149 BE off=0x{off:08x}")

if __name__ == "__main__":
    main()
