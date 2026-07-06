from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

def u16le(b, off):
    if off + 2 > len(b):
        return None
    return struct.unpack_from("<H", b, off)[0]

def u32le(b, off):
    if off + 4 > len(b):
        return None
    return struct.unpack_from("<I", b, off)[0]

def main():
    data = DB.read_bytes()

    print("=" * 80)
    print("BLOCK MATH TRANSFORM FAST")
    print("=" * 80)
    print(f"database size: {len(data)} bytes")

    tile_min = 2304
    tile_max = 2431

    hits = []

    for off in range(0, len(data) - 4):
        v16 = u16le(data, off)
        v32 = u32le(data, off)

        if v16 is not None and tile_min <= v16 <= tile_max:
            hits.append((off, "u16LE", v16))

        if v32 is not None and tile_min <= v32 <= tile_max:
            hits.append((off, "u32LE", v32))

    print(f"tile id hits in Photo Database: {len(hits)}")
    print()

    if not hits:
        print("NO TILE IDS FOUND DIRECTLY IN PHOTO DATABASE")
        print("So the database may use transformed values, offsets, indexes, or block math.")
        return

    print("first 120 hits only:")
    print("-" * 80)

    for off, kind, val in hits[:120]:
        block_20 = off // 20
        mod_20 = off % 20

        block_40 = off // 40
        mod_40 = off % 40

        block_64 = off // 64
        mod_64 = off % 64

        block_128 = off // 128
        mod_128 = off % 128

        print(
            f"0x{off:08x} {kind}={val} | "
            f"/20={block_20} mod20={mod_20} | "
            f"/40={block_40} mod40={mod_40} | "
            f"/64={block_64} mod64={mod_64} | "
            f"/128={block_128} mod128={mod_128}"
        )

    print()
    print("unique tile ids found:")
    found = sorted(set(v for _, _, v in hits))
    print(found)
    print()
    print(f"count unique: {len(found)}")


if __name__ == "__main__":
    main()
