from pathlib import Path
from PIL import Image, ImageOps

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
TARGETS = [
    CACHE / "F23" / "T172.ithmb",
    CACHE / "F12" / "T161.ithmb",
    CACHE / "F08" / "T157.ithmb",
]

OUT = Path("output/bruteforce_codecs")
OUT.mkdir(parents=True, exist_ok=True)

SIZES = [(120, 120), (130, 88), (176, 220), (220, 176)]
OFFSETS = [0, 88, 112, 224, 376, 608, 928, 1024]


def clamp(v):
    return max(0, min(255, int(v)))


def save(img, name):
    img.save(OUT / f"{name}.png")
    ImageOps.mirror(img).save(OUT / f"{name}_flipH.png")


def rgb565(data, w, h, bgr=False, big=False):
    need = w * h * 2
    if len(data) < need:
        return None

    pixels = []
    for i in range(0, need, 2):
        v = (data[i] << 8) | data[i + 1] if big else data[i] | (data[i + 1] << 8)
        r = ((v >> 11) & 31) << 3
        g = ((v >> 5) & 63) << 2
        b = (v & 31) << 3
        pixels.append((b, g, r) if bgr else (r, g, b))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def gray8(data, w, h):
    need = w * h
    if len(data) < need:
        return None
    return Image.frombytes("L", (w, h), data[:need]).convert("RGB")


def ycbcr422(data, w, h, mode):
    need = w * h * 2
    if len(data) < need:
        return None

    pixels = []
    for i in range(0, need - 3, 4):
        a, b, c, d = data[i], data[i + 1], data[i + 2], data[i + 3]

        if mode == "YUYV":
            y0, cb, y1, cr = a, b, c, d
        elif mode == "UYVY":
            cb, y0, cr, y1 = a, b, c, d
        elif mode == "YVYU":
            y0, cr, y1, cb = a, b, c, d
        else:
            cr, y0, cb, y1 = a, b, c, d

        for y in (y0, y1):
            r = y + 1.402 * (cr - 128)
            g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
            b2 = y + 1.772 * (cb - 128)
            pixels.append((clamp(r), clamp(g), clamp(b2)))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels[: w * h])
    return img


count = 0

for target in TARGETS:
    if not target.exists():
        continue

    raw = target.read_bytes()
    tag = f"{target.parent.name}_{target.stem}"

    for off in OFFSETS:
        chunk = raw[off:]

        for w, h in SIZES:
            for big in [False, True]:
                for bgr in [False, True]:
                    img = rgb565(chunk, w, h, bgr=bgr, big=big)
                    if img:
                        save(img, f"{tag}_off{off}_rgb565_{w}x{h}_{'BGR' if bgr else 'RGB'}_{'BE' if big else 'LE'}")
                        count += 2

            img = gray8(chunk, w, h)
            if img:
                save(img, f"{tag}_off{off}_gray8_{w}x{h}")
                count += 2

            for mode in ["YUYV", "UYVY", "YVYU", "VYUY"]:
                img = ycbcr422(chunk, w, h, mode)
                if img:
                    save(img, f"{tag}_off{off}_ycbcr422_{w}x{h}_{mode}")
                    count += 2

print("Images générées:", count)
print("Dossier:", OUT)
