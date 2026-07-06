from pathlib import Path
from PIL import Image, ImageOps
import math

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/tile_reassemble_formats")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    CACHE / "F06" / "T155.ithmb",
    CACHE / "F07" / "T156.ithmb",
    CACHE / "F23" / "T172.ithmb",
]

OFFSETS = [0, 4, 8, 16, 32, 64, 128, 0x1c0, 0x8c0, 0x3f0]
CANVAS = [(48,48), (64,64), (96,96), (128,128)]
TILES = [(4,4), (8,8), (16,16)]
ORDERS = ["row", "col", "reverse_row", "morton"]

MAX_PER_TARGET = 1000


def morton_positions(cols, rows):
    out = []
    for y in range(rows):
        for x in range(cols):
            z = 0
            for i in range(8):
                z |= ((x >> i) & 1) << (2*i)
                z |= ((y >> i) & 1) << (2*i+1)
            out.append((z, x, y))
    return [(x,y) for z,x,y in sorted(out)]


def positions(cols, rows, order):
    if order == "row":
        return [(x,y) for y in range(rows) for x in range(cols)]
    if order == "col":
        return [(x,y) for x in range(cols) for y in range(rows)]
    if order == "reverse_row":
        return list(reversed([(x,y) for y in range(rows) for x in range(cols)]))
    if order == "morton":
        return morton_positions(cols, rows)
    return []


def rgb565_pixels(buf, big=False, bgr=False):
    pix = []
    for i in range(0, len(buf)-1, 2):
        v = (buf[i] << 8) | buf[i+1] if big else buf[i] | (buf[i+1] << 8)
        r = ((v >> 11) & 31) << 3
        g = ((v >> 5) & 63) << 2
        b = (v & 31) << 3
        pix.append((b,g,r) if bgr else (r,g,b))
    return pix


def decode_tile(buf, tw, th, mode):
    n = tw * th

    if mode == "gray":
        if len(buf) < n:
            return None
        return [(v,v,v) for v in buf[:n]], n

    if mode in ["rgb565le", "rgb565be", "bgr565le", "bgr565be"]:
        need = n * 2
        if len(buf) < need:
            return None
        big = "be" in mode
        bgr = "bgr" in mode
        return rgb565_pixels(buf[:need], big, bgr), need

    if mode in ["rgb888", "bgr888"]:
        need = n * 3
        if len(buf) < need:
            return None
        pix = []
        for i in range(0, need, 3):
            a,b,c = buf[i], buf[i+1], buf[i+2]
            pix.append((a,b,c) if mode == "rgb888" else (c,b,a))
        return pix, need

    return None


def make_image(raw, W, H, tw, th, order, mode):
    cols = W // tw
    rows = H // th
    img = Image.new("RGB", (W,H))

    p = 0
    for tx, ty in positions(cols, rows, order):
        result = decode_tile(raw[p:], tw, th, mode)
        if not result:
            return None

        pix, used = result
        p += used

        for y in range(th):
            for x in range(tw):
                idx = y * tw + x
                if idx < len(pix):
                    img.putpixel((tx*tw+x, ty*th+y), pix[idx])

    return img


MODES = ["gray", "rgb565le", "rgb565be", "bgr565le", "bgr565be", "rgb888", "bgr888"]

total = 0

for target in TARGETS:
    raw_file = target.read_bytes()
    tag = f"{target.parent.name}_{target.stem}"
    made = 0

    print("Testing", target.relative_to(CACHE), len(raw_file))

    for off in OFFSETS:
        raw = raw_file[off:]

        for W,H in CANVAS:
            for tw,th in TILES:
                if W % tw or H % th:
                    continue

                for order in ORDERS:
                    for mode in MODES:
                        img = make_image(raw, W, H, tw, th, order, mode)
                        if img is None:
                            continue

                        name = f"{tag}_off{off:x}_{W}x{H}_tile{tw}x{th}_{order}_{mode}"
                        img.save(OUT / f"{name}.png")
                        ImageOps.autocontrast(img).save(OUT / f"{name}_auto.png")
                        made += 2
                        total += 2

                        if made >= MAX_PER_TARGET:
                            break
                    if made >= MAX_PER_TARGET:
                        break
                if made >= MAX_PER_TARGET:
                    break
            if made >= MAX_PER_TARGET:
                break
        if made >= MAX_PER_TARGET:
            break

    print("generated:", made)

print("TOTAL:", total)
print("OUT:", OUT)
