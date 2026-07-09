from pathlib import Path
from PIL import Image

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/payload_grayscale_grid")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    ROOT / "F05" / "T154.ithmb",
    ROOT / "F06" / "T155.ithmb",
    ROOT / "F07" / "T156.ithmb",
    ROOT / "F08" / "T157.ithmb",
    ROOT / "F09" / "T158.ithmb",
]

DIMS = [(96,96), (128,128), (160,120), (176,132), (220,176), (320,240)]
OFFSETS = [
    0,
    0x7000, 0x25000, 0x2f000, 0x30000, 0x33000, 0x34000,
    0x3a000, 0x3c000, 0x42000, 0x61000, 0x62000,
    0x81000, 0xba000, 0xbb000, 0xc6000,
]

def render_gray(data, off, w, h):
    need = w * h
    buf = data[off:off+need]
    if len(buf) < need:
        return None
    return Image.frombytes("L", (w,h), buf).convert("RGB")

def main():
    for path in FILES:
        data = path.read_bytes()

        for off in OFFSETS:
            for w,h in DIMS:
                img = render_gray(data, off,w,h)
                if img is None:
                    continue

                out = OUT / f"{path.parent.name}_{path.name}_off{off:x}_{w}x{h}_GRAY.png"
                img.save(out)
                print("saved", out)

if __name__ == "__main__":
    main()
