from pathlib import Path
from PIL import Image

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/yuv_block_order")
OUT.mkdir(parents=True, exist_ok=True)

FILE = ROOT / "F06" / "T104.ithmb"

W, H = 160, 120
OFFSETS = [0, 8, 16, 24, 32, 64, 128, 256, 512]
BLOCKS = [4, 8, 16, 32]
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

def put_pair(px, x, y, q, fmt):
    a,b,c,d = fmt
    y0,u,y1,v = q[a],q[b],q[c],q[d]
    px[x,y] = rgb(y0,u,v)
    if x + 1 < W:
        px[x+1,y] = rgb(y1,u,v)

def render(data, off, block, fmt):
    img = Image.new("RGB", (W,H))
    px = img.load()
    p = off

    for by in range(0, H, block):
        for bx in range(0, W, block):
            for y in range(by, min(by+block, H)):
                for x in range(bx, min(bx+block, W), 2):
                    if p + 3 >= len(data):
                        return img
                    q = [data[p], data[p+1], data[p+2], data[p+3]]
                    put_pair(px, x, y, q, fmt)
                    p += 4

    return img

def main():
    data = FILE.read_bytes()

    for off in OFFSETS:
        for block in BLOCKS:
            for name, fmt in FORMATS.items():
                img = render(data, off, block, fmt)
                out = OUT / f"T104_off{off}_160x120_block{block}_{name}.png"
                img.save(out)
                print("saved", out)

if __name__ == "__main__":
    main()
