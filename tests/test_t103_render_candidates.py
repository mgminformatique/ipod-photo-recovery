from pathlib import Path
from PIL import Image
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F05" / "T103.ithmb"
OUT = Path("output/t103_render_candidates")
OUT.mkdir(parents=True, exist_ok=True)

START = 8
RECORD_SIZE = 24

def rgb565_to_rgb(v):
    r = ((v >> 11) & 0x1F) << 3
    g = ((v >> 5) & 0x3F) << 2
    b = (v & 0x1F) << 3
    return (r, g, b)

def main():
    data = FILE.read_bytes()
    payload = data[START:]

    print("=" * 80)
    print("T103 RENDER CANDIDATES")
    print("=" * 80)
    print(f"file size: {len(data)}")
    print(f"payload size: {len(payload)}")

    candidates = [
        (80, 80),
        (96, 96),
        (100, 100),
        (104, 104),
        (112, 112),
        (120, 120),
        (128, 128),
        (144, 144),
        (160, 120),
        (176, 132),
        (208, 156),
        (220, 176),
        (240, 180),
        (320, 240),
    ]

    for w, h in candidates:
        need = w * h * 2
        if need > len(payload):
            continue

        img = Image.new("RGB", (w, h))
        px = img.load()

        for i in range(w * h):
            off = i * 2
            v = struct.unpack_from("<H", payload, off)[0]
            px[i % w, i // w] = rgb565_to_rgb(v)

        out = OUT / f"t103_rgb565_{w}x{h}.png"
        img.save(out)
        print(f"saved {out}")

if __name__ == "__main__":
    main()
