from pathlib import Path

from core.binary import BinaryFile
from decoder.tiled import (
    bytes_to_rgb888_pixels,
    linear_image,
    tiled_image,
    snake_rows_image,
)

bf = BinaryFile("/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb")

out = Path("output/tiled_preview")
out.mkdir(parents=True, exist_ok=True)

width = 120
height = 120
offsets = [0, 88, 928, 1024]
modes = ["RGB", "BGR"]
tiles = [
    (4, 4),
    (8, 8),
    (16, 16),
    (32, 8),
    (8, 32),
    (32, 32),
]

for offset in offsets:
    for mode in modes:
        pixels = bytes_to_rgb888_pixels(bf.data, width, height, offset, mode)

        if pixels is None:
            continue

        linear_image(pixels, width, height).save(
            out / f"T161_{width}x{height}_off{offset}_{mode}_linear.png"
        )

        snake_rows_image(pixels, width, height).save(
            out / f"T161_{width}x{height}_off{offset}_{mode}_snake_rows.png"
        )

        for tw, th in tiles:
            tiled_image(pixels, width, height, tw, th).save(
                out / f"T161_{width}x{height}_off{offset}_{mode}_tile_{tw}x{th}.png"
            )

print("Fait:", out)
