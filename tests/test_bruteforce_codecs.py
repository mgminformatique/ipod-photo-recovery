from pathlib import Path
from PIL import Image, ImageOps
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
TARGET = CACHE / "F23" / "T172.ithmb"

OUT = Path("output/bruteforce_codecs")
OUT.mkdir(parents=True, exist_ok=True)

raw = TARGET.read_bytes()

SIZES = [
    (120, 120),
    (130, 88),
    (88, 130),
    (176, 220),
    (220, 176),
    (240, 320),
    (320, 240),
]

OFFSETS = [
    0, 8, 16, 24, 32, 64, 88, 112, 128, 256, 512, 1024,
    1696, 1808, 4698, 7674, 8472, 17522, 31126, 407591
]


def clamp(v):
    return max(0, min(255, int(v)))


def save_variants(img, name):
    variants = {
        "normal": img,
        "flip_h": ImageOps.mirror(img),
        "flip_v": ImageOps.flip(img),
        "rot90": img.rotate(90, expand=True),
        "rot180": img.rotate(180),
        "rot270": img.rotate(270, expand=True),
    }

    for suffix, im in variants.items():
        im.save(OUT / f"{name}_{suffix}.png")


def rgb565(data, w, h, order="rgb", endian="little"):
    pixels = []
    need = w * h * 2

    if len(data) < need:
        return None

    for i in range(0, need, 2):
        if endian == "little":
            v = data[i] | (data[i + 1] << 8)
        else:
            v = (data[i] << 8) | data[i + 1]

        r = ((v >> 11) & 0x1F) << 3
        g = ((v >> 5) & 0x3F) << 2
        b = (v & 0x1F) << 3

        d = {"r": r, "g": g, "b": b}
        pixels.append(tuple(d[c] for c in order))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def rgb555(data, w, h, order="rgb", endian="little"):
    pixels = []
    need = w * h * 2

    if len(data) < need:
        return None

    for i in range(0, need, 2):
        if endian == "little":
            v = data[i] | (data[i + 1] << 8)
        else:
            v = (data[i] << 8) | data[i + 1]

        r = ((v >> 10) & 0x1F) << 3
        g = ((v >> 5) & 0x1F) << 3
        b = (v & 0x1F) << 3

        d = {"r": r, "g": g, "b": b}
        pixels.append(tuple(d[c] for c in order))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def rgb888(data, w, h, order="rgb"):
    need = w * h * 3

    if len(data) < need:
        return None

    pixels = []
    for i in range(0, need, 3):
        vals = {
            "r": data[i],
            "g": data[i + 1],
            "b": data[i + 2],
        }
        pixels.append(tuple(vals[c] for c in order))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def gray8(data, w, h):
    need = w * h

    if len(data) < need:
        return None

    img = Image.frombytes("L", (w, h), data[:need])
    return img.convert("RGB")


def ycbcr422(data, w, h, layout):
    need = w * h * 2

    if len(data) < need:
        return None

    pixels = []

    for i in range(0, need, 4):
        a, b, c, d = data[i], data[i + 1], data[i + 2], data[i + 3]

        if layout == "y0_cb_y1_cr":
            y0, cb, y1, cr = a, b, c, d
        elif layout == "cb_y0_cr_y1":
            cb, y0, cr, y1 = a, b, c, d
        elif layout == "y0_cr_y1_cb":
            y0, cr, y1, cb = a, b, c, d
        elif layout == "cr_y0_cb_y1":
            cr, y0, cb, y1 = a, b, c, d
        else:
            return None

        for y in (y0, y1):
            r = y + 1.402 * (cr - 128)
            g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
            b2 = y + 1.772 * (cb - 128)
            pixels.append((clamp(r), clamp(g), clamp(b2)))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels[: w * h])
    return img


def tile_reorder_linear(data, w, h, tile_w, tile_h, bpp):
    pixels_per_tile = tile_w * tile_h
    tile_bytes = pixels_per_tile * bpp
    tiles_x = math.ceil(w / tile_w)
    tiles_y = math.ceil(h / tile_h)

    out = bytearray(w * h * bpp)
    src = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            for y in range(tile_h):
                for x in range(tile_w):
                    px = tx * tile_w + x
                    py = ty * tile_h + y

                    if px >= w or py >= h:
                        continue

                    dst = (py * w + px) * bpp

                    if src + bpp <= len(data) and dst + bpp <= len(out):
                        out[dst:dst + bpp] = data[src:src + bpp]

                    src += bpp

    return bytes(out)


count = 0

for offset in OFFSETS:
    chunk = raw[offset:]

    for w, h in SIZES:

        for endian in ["little", "big"]:
            for order in ["rgb", "bgr", "grb", "gbr", "rbg", "brg"]:
                img = rgb565(chunk, w, h, order=order, endian=endian)
                if img:
                    save_variants(img, f"off{offset}_rgb565_{w}x{h}_{order}_{endian}")
                    count += 6

                img = rgb555(chunk, w, h, order=order, endian=endian)
                if img:
                    save_variants(img, f"off{offset}_rgb555_{w}x{h}_{order}_{endian}")
                    count += 6

        for order in ["rgb", "bgr", "grb", "gbr", "rbg", "brg"]:
            img = rgb888(chunk, w, h, order=order)
            if img:
                save_variants(img, f"off{offset}_rgb888_{w}x{h}_{order}")
                count += 6

        img = gray8(chunk, w, h)
        if img:
            save_variants(img, f"off{offset}_gray8_{w}x{h}")
            count += 6

        for layout in [
            "y0_cb_y1_cr",
            "cb_y0_cr_y1",
            "y0_cr_y1_cb",
            "cr_y0_cb_y1",
        ]:
            img = ycbcr422(chunk, w, h, layout)
            if img:
                save_variants(img, f"off{offset}_ycbcr422_{w}x{h}_{layout}")
                count += 6

        for tile_w, tile_h in [(4, 4), (8, 8), (16, 16), (24, 24), (32, 32)]:
            tiled = tile_reorder_linear(chunk, w, h, tile_w, tile_h, 2)

            for endian in ["little", "big"]:
                for order in ["rgb", "bgr"]:
                    img = rgb565(tiled, w, h, order=order, endian=endian)
                    if img:
                        save_variants(
                            img,
                            f"off{offset}_tile{tile_w}x{tile_h}_rgb565_{w}x{h}_{order}_{endian}",
                        )
                        count += 6

print("Fichier testé:", TARGET)
print("Images générées:", count)
print("Sortie:", OUT)
