from pathlib import Path
import zlib

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGETS = [
    CACHE / "F08" / "T157.ithmb",
    CACHE / "F46" / "T144.ithmb",
    CACHE / "F47" / "T145.ithmb",
    CACHE / "F48" / "T146.ithmb",
    CACHE / "F49" / "T147.ithmb",
    CACHE / "F50" / "T148.ithmb",
]

MAGICS = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"JFIF": "JFIF",
    b"Exif": "EXIF",
    b"\x78\x01": "zlib_7801",
    b"\x78\x9c": "zlib_789c",
    b"\x78\xda": "zlib_78da",
    b"\x1f\x8b": "gzip",
}

for path in TARGETS:
    if not path.exists():
        continue

    data = path.read_bytes()

    print("=" * 100)
    print(path.relative_to(CACHE), "size", len(data))

    for magic, name in MAGICS.items():
        hits = []
        start = 0

        while True:
            pos = data.find(magic, start)
            if pos == -1:
                break
            hits.append(pos)
            start = pos + 1

        if hits:
            print(name, [hex(x) for x in hits[:20]])

    print("try zlib signatures:")
    for sig in [b"\x78\x01", b"\x78\x9c", b"\x78\xda"]:
        start = 0
        while True:
            pos = data.find(sig, start)
            if pos == -1:
                break

            try:
                out = zlib.decompress(data[pos:])
                print(f"  zlib OK at 0x{pos:x} len={len(out)} first={out[:32].hex(' ')}")
            except Exception:
                pass

            start = pos + 1

print("done")
