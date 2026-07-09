from pathlib import Path
from PIL import Image

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/active_payload_blocks")
OUT.mkdir(parents=True, exist_ok=True)

JOBS = [
    (ROOT / "F05" / "T154.ithmb", [0x2f000, 0x30000, 0x61000, 0x62000]),
    (ROOT / "F06" / "T155.ithmb", [0x33000, 0x34000, 0x66000, 0xbb000]),
    (ROOT / "F07" / "T156.ithmb", [0x07000, 0x3a000, 0x3c000, 0x42000]),
    (ROOT / "F08" / "T157.ithmb", [0x1f000, 0x35000, 0x81000, 0xba000]),
    (ROOT / "F09" / "T158.ithmb", [0x25000, 0x27000, 0xb7000, 0xc6000]),
]

DIMS = [(96,96), (128,128), (160,120), (176,132), (220,176), (320,240)]
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

def render(data, off, w, h, fmt):
    img = Image.new("RGB", (w,h))
    px = img.load()
    a,b,c,d = fmt

    for y in range(h):
        for x in range(0,w,2):
            i = off + (y*w + x)*2
            if i + 3 >= len(data):
                continue
            q = [data[i], data[i+1], data[i+2], data[i+3]]
            y0,u,y1,v = q[a],q[b],q[c],q[d]
            px[x,y] = rgb(y0,u,v)
            if x+1 < w:
                px[x+1,y] = rgb(y1,u,v)
    return img

def main():
    for path, offsets in JOBS:
        data = path.read_bytes()
        for off in offsets:
            for w,h in DIMS:
                if off + w*h*2 > len(data):
                    continue
                for name, fmt in FORMATS.items():
                    img = render(data, off,w,h,fmt)
                    out = OUT / f"{path.parent.name}_{path.name}_off{off:x}_{w}x{h}_{name}.png"
                    img.save(out)
                    print("saved", out)

if __name__ == "__main__":
    main()
