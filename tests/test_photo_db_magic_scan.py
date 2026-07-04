from pathlib import Path
import zlib, gzip, bz2, lzma

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

MAGICS = {
    b"\x78\x01": "zlib no compression",
    b"\x78\x9c": "zlib default",
    b"\x78\xda": "zlib best",
    b"\x1f\x8b": "gzip",
    b"BZh": "bzip2",
    b"\xfd7zXZ": "xz",
    b"bplist": "binary plist",
    b"SQLite": "sqlite",
    b"mh": "iTunes mh*",
}

print("=" * 80)
print("PHOTO DATABASE MAGIC / DECOMPRESS SCAN")
print("=" * 80)
print("size:", len(data))

for magic, name in MAGICS.items():
    hits = []
    start = 0
    while True:
        i = data.find(magic, start)
        if i == -1:
            break
        hits.append(i)
        start = i + 1
    if hits:
        print(name, magic.hex(), [hex(x) for x in hits[:20]])

print()
print("Try raw zlib from every offset...")
found = 0

for off in range(len(data)):
    chunk = data[off:]
    for wbits, label in [
        (15, "zlib"),
        (-15, "raw-deflate"),
        (31, "gzip"),
    ]:
        try:
            out = zlib.decompress(chunk, wbits)
            if len(out) >= 16:
                print(f"OK {label} offset=0x{off:x} out={len(out)} first={out[:32].hex(' ')}")
                found += 1
                Path("output").mkdir(exist_ok=True)
                Path(f"output/photo_db_decomp_{label}_{off:x}.bin").write_bytes(out)
        except Exception:
            pass

print("found:", found)
