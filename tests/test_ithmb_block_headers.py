from pathlib import Path
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

for path in sorted(CACHE.glob("F*/T*.ithmb")):
    data = path.read_bytes()
    hits = []

    for off in range(0, len(data) - 4, 4096):
        h = data[off:off+4]
        hits.append(h)

    if not hits:
        continue

    first = hits[0]
    unique = Counter(hits)

    print("=" * 100)
    print(path.relative_to(CACHE))
    print("size:", len(data))
    print("blocks:", len(hits))
    print("unique headers:", len(unique))
    print("first header:", first.hex(" "))
    print("last header:", hits[-1].hex(" "))

    # Affiche les 20 premiers headers
    for i, h in enumerate(hits[:20]):
        val_be = int.from_bytes(h, "big")
        val_le = int.from_bytes(h, "little")
        print(f"block={i:03d} off=0x{i*4096:08x} h={h.hex(' ')} be={val_be} le={val_le}")
