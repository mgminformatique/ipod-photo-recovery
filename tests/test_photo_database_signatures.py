from pathlib import Path

data = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database").read_bytes()

signatures = {
    "zlib_78_01": b"\x78\x01",
    "zlib_78_9c": b"\x78\x9c",
    "zlib_78_da": b"\x78\xda",
    "gzip": b"\x1f\x8b",
    "bzip2": b"BZh",
    "zip": b"PK\x03\x04",
    "sqlite": b"SQLite format 3",
    "plist_xml": b"<?xml",
    "bplist": b"bplist",
    "png": b"\x89PNG",
    "jpeg": b"\xff\xd8\xff",
}

print("Photo Database compression/signature scan")
print("Size:", len(data))
print()

total = 0

for name, sig in signatures.items():
    positions = []
    start = 0

    while True:
        pos = data.find(sig, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1

    if positions:
        total += len(positions)
        print(name, "hits:", len(positions), "first:", positions[:20])

print()
print("Total signature hits:", total)
