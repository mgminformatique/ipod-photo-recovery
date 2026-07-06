from pathlib import Path
from PIL import Image, ImageOps

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/records_48x48")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    (CACHE / "F05" / "T154.ithmb", 0x04a8),
    (CACHE / "F06" / "T155.ithmb", 0x08c0),
    (CACHE / "F23" / "T172.ithmb", 0x03f0),
]

def save_gray(buf, name):
    data = buf[:2304]
    img = Image.frombytes("L", (48, 48), data)
    img.save(OUT / f"{name}_gray.png")
    ImageOps.autocontrast(img).save(OUT / f"{name}_gray_auto.png")

def save_rgb565(buf, name, big=False, bgr=False):
    data = buf[:4608]
    if len(data) < 4608:
        return

    pixels = []
    for i in range(0, 4608, 2):
        v = (data[i] << 8) | data[i+1] if big else data[i] | (data[i+1] << 8)
        r = ((v >> 11) & 31) << 3
        g = ((v >> 5) & 63) << 2
        b = (v & 31) << 3
        pixels.append((b,g,r) if bgr else (r,g,b))

    img = Image.new("RGB", (48,48))
    img.putdata(pixels)
    img.save(OUT / f"{name}_{'BE' if big else 'LE'}_{'BGR' if bgr else 'RGB'}.png")

for path, start in TARGETS:
    raw = path.read_bytes()
    tag = f"{path.parent.name}_{path.stem}"

    print(path.relative_to(CACHE), "start", hex(start), "size", len(raw))

    for idx in range(80):
        off = start + idx * 2304
        rec = raw[off:off+4608]
        if len(rec) < 2304:
            break

        name = f"{tag}_rec_{idx:03d}_off_{off:06x}"
        save_gray(rec, name)

        save_rgb565(rec, name, big=False, bgr=False)
        save_rgb565(rec, name, big=False, bgr=True)
        save_rgb565(rec, name, big=True, bgr=False)
        save_rgb565(rec, name, big=True, bgr=True)

print("Sortie:", OUT)
