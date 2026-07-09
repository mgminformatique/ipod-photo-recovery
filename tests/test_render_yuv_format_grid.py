from pathlib import Path
from PIL import Image

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/yuv_format_grid")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [
    ROOT / "F06" / "T104.ithmb",
    ROOT / "F07" / "T105.ithmb",
    ROOT / "F08" / "T106.ithmb",
    ROOT / "F09" / "T107.ithmb",
]

DIMS = [(64,64), (96,96), (128,128), (160,120), (176,132), (220,176)]
OFFSETS = [0, 8, 16, 24, 32, 64, 128, 256, 512, 1024]

FORMATS = {
    "YUYV": (0,1,2,3),
    "UYVY": (1,0,3,2),
    "YVYU": (0,3,2,1),
    "VYUY": (1,2,3,0),
}

def clamp(x):
    return max(0, min(255, int(x)))

def rgb(y,u,v):
    r = y + 1.402 * (v - 128)
    g = y - 0.344136 * (u - 128) - 0.714136 * (v - 128)
    b = y + 1.772 * (u - 128)
    return clamp(r), clamp(g), clamp(b)

def render(buf, w, h, fmt):
    img = Image.new("RGB", (w,h))
    px = img.load()
    a,b,c,d = fmt

    for y in range(h):
        for x in range(0,w,2):
            i = (y*w + x)*2
            if i+3 >= len(buf):
                continue

            q = [buf[i], buf[i+1], buf[i+2], buf[i+3]]
            y0 = q[a]
            u  = q[b]
            y1 = q[c]
            v  = q[d]

            px[x,y] = rgb(y0,u,v)
            if x+1 < w:
                px[x+1,y] = rgb(y1,u,v)

    return img

def main():
    for path in FILES:
        data = path.read_bytes()

        for off in OFFSETS:
            for w,h in DIMS:
                need = w*h*2
                if off + need > len(data):
                    continue

                buf = data[off:off+need]

                for name, fmt in FORMATS.items():
                    img = render(buf, w,h,fmt)
                    out = OUT / f"{path.parent.name}_{path.name}_off{off}_{w}x{h}_{name}.png"
                    img.save(out)
                    print("saved", out)

if __name__ == "__main__":
    main()
