from pathlib import Path
from PIL import Image

SRC = Path(
    "output/t156_1k_objects/"
    "object_01_pages_0040-0091_count_52.bin"
)
OUT = Path("output/t156_rgb888_130x136")
OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 130
HEIGHT = 136
EXPECTED = WIDTH * HEIGHT * 3

data = SRC.read_bytes()

print("=" * 100)
print("T156 OBJECT RGB888 130x136")
print("=" * 100)
print(f"source bytes: {len(data)}")
print(f"expected:     {EXPECTED}")

if len(data) != EXPECTED:
    raise SystemExit("La taille ne correspond pas exactement.")

rgb = Image.frombytes("RGB", (WIDTH, HEIGHT), data)
rgb.save(OUT / "object_01_RGB_130x136.png")

bgr_data = bytearray()

for offset in range(0, len(data), 3):
    r, g, b = data[offset:offset + 3]
    bgr_data.extend((b, g, r))

bgr = Image.frombytes("RGB", (WIDTH, HEIGHT), bytes(bgr_data))
bgr.save(OUT / "object_01_BGR_130x136.png")

print(f"saved: {OUT / 'object_01_RGB_130x136.png'}")
print(f"saved: {OUT / 'object_01_BGR_130x136.png'}")
