from pathlib import Path
from PIL import Image

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/raw_yuv_grid")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    ROOT / "F06" / "T104.ithmb",
    ROOT / "F07" / "T105.ithmb",
    ROOT / "F09" / "T107.ithmb",
    ROOT / "F17" / "T115.ithmb",
]

DIMS = [(64,64), (96,96), (128,128), (160,120), (176,132), (220,176)]
OFFSETS = [0, 8, 16, 24, 32, 64, 128, 256, 512, 1024]

def clamp(x):
    return max(0, min(255, int(x)))

def rgb_from_yuv(y,u,v):
    r = y + 1.402 * (v - 128)
    g = y - 0.344136 * (u - 128) - 0.714136 * (v - 128)
    b = y + 1.772 * (u - 128)
    return clamp(r), clamp(g), clamp(b)

def render(buf, w, h):
    img = Image.new("RGB", (w,h))
    px = img.load()
    for y in range(h):
        for x in range(0,w,2):
            i = (y*w + x)*2
            if i+3 >= len(buf):
                continue
            y0,u,y1,v = buf[i], buf[i+1], buf[i+2], buf[i+3]
            px[x,y] = rgb_from_yuv(y0,u,v)
            if x+1 < w:
                px[x+1,y] = rgb_from_yuv(y1,u,v)
    return img

def main():
    for path in FILES:
        data = path.read_bytes()
        for off in OFFSETS:
            for w,h in DIMS:
                need = w*h*2
                if off + need <= len(data):
                    img = render(data[off:off+need], w,h)
                    out = OUT / f"{path.parent.name}_{path.name}_off{off}_{w}x{h}.png"
                    img.save(out)
                    print("saved", out)

if __name__ == "__main__":
    main()
