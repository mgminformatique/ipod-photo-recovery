from pathlib import Path
from PIL import Image
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/rgb16_grid")
OUT.mkdir(parents=True, exist_ok=True)

FILE = ROOT / "F06" / "T104.ithmb"

DIMS = [(96,96), (128,128), (160,120), (176,132), (220,176)]
OFFSETS = [0, 8, 16, 24, 32, 64, 128, 256, 512]
STRIDES = [0, 192, 256, 320, 352, 384, 440, 512, 640]

def rgb565(v):
    r = ((v >> 11) & 0x1f) * 255 // 31
    g = ((v >> 5) & 0x3f) * 255 // 63
    b = (v & 0x1f) * 255 // 31
    return r,g,b

def rgb555(v):
    r = ((v >> 10) & 0x1f) * 255 // 31
    g = ((v >> 5) & 0x1f) * 255 // 31
    b = (v & 0x1f) * 255 // 31
    return r,g,b

def render(data, off, w, h, stride, mode, endian):
    if stride == 0:
        stride = w * 2

    img = Image.new("RGB", (w,h))
    px = img.load()

    for y in range(h):
        row = off + y * stride
        for x in range(w):
            p = row + x * 2
            if p + 1 >= len(data):
                continue

            if endian == "LE":
                v = data[p] | (data[p+1] << 8)
            else:
                v = (data[p] << 8) | data[p+1]

            px[x,y] = rgb565(v) if mode == "RGB565" else rgb555(v)

    return img

def main():
    data = FILE.read_bytes()

    for off in OFFSETS:
        for w,h in DIMS:
            for stride in STRIDES:
                if off + (stride or w*2) * h > len(data):
                    continue

                for mode in ["RGB565", "RGB555"]:
                    for endian in ["LE", "BE"]:
                        img = render(data, off, w,h,stride,mode,endian)
                        out = OUT / f"T104_off{off}_{w}x{h}_stride{stride}_{mode}_{endian}.png"
                        img.save(out)
                        print("saved", out)

if __name__ == "__main__":
    main()
