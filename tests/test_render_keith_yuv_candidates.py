from pathlib import Path
from PIL import Image
import math

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/keith_yuv_candidates")
OUT.mkdir(parents=True, exist_ok=True)

def clamp(x):
    return max(0, min(255, int(x)))

def yuv_to_rgb(y, u, v):
    y = (y / 255.0 - 0.5) * 2.0
    u = (u / 255.0 - 0.5) * 2.0
    v = (v / 255.0 - 0.5) * 2.0

    r = (y + 1.140 * v) / 2.0 + 0.5
    g = (y - 0.394 * u - 0.581 * v) / 2.0 + 0.5
    b = (y + 2.028 * u) / 2.0 + 0.5

    return clamp(r * 255), clamp(g * 255), clamp(b * 255)

def render_file(path, w, h, max_images=3):
    data = path.read_bytes()
    image_bytes = w * h * 2
    count = min(max_images, len(data) // image_bytes)

    for img_i in range(count):
        buf = data[img_i * image_bytes:(img_i + 1) * image_bytes]
        img = Image.new("RGB", (w, h))
        px = img.load()

        image_pixels = w * h
        row_bytes = w * 2

        for y in range(h):
            for x in range(w):
                base_y = y // 2
                pair_x = (x // 2) * 4

                if y % 2 == 0:
                    off = base_y * row_bytes + pair_x
                else:
                    off = image_pixels + (base_y * row_bytes + pair_x)

                if off + 3 >= len(buf):
                    continue

                even_c = buf[off]
                even_l = buf[off + 1]
                odd_c = buf[off + 2]
                odd_l = buf[off + 3]

                c = even_c
                lum = even_l if x % 2 == 0 else odd_l

                u = (c >> 4) * 17
                v = (c & 0x0F) * 17

                px[x, y] = yuv_to_rgb(lum, u, v)

        out = OUT / f"{path.parent.name}_{path.name}_{w}x{h}_{img_i}.png"
        img.save(out)
        print(f"saved {out}")

def main():
    candidates = [
        (720, 480),
        (220, 176),
        (176, 132),
        (130, 88),
        (42, 30),
    ]

    files = sorted(ROOT.rglob("*.ithmb"))

    for path in files:
        size = path.stat().st_size
        print("=" * 100)
        print(path.relative_to(ROOT), "size", size)

        for w, h in candidates:
            image_bytes = w * h * 2
            if size >= image_bytes and size % image_bytes == 0:
                print(f"candidate {w}x{h} images={size // image_bytes}")
                render_file(path, w, h)

if __name__ == "__main__":
    main()
