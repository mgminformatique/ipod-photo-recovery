from pathlib import Path
from PIL import Image
import numpy as np

SRC = Path("output/payload_units_136x130")
OUT = Path("output/payload_170x104_non_wrapping")
OUT.mkdir(parents=True, exist_ok=True)

PIXELS = 17680
WIDTH = 170
HEIGHT = 104
DRIFT = 10

ORDERS = {
    "RGB": (0, 1, 2),
    "BGR": (2, 1, 0),
}

MAX_UNITS = 30


def reorder(data: bytes, order):
    array = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
    return array[:, list(order)]


folders = [
    folder
    for folder in sorted(SRC.iterdir())
    if folder.is_dir()
]

saved = 0

print("=" * 100)
print("170x104 NON-WRAPPING ROW CORRECTION")
print("=" * 100)

for folder in folders:
    if saved >= MAX_UNITS:
        break

    source = folder / "RGB_normal.png"

    if not source.exists():
        continue

    raw = Image.open(source).convert("RGB").tobytes()

    if len(raw) != PIXELS * 3:
        continue

    for order_name, order in ORDERS.items():
        pixels = reorder(raw, order)

        base = pixels.reshape(HEIGHT, WIDTH, 3)

        # Version 1 : retire le décalage progressivement,
        # sans reboucler les pixels.
        corrected = np.zeros_like(base)

        for row in range(HEIGHT):
            shift = (row * DRIFT) % WIDTH

            if shift == 0:
                corrected[row] = base[row]
            else:
                usable = WIDTH - shift
                corrected[row, :usable] = base[row, shift:]
                corrected[row, usable:] = 0

        image = Image.fromarray(corrected, "RGB")
        image.save(OUT / f"{folder.name}_{order_name}_crop.png")

        image.resize(
            (WIDTH * 4, HEIGHT * 4),
            Image.Resampling.NEAREST,
        ).save(
            OUT / f"{folder.name}_{order_name}_crop_4x.png"
        )

        # Version 2 : chaque ligne commence 10 pixels plus loin
        # dans le flux linéaire original.
        flat = pixels.reshape(-1, 3)
        reconstructed = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        for row in range(HEIGHT):
            start = row * WIDTH + row * DRIFT
            end = start + WIDTH

            if end <= len(flat):
                reconstructed[row] = flat[start:end]

        image2 = Image.fromarray(reconstructed, "RGB")
        image2.save(OUT / f"{folder.name}_{order_name}_stream.png")

        image2.resize(
            (WIDTH * 4, HEIGHT * 4),
            Image.Resampling.NEAREST,
        ).save(
            OUT / f"{folder.name}_{order_name}_stream_4x.png"
        )

    print(f"saved: {folder.name}")
    saved += 1

print()
print(f"units saved: {saved}")
print(f"results: {OUT}")
