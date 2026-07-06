from pathlib import Path
from collections import Counter
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/high_entropy_regions")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    CACHE / "F08" / "T157.ithmb",
    CACHE / "F46" / "T144.ithmb",
    CACHE / "F47" / "T145.ithmb",
    CACHE / "F48" / "T146.ithmb",
    CACHE / "F49" / "T147.ithmb",
    CACHE / "F50" / "T148.ithmb",
]

def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

def find_regions(data):
    regions = []
    in_region = False
    start = None

    for off in range(0, len(data), 4096):
        chunk = data[off:off+4096]
        e = entropy(chunk)
        is_data = e > 7.5 and chunk.count(0) < 200

        if is_data and not in_region:
            start = off
            in_region = True

        if not is_data and in_region:
            regions.append((start, off))
            in_region = False

    if in_region:
        regions.append((start, len(data)))

    return regions

for path in TARGETS:
    data = path.read_bytes()
    tag = f"{path.parent.name}_{path.stem}"

    print("=" * 100)
    print(path.relative_to(CACHE), "size", len(data))

    regions = find_regions(data)

    for i, (start, end) in enumerate(regions):
        chunk = data[start:end]
        out = OUT / f"{tag}_region_{i:02d}_0x{start:06x}_0x{end-1:06x}.bin"
        out.write_bytes(chunk)

        print(
            f"region {i:02d} "
            f"0x{start:06x}-0x{end-1:06x} "
            f"size={len(chunk)} "
            f"entropy={entropy(chunk):.3f} "
            f"file={out.name}"
        )

print("Sortie:", OUT)
