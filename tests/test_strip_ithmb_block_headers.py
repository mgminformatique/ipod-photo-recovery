from pathlib import Path
from PIL import Image, ImageOps

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/ithmb_stripped")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    CACHE / "F23" / "T172.ithmb",
    CACHE / "F12" / "T161.ithmb",
    CACHE / "F08" / "T157.ithmb",
]

SIZES = [(120, 120), (130, 88), (176, 220), (220, 176)]


def strip_headers(raw, block_size=4096, header_size=4):
    out = bytearray()
    for i in range(0, len(raw), block_size):
        block = raw[i:i + block_size]
        if len(block) > header_size:
            out.extend(block[header_size:])
    return bytes(out)


def rgb565(data, w, h, big=False, bgr=False):
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


for target in TARGETS:
    if not target.exists():
        continue

    raw = target.read_bytes()
    stripped = strip_headers(raw)

    tag = f"{target.parent.name}_{target.stem}"
    (OUT / f"{tag}_stripped.bin").write_bytes(stripped)

    print(target.relative_to(CACHE), "raw", len(raw), "stripped", len(stripped))

    for offset in [0, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
        chunk = stripped[offset:]

        for w, h in SIZES:
            for big in [False, True]:
                for bgr in [False, True]:
                    img = rgb565(chunk, w, h, big=big, bgr=bgr)
                    if img:
                        name = f"{tag}_strip_off{offset}_rgb565_{w}x{h}_{'BE' if big else 'LE'}_{'BGR' if bgr else 'RGB'}"
                        img.save(OUT / f"{name}.png")
                        ImageOps.mirror(img).save(OUT / f"{name}_flipH.png")

print("Sortie:", OUT)
