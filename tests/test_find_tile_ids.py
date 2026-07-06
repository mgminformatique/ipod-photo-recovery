from pathlib import Path
import struct

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

# IDs qu'on vient de voir dans les records
TILE_IDS = list(range(2304, 2432))

FILES = sorted(CACHE.glob("F*/T*.ithmb"))
DB = CACHE / "Photo Database"

if DB.exists():
    FILES.append(DB)

print("=" * 100)
print("FIND TILE IDS")
print("=" * 100)
print("tile ids:", TILE_IDS[0], "to", TILE_IDS[-1])
print("files:", len(FILES))

for path in FILES:
    data = path.read_bytes()
    hits = []

    for tile_id in TILE_IDS:
        pats = [
            ("u16LE", struct.pack("<H", tile_id)),
            ("u16BE", struct.pack(">H", tile_id)),
            ("u32LE", struct.pack("<I", tile_id)),
            ("u32BE", struct.pack(">I", tile_id)),
        ]

        for kind, pat in pats:
            start = 0
            while True:
                pos = data.find(pat, start)
                if pos == -1:
                    break

                hits.append((pos, kind, tile_id))
                start = pos + 1

    if not hits:
        continue

    hits.sort()

    print("=" * 100)
    print(path.relative_to(CACHE) if path != DB else "Photo Database")
    print("hits:", len(hits))

    for pos, kind, tile_id in hits[:80]:
        print(f"0x{pos:08x} {kind} tile_id={tile_id}")

print("done")
