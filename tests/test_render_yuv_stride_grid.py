from pathlib import Path
from PIL import Image

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/yuv_stride_grid")
OUT.mkdir(parents=True, exist_ok=True)

FILES = [ROOT / "F06" / "T104.ithmb"]
DIMS = [(96,96), (128,128), (160,120), (176,132), (220,176)]
OFFSETS = [0, 8, 16, 24, 32, 64, 128, 256, 512]
STRIDES = [128, 192, 256, 320, 352, 384, 440, 512, 640]

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

def render(data, off, w, h, stride, fmt):
    img = Image.new("RGB", (w,h))
    px = img.load()
    a,b,c,d = fmt

    for y in range(h):
        row = off + y * stride
        for x in range(0, w, 2):
            i = row + x * 2
            if i + 3 >= len(data):
                continue
            q = [data[i], data[i+1], data[i+2], data[i+3]]
            y0, u, y1, v = q[a], q[b], q[c], q[d]
            px[x,y] = rgb(y0,u,v)
            if x + 1 < w:
                px[x+1,y] = rgb(y1,u,v)
    return img

def main():
    for path in FILES:
        data = path.read_bytes()
        for off in OFFSETS:
            for w,h in DIMS:
                for stride in STRIDES:
                    if off + stride * h > len(data):
                        continue
                    for name, fmt in FORMATS.items():
                        img = render(data, off, w,h,stride,fmt)
                        out = OUT / f"{path.parent.name}_{path.name}_off{off}_{w}x{h}_stride{stride}_{name}.png"
                        img.save(out)
                        print("saved", out)

if __name__ == "__main__":
    main()
