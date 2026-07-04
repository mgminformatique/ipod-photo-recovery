from pathlib import Path
from PIL import Image, ImageDraw
from parser.ithmb_records import ITHMBRecordParser

cache = Path("/home/murph/Desktop/iPod Photo Cache")
out = Path("output/slots")
out.mkdir(parents=True, exist_ok=True)

WIDTH = 120
HEIGHT = 120
FRAME_SIZE = WIDTH * HEIGHT * 2


def rgb565_to_img(data):
    img = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = []

    for i in range(0, min(len(data), FRAME_SIZE), 2):
        if i + 1 >= len(data):
            break

        v = data[i] | (data[i + 1] << 8)

        r = ((v >> 11) & 0x1F) << 3
        g = ((v >> 5) & 0x3F) << 2
        b = (v & 0x1F) << 3

        pixels.append((r, g, b))

    pixels += [(0, 0, 0)] * ((WIDTH * HEIGHT) - len(pixels))
    img.putdata(pixels[:WIDTH * HEIGHT])
    return img


for ithmb in sorted(cache.glob("F*/T*.ithmb")):
    records = ITHMBRecordParser(ithmb).find_records()

    if not records:
        continue

    raw = ithmb.read_bytes()

    for idx, r in enumerate(records):
        slot = r.data[6]

        # Hypothèse actuelle:
        # record index = frame index
        frame_offset = idx * FRAME_SIZE
        frame = raw[frame_offset:frame_offset + FRAME_SIZE]

        img = rgb565_to_img(frame)

        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 70, 18), fill=(0, 0, 0))
        draw.text((3, 3), f"S{slot} R{idx}", fill=(255, 255, 255))

        name = f"slot_{slot:03d}_{ithmb.parent.name}_{ithmb.stem}_record_{idx:02d}.png"
        img.save(out / name)

print("Export terminé:", out)
