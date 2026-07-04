from pathlib import Path
from collections import Counter

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

print("PHOTO DATABASE BLOCK/CRYPTO SCAN")
print("size:", len(data))
print()

for block in [8, 16, 32, 64]:
    chunks = [data[i:i+block] for i in range(0, len(data)-block+1, block)]
    counts = Counter(chunks)
    repeated = [(c, b) for b, c in counts.items() if c > 1]

    print("=" * 80)
    print("block size:", block)
    print("chunks:", len(chunks))
    print("repeated chunks:", len(repeated))

    if repeated:
        for c, b in sorted(repeated, reverse=True)[:10]:
            print(c, b.hex(" "))

print()
print("First/last block XOR patterns:")
for block in [8, 16, 32]:
    first = data[:block]
    last = data[-block:]
    x = bytes(a ^ b for a, b in zip(first, last))
    print(f"block={block} xor={x.hex(' ')}")
