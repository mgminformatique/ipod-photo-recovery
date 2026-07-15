from pathlib import Path
from PIL import Image

SRC = Path(
    "output/t156_1k_objects/"
    "object_01_pages_0040-0091_count_52.bin"
)

OUT = Path("output/t156_rgb888_tiles_8x8")
OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 130
HEIGHT = 136

TILE_W = 8
TILE_H = 8
BPP = 3

data = SRC.read_bytes()

expected = WIDTH * HEIGHT * BPP

if len(data) != expected:
    raise SystemExit(
        f"Bad size: got {len(data)}, expected {expected}"
    )

tiles_x = (WIDTH + TILE_W - 1) // TILE_W
tiles_y = (HEIGHT + TILE_H - 1) // TILE_H

tile_bytes = TILE_W * TILE_H * BPP

print("=" * 100)
print("T156 RGB888 TILE 8x8")
print("=" * 100)
print(f"source bytes: {len(data)}")
print(f"image: {WIDTH}x{HEIGHT}")
print(f"tile grid: {tiles_x}x{tiles_y}")
print(f"tile bytes: {tile_bytes}")
print()

def place_tiles(order):
    image = Image.new("RGB", (WIDTH, HEIGHT))
    offset = 0

    if order == "row":
        tile_positions = [
            (tx, ty)
            for ty in range(tiles_y)
            for tx in range(tiles_x)
        ]
    elif order == "col":
        tile_positions = [
            (tx, ty)
            for tx in range(tiles_x)
            for ty in range(tiles_y)
        ]
    else:
        raise ValueError(order)

    for tx, ty in tile_positions:
        tile_data = data[offset:offset + tile_bytes]

        if len(tile_data) < tile_bytes:
            break

        tile = Image.frombytes(
            "RGB",
            (TILE_W, TILE_H),
            tile_data,
        )

        x = tx * TILE_W
        y = ty * TILE_H

        visible_w = min(TILE_W, WIDTH - x)
        visible_h = min(TILE_H, HEIGHT - y)

        if visible_w <= 0 or visible_h <= 0:
            offset += tile_bytes
            continue

        if visible_w != TILE_W or visible_h != TILE_H:
            tile = tile.crop((0, 0, visible_w, visible_h))

        image.paste(tile, (x, y))
        offset += tile_bytes

    return image


row = place_tiles("row")
row.save(OUT / "object_01_rgb888_tile8x8_row.png")

col = place_tiles("col")
col.save(OUT / "object_01_rgb888_tile8x8_col.png")

print(f"saved: {OUT / 'object_01_rgb888_tile8x8_row.png'}")
print(f"saved: {OUT / 'object_01_rgb888_tile8x8_col.png'}")
