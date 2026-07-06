from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

KNOWN_TAGS = {
    b"mhfd", b"mhli", b"mhii", b"mhod", b"mhia",
    b"mhlf", b"mhif", b"mhba", b"mhsd", b"mhla",
    b"mhip", b"mhlp", b"mhpo"
}

def u32le(b, off):
    if off + 4 > len(b):
        return None
    return struct.unpack_from("<I", b, off)[0]

def ascii4(b):
    try:
        return b.decode("ascii")
    except Exception:
        return repr(b)

def main():
    data = DB.read_bytes()

    print("=" * 100)
    print("PARSE PHOTO DATABASE")
    print("=" * 100)
    print(f"database size: {len(data)} bytes")
    print()

    hits = []

    for off in range(0, len(data) - 8):
        tag = data[off:off+4]
        if tag in KNOWN_TAGS:
            size1 = u32le(data, off + 4)
            size2 = u32le(data, off + 8)

            hits.append((off, tag, size1, size2))

    print(f"known block tag hits: {len(hits)}")
    print()

    print("ALL KNOWN TAGS FOUND")
    print("-" * 100)

    for i, (off, tag, size1, size2) in enumerate(hits, 1):
        print(
            f"{i:04d} "
            f"off=0x{off:08x} "
            f"tag={ascii4(tag):4s} "
            f"size1={size1} "
            f"size2={size2}"
        )

    print()
    print("=" * 100)
    print("TAG COUNTS")
    print("=" * 100)

    counts = {}
    for _, tag, _, _ in hits:
        counts[tag] = counts.get(tag, 0) + 1

    for tag, count in sorted(counts.items(), key=lambda x: x[0]):
        print(f"{ascii4(tag)}: {count}")

    print()
    print("=" * 100)
    print("POSSIBLE BLOCK WALK")
    print("=" * 100)

    # Try to walk from first mhfd using size1 as header size and size2 as total size
    if hits:
        start = hits[0][0]
        print(f"first known block at 0x{start:08x}")

    for off, tag, size1, size2 in hits[:80]:
        print()
        print("-" * 100)
        print(f"block candidate at 0x{off:08x} tag={ascii4(tag)}")
        print(f"u32 @ +4  = {size1}")
        print(f"u32 @ +8  = {size2}")

        preview_start = off
        preview_end = min(len(data), off + 64)
        preview = data[preview_start:preview_end]

        print("hex preview:")
        print(" ".join(f"{x:02x}" for x in preview))

        print("ascii preview:")
        print("".join(chr(x) if 32 <= x <= 126 else "." for x in preview))


if __name__ == "__main__":
    main()
