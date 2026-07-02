from pathlib import Path

from core.binary import BinaryFile
from decoder.rgb565_tiled import (
    rgb565_to_pixels,
    save_linear,
    save_tiled,
    save_column_tiled,
)

bf = BinaryFile("/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb")

out = Path("output/rgb565_tiled")
out.mkdir(parents=True, exist_ok=True)

width = 120
height = 120
frame_size = width * height * 2

base_offsets = [0, 88]
tile_sizes = [
    (2, 2),
    (4, 4),
    (8, 8),
    (16, 16),
    (8, 16),
    (16, 8),
    (24, 24),
    (30, 30),
]

for base_offset in base_offsets:
    for frame in range(16):
        offset = base_offset + frame * frame_size

        pixels = rgb565_to_pixels(bf.data, width, height, offset)

        if pixels is None:
            continue

        save_linear(
            pixels,
            width,
            height,
            out / f"T113_off{base_offset}_frame{frame:02d}_linear.png",
        )

        for tw, th in tile_sizes:
            save_tiled(
                pixels,
                width,
                height,
                tw,
                th,
                out / f"T113_off{base_offset}_frame{frame:02d}_tile_row_{tw}x{th}.png",
            )

            save_column_tiled(
                pixels,
                width,
                height,
                tw,
                th,
                out / f"T113_off{base_offset}_frame{frame:02d}_tile_col_{tw}x{th}.png",
            )

print("Fait:", out)
