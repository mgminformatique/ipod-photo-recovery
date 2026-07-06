from pathlib import Path
from PIL import Image, ImageOps
import itertools

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/bruteforce_formats")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    CACHE / "F06" / "T155.ithmb",
    CACHE / "F07" / "T156.ithmb",
    CACHE / "F23" / "T172.ithmb",
]

OFFSETS = [
    0, 4, 8, 16, 32, 64, 112, 128, 240, 512, 1024,
    0x1c0, 0x8c0, 0x3f0, 0x1000, 0x2000, 0x3000,
]

SIZES = [
    (48, 48),
    (64, 64),
    (96, 96),
    (120, 120),
    (128, 128),
    (160, 120),
    (176, 132),
    (176, 220),
    (220, 176),
    (240, 180),
    (320, 240),
]

MAX_IMAGES_PER_TARGET = 900


def clamp(v):
    return max(0, min(255, int(v)))


def save(img, name):
    img.save(OUT / f"{name}.png")
    ImageOps.autocontrast(img).save(OUT / f"{name}_auto.png")


def gray8(buf, w, h):
    need = w * h
    if len(buf) < need:
        return None
    return Image.frombytes("L", (w, h), buf[:need]).convert("RGB")


def rgb565(buf, w, h, big=False, bgr=False):
    need = w * h * 2
    if len(buf) < need:
        return None

    pixels = []
    for i in range(0, need, 2):
        v = (buf[i] << 8) | buf[i + 1] if big else buf[i] | (buf[i + 1] << 8)
        r = ((v >> 11) & 31) << 3
        g = ((v >> 5) & 63) << 2
        b = (v & 31) << 3
        pixels.append((b, g, r) if bgr else (r, g, b))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def rgb555(buf, w, h, big=False, bgr=False):
    need = w * h * 2
    if len(buf) < need:
        return None

    pixels = []
    for i in range(0, need, 2):
        v = (buf[i] << 8) | buf[i + 1] if big else buf[i] | (buf[i + 1] << 8)
        r = ((v >> 10) & 31) << 3
        g = ((v >> 5) & 31) << 3
        b = (v & 31) << 3
        pixels.append((b, g, r) if bgr else (r, g, b))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def rgb4444(buf, w, h, big=False, order="rgba"):
    need = w * h * 2
    if len(buf) < need:
        return None

    pixels = []
    for i in range(0, need, 2):
        v = (buf[i] << 8) | buf[i + 1] if big else buf[i] | (buf[i + 1] << 8)
        n = {
            "a": ((v >> 12) & 15) * 17,
            "r": ((v >> 8) & 15) * 17,
            "g": ((v >> 4) & 15) * 17,
            "b": (v & 15) * 17,
        }
        pixels.append((n[order[0]], n[order[1]], n[order[2]]))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def rgb888(buf, w, h, order="rgb"):
    need = w * h * 3
    if len(buf) < need:
        return None

    pixels = []
    for i in range(0, need, 3):
        vals = {"r": buf[i], "g": buf[i + 1], "b": buf[i + 2]}
        pixels.append((vals[order[0]], vals[order[1]], vals[order[2]]))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def rgba8888(buf, w, h, order="rgba"):
    need = w * h * 4
    if len(buf) < need:
        return None

    pixels = []
    for i in range(0, need, 4):
        vals = {"r": buf[i], "g": buf[i + 1], "b": buf[i + 2], "a": buf[i + 3]}
        pixels.append((vals[order[0]], vals[order[1]], vals[order[2]]))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return img


def yuv422(buf, w, h, layout):
    need = w * h * 2
    if len(buf) < need:
        return None

    pixels = []

    for i in range(0, need - 3, 4):
        a, b, c, d = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]

        if layout == "YUYV":
            y0, u, y1, v = a, b, c, d
        elif layout == "UYVY":
            u, y0, v, y1 = a, b, c, d
        elif layout == "YVYU":
            y0, v, y1, u = a, b, c, d
        else:
            v, y0, u, y1 = a, b, c, d

        for y in (y0, y1):
            r = y + 1.402 * (v - 128)
            g = y - 0.344136 * (u - 128) - 0.714136 * (v - 128)
            b2 = y + 1.772 * (u - 128)
            pixels.append((clamp(r), clamp(g), clamp(b2)))

    img = Image.new("RGB", (w, h))
    img.putdata(pixels[: w * h])
    return img


total = 0

for target in TARGETS:
    if not target.exists():
        print("missing:", target)
        continue

    raw = target.read_bytes()
    tag = f"{target.parent.name}_{target.stem}"
    made = 0

    print("Testing", target.relative_to(CACHE), "size", len(raw))

    for off in OFFSETS:
        buf = raw[off:]

        for w, h in SIZES:
            tests = []

            tests.append(("gray8", gray8(buf, w, h)))

            for big in [False, True]:
                for bgr in [False, True]:
                    tests.append((f"rgb565_{'BE' if big else 'LE'}_{'BGR' if bgr else 'RGB'}", rgb565(buf, w, h, big, bgr)))
                    tests.append((f"rgb555_{'BE' if big else 'LE'}_{'BGR' if bgr else 'RGB'}", rgb555(buf, w, h, big, bgr)))

                for order in ["rgba", "bgra", "argb", "abgr"]:
                    tests.append((f"rgb4444_{'BE' if big else 'LE'}_{order}", rgb4444(buf, w, h, big, order)))

            for order in ["rgb", "bgr", "gbr", "grb", "rbg", "brg"]:
                tests.append((f"rgb888_{order}", rgb888(buf, w, h, order)))

            for order in ["rgba", "bgra", "argb", "abgr"]:
                tests.append((f"rgba8888_{order}", rgba8888(buf, w, h, order)))

            for layout in ["YUYV", "UYVY", "YVYU", "VYUY"]:
                tests.append((f"yuv422_{layout}", yuv422(buf, w, h, layout)))

            for name, img in tests:
                if img is None:
                    continue

                out_name = f"{tag}_off{off:x}_{w}x{h}_{name}"
                save(img, out_name)
                made += 2
                total += 2

                if made >= MAX_IMAGES_PER_TARGET:
                    break

            if made >= MAX_IMAGES_PER_TARGET:
                break

        if made >= MAX_IMAGES_PER_TARGET:
            break

    print("generated for target:", made)

print("TOTAL images:", total)
print("OUT:", OUT)
