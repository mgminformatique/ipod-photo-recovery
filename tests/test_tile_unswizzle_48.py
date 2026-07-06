from pathlib import Path
from PIL import Image, ImageOps
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/tile_unswizzle_48")
OUT.mkdir(parents=True, exist_ok=True)

TARGET = CACHE / "F05" / "T154.ithmb"
START = 0x04A8
REC_SIZE = 4608

TILE_SIZES = [(4,4), (8,8), (16,16), (8,16), (16,8)]
MODES = ["gray", "rgb565_le", "rgb565_be"]


def morton_order(n):
    coords = []
    size = int(math.sqrt(n))
    for y in range(size):
        for x in range(size):
            z = 0
            for i in range(8):
                z |= ((x >> i) & 1) << (2*i)
                z |= ((y >> i) & 1) << (2*i + 1)
            coords.append((z, x, y))
    return [(x, y) for z, x, y in sorted(coords)]


def decode_rgb565(buf, big=False):
    pixels = []
    for i in range(0, min(len(buf), 4608), 2):
        v = (buf[i] << 8) | buf[i+1] if big else buf[i] | (buf[i+1] << 8)
        r = ((v >> 11) & 31) << 3
        g = ((v >> 5) & 63) << 2
        b = (v & 31) << 3
        pixels.append((r, g, b))
    return pixels


def make_image_from_tiles(buf, mode, tw, th, order):
    W = H = 48
    img = Image.new("RGB", (W, H))

    if mode == "gray":
        unit = tw * th
        blank = [0] * unit
    else:
        unit = tw * th * 2
        blank = bytes(unit)

    tiles_x = W // tw
    tiles_y = H // th
    tile_positions = [(x, y) for y in range(tiles_y) for x in range(tiles_x)]

    if order == "reverse":
        tile_positions = list(reversed(tile_positions))
    elif order == "morton" and tiles_x == tiles_y:
        tile_positions = morton_order(tiles_x * tiles_y)

    p = 0
    for tx, ty in tile_positions:
        tile = buf[p:p+unit]
        p += unit

        if len(tile) < unit:
            continue

        if mode == "gray":
            vals = list(tile)
            for y in range(th):
                for x in range(tw):
                    v = vals[y * tw + x]
                    img.putpixel((tx*tw+x, ty*th+y), (v, v, v))
        else:
            pixels = decode_rgb565(tile, big=(mode == "rgb565_be"))
            for y in range(th):
                for x in range(tw):
                    idx = y * tw + x
                    if idx < len(pixels):
                        img.putpixel((tx*tw+x, ty*th+y), pixels[idx])

    return img


raw = TARGET.read_bytes()

for rec_idx in range(0, 80):
    rec = raw[START + rec_idx * 2304 : START + rec_idx * 2304 + REC_SIZE]
    if len(rec) < 2304:
        break

    for mode in MODES:
        for tw, th in TILE_SIZES:
            for order in ["linear", "reverse", "morton"]:
                if order == "morton" and (48 // tw) != (48 // th):
                    continue

                img = make_image_from_tiles(rec, mode, tw, th, order)
                name = f"rec{rec_idx:03d}_{mode}_tile{tw}x{th}_{order}"
                img.save(OUT / f"{name}.png")
                ImageOps.autocontrast(img).save(OUT / f"{name}_auto.png")

print("Sortie:", OUT)
