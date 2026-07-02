from pathlib import Path
from PIL import Image

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F08/T157.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F10/T108.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F11/T109.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F26/T124.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F30/T128.ithmb",
]

SIZES = [
    (120, 120),
    (130, 88),
    (176, 220),
    (220, 176),
    (320, 240),
]

OFFSETS = [0, 88, 224, 376, 608, 928, 1024]

MODES = ["RGB", "BGR"]

out = Path("output/batch_gray_preview")
out.mkdir(parents=True, exist_ok=True)


def decode_rgb888(data, width, height, offset, mode):
    need = width * height * 3
    chunk = data[offset:offset + need]

    if len(chunk) < need:
        return None

    pixels = []

    for i in range(0, need, 3):
        a, b, c = chunk[i], chunk[i + 1], chunk[i + 2]

        if mode == "RGB":
            pixels.append((a, b, c))
        else:
            pixels.append((c, b, a))

    img = Image.new("RGB", (width, height))
    img.putdata(pixels)
    return img


for path in FILES:
    p = Path(path)
    data = p.read_bytes()

    for width, height in SIZES:
        for offset in OFFSETS:
            for mode in MODES:
                img = decode_rgb888(data, width, height, offset, mode)

                if img is None:
                    continue

                name = f"{p.parent.name}_{p.stem}_{width}x{height}_off{offset}_{mode}.png"
                img.save(out / name)

print("Fait:", out)
