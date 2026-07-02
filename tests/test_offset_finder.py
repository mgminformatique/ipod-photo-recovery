from pathlib import Path
from PIL import Image

ITHMB = "/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb"

WIDTH = 120
HEIGHT = 120
BPP = 2

FRAME_SIZE = WIDTH * HEIGHT * BPP

OFFSETS = [
    0,
    16,
    32,
    48,
    64,
    80,
    88,
    96,
    112,
    128,
    160,
    192,
    224,
    256,
    280,
    320,
    376,
    512,
    608,
    632,
    776,
    928,
    1024,
]

outdir = Path("output/offset_test")
outdir.mkdir(parents=True, exist_ok=True)

data = Path(ITHMB).read_bytes()

for offset in OFFSETS:

    if len(data) <= offset + FRAME_SIZE:
        continue

    frame = data[offset:offset + FRAME_SIZE]

    img = Image.new("RGB", (WIDTH, HEIGHT))

    pixels = []

    for i in range(0, len(frame), 2):

        if i + 1 >= len(frame):
            break

        value = frame[i] | (frame[i + 1] << 8)

        r = ((value >> 11) & 0x1F) << 3
        g = ((value >> 5) & 0x3F) << 2
        b = (value & 0x1F) << 3

        pixels.append((r, g, b))

    img.putdata(pixels[:WIDTH * HEIGHT])

    img.save(outdir / f"offset_{offset}.png")

print("Done.")
print("Images:", outdir)
