from pathlib import Path
import struct

root = Path("/home/murph/Desktop/iPod Photo Cache")

values = [
    0x28de0c,
    0x28d50c,
    0x28cc0c,
    0x28ba0c,
    0x28a80c,
    0x289f0c,
    0x28960c,
    0x288d0c,
]

for f in sorted(root.rglob("*")):
    if not f.is_file():
        continue

    data = f.read_bytes()
    hits = []

    for v in values:
        le = struct.pack("<I", v)
        be = struct.pack(">I", v)

        if le in data:
            hits.append(f"{hex(v)} LE")
        if be in data:
            hits.append(f"{hex(v)} BE")

    if hits:
        print(f.relative_to(root), hits)
