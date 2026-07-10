from pathlib import Path

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

data = SRC.read_bytes()

BLOCK = 0x1000

blocks = []

for off in range(0, len(data), BLOCK):
    b = data[off:off+BLOCK]
    if len(b) == BLOCK:
        blocks.append(b[4:])      # retire le header

print("blocks:", len(blocks))
print()

for i in range(min(20, len(blocks)-1)):
    a = blocks[i]
    b = blocks[i+1]

    same = sum(x == y for x, y in zip(a, b))

    print(
        f"{i:03d}->{i+1:03d} "
        f"{same}/{len(a)} "
        f"{same/len(a)*100:5.1f}%"
    )
