from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

SRC = Path(
    "output/t156_1k_objects/"
    "object_01_pages_0040-0091_count_52.bin"
)

OUT = Path("output/t156_individual_1k_pages")
OUT.mkdir(parents=True, exist_ok=True)

PAGE_DATA_SIZE = 1020

data = SRC.read_bytes()

if len(data) % PAGE_DATA_SIZE != 0:
    raise SystemExit(
        f"Bad object size: {len(data)} is not divisible by {PAGE_DATA_SIZE}"
    )

pages = [
    data[offset:offset + PAGE_DATA_SIZE]
    for offset in range(0, len(data), PAGE_DATA_SIZE)
]

print("=" * 100)
print("T156 INDIVIDUAL 1K PAGE RENDER")
print("=" * 100)
print(f"object bytes: {len(data)}")
print(f"pages: {len(pages)}")
print()

dimensions = [
    (34, 30),
    (30, 34),
]

for width, height in dimensions:
    folder = OUT / f"{width}x{height}"
    folder.mkdir(parents=True, exist_ok=True)

    contact = Image.new(
        "L",
        (13 * width, 4 * height),
        0,
    )

    for index, page in enumerate(pages):
        image = Image.frombytes("L", (width, height), page)
        image = ImageOps.autocontrast(image)

        image.save(folder / f"page_{index:02d}.png")

        x = (index % 13) * width
        y = (index // 13) * height
        contact.paste(image, (x, y))

    enlarged = contact.resize(
        (contact.width * 4, contact.height * 4),
        Image.Resampling.NEAREST,
    )

    draw = ImageDraw.Draw(enlarged)

    for column in range(1, 13):
        x = column * width * 4
        draw.line((x, 0, x, enlarged.height), fill=255)

    for row in range(1, 4):
        y = row * height * 4
        draw.line((0, y, enlarged.width, y), fill=255)

    contact_path = OUT / f"contact_sheet_{width}x{height}.png"
    enlarged.save(contact_path)

    print(f"saved: {contact_path}")

print()
print(f"saved individual pages in: {OUT}")
