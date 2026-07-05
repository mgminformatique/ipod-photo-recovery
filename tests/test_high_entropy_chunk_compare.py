from pathlib import Path
from collections import Counter
import hashlib
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGETS = [
    CACHE / "F08" / "T157.ithmb",
    CACHE / "F46" / "T144.ithmb",
    CACHE / "F47" / "T145.ithmb",
    CACHE / "F48" / "T146.ithmb",
    CACHE / "F49" / "T147.ithmb",
    CACHE / "F50" / "T148.ithmb",
]

CHUNKS = [256, 512, 1024, 2048, 4096, 8192]

def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())

print("HIGH ENTROPY CHUNK COMPARE")

for chunk_size in CHUNKS:
    print("=" * 100)
    print("chunk_size:", chunk_size)

    all_hashes = {}

    for path in TARGETS:
        if not path.exists():
            continue

        data = path.read_bytes()
        rel = str(path.relative_to(CACHE))

        hashes = []
        entropies = []

        for off in range(0, len(data), chunk_size):
            chunk = data[off:off + chunk_size]
            if len(chunk) < chunk_size:
                continue

            h = hashlib.sha1(chunk).hexdigest()
            hashes.append(h)
            entropies.append(entropy(chunk))

            all_hashes.setdefault(h, []).append((rel, off))

        print(
            f"{rel:18} "
            f"chunks={len(hashes):5d} "
            f"avg_entropy={sum(entropies)/len(entropies):.3f} "
            f"first={data[:16].hex(' ')}"
        )

    repeated = {h: locs for h, locs in all_hashes.items() if len(locs) > 1}

    print("repeated chunks across files:", len(repeated))

    for h, locs in list(repeated.items())[:20]:
        print(" hash", h)
        for rel, off in locs[:10]:
            print(f"   {rel} off=0x{off:06x}")

print("done")
