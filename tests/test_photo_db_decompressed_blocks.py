from pathlib import Path
from collections import Counter
import zlib
import math
import re

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
OUT = Path("output/photo_db_decompressed_blocks")
OUT.mkdir(parents=True, exist_ok=True)

data = DB.read_bytes()


def entropy(buf):
    if not buf:
        return 0
    c = Counter(buf)
    total = len(buf)
    return -sum((n / total) * math.log2(n / total) for n in c.values())


def ascii_strings(buf, min_len=4):
    return re.findall(rb"[\x20-\x7e]{%d,}" % min_len, buf)


found = []

for off in range(len(data)):
    try:
        out = zlib.decompress(data[off:], -15)  # raw deflate
    except Exception:
        continue

    if len(out) < 16:
        continue

    found.append((off, out))

print("=" * 100)
print("PHOTO DATABASE DECOMPRESSED BLOCKS")
print("=" * 100)
print("blocks:", len(found))
print()

for idx, (off, out) in enumerate(found):
    name = OUT / f"block_{idx:03d}_off_{off:06x}_len_{len(out)}.bin"
    name.write_bytes(out)

    e = entropy(out)
    strings = ascii_strings(out)

    print("=" * 100)
    print(f"block {idx:03d}")
    print(f"offset: 0x{off:06x}")
    print(f"length: {len(out)}")
    print(f"entropy: {e:.3f}")
    print(f"first32: {out[:32].hex(' ')}")

    if strings:
        print("strings:")
        for s in strings[:10]:
            print(" ", s.decode("latin1", errors="replace"))

print()
print("saved to:", OUT)
