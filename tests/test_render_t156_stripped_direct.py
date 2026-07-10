from pathlib import Path
from PIL import Image

SRC = Path("output/T156_stripped.bin")
OUT = Path("output/t156_stripped_direct")
OUT.mkdir(exist_ok=True)

data = SRC.read_bytes()

def save_gray(w, h, off=0):
    size = w * h
    chunk = data[off:off+size]
    if len(chunk) < size:
        return
    img = Image.frombytes("L", (w, h), chunk)
    img.save(OUT / f"gray_{w}x{h}_off{off}.png")

for off in [0, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
    for w, h in [(64,64), (96,96), (120,120), (128,128), (176,220), (220,176)]:
        save_gray(w, h, off)

print("saved", OUT)
