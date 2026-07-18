from pathlib import Path
import math
import sys

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    print("Modules manquants : numpy et pillow")
    print("Sous Ubuntu : sudo apt install python3-numpy python3-pil")
    sys.exit(1)


CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/tile_reorder")

TARGETS = {
    "T154.ithmb": {
        "mode": "RGB888",
        "offset": 128,
        "width": 240,
    },
    "T155.ithmb": {
        "mode": "RGB888",
        "offset": 1024,
        "width": 480,
    },
    "T161.ithmb": {
        "mode": "RGB888",
        "offset": 32,
        "width": 480,
    },
    "T170.ithmb": {
        "mode": "RGB888",
        "offset": 4096,
        "width": 480,
    },
    "T173.ithmb": {
        "mode": "RGB888",
        "offset": 2048,
        "width": 480,
    },
}

TILE_SIZES = [8, 16, 32]

MAX_PREVIEW_WIDTH = 900
MAX_PREVIEW_HEIGHT = 900


def locate_file(filename):
    matches = list(CACHE_ROOT.rglob(filename))

    if not matches:
        return None

    return matches[0]


def decode_rgb888(data, offset, bgr=False):
    raw = data[offset:]
    usable = len(raw) - (len(raw) % 3)
    raw = raw[:usable]

    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)

    if bgr:
        pixels = pixels[:, ::-1]

    return pixels.copy()


def build_raster(pixels, width):
    height = len(pixels) // width
    used = width * height

    if height <= 0:
        return None

    return pixels[:used].reshape(height, width, 3)


def build_column_major(pixels, width):
    height = len(pixels) // width
    used = width * height

    if height <= 0:
        return None

    flat = pixels[:used]

    return flat.reshape(width, height, 3).transpose(1, 0, 2)


def split_tiles_from_stream(pixels, tile_size):
    pixels_per_tile = tile_size * tile_size
    tile_count = len(pixels) // pixels_per_tile

    if tile_count <= 0:
        return []

    used = tile_count * pixels_per_tile
    pixel_data = pixels[:used]

    tiles = pixel_data.reshape(
        tile_count,
        tile_size,
        tile_size,
        3,
    )

    return list(tiles)


def tile_grid_dimensions(tile_count, image_width, tile_size):
    preferred_columns = max(1, image_width // tile_size)

    candidates = []

    for columns in range(
        max(1, preferred_columns - 6),
        preferred_columns + 7,
    ):
        rows = math.ceil(tile_count / columns)
        wasted = rows * columns - tile_count
        width_difference = abs(columns - preferred_columns)

        score = wasted * 10 + width_difference
        candidates.append((score, columns, rows))

    candidates.sort()
    _, columns, rows = candidates[0]

    return columns, rows


def morton_decode(index):
    x = 0
    y = 0
    bit = 0

    while index:
        x |= (index & 1) << bit
        index >>= 1

        y |= (index & 1) << bit
        index >>= 1

        bit += 1

    return x, y


def order_raster(tile_count, columns, rows):
    order = []

    for index in range(tile_count):
        y = index // columns
        x = index % columns

        if y >= rows:
            break

        order.append((index, x, y))

    return order


def order_column(tile_count, columns, rows):
    order = []
    index = 0

    for x in range(columns):
        for y in range(rows):
            if index >= tile_count:
                return order

            order.append((index, x, y))
            index += 1

    return order


def order_zigzag(tile_count, columns, rows):
    order = []
    index = 0

    for y in range(rows):
        xs = range(columns)

        if y % 2 == 1:
            xs = reversed(range(columns))

        for x in xs:
            if index >= tile_count:
                return order

            order.append((index, x, y))
            index += 1

    return order


def order_morton(tile_count, columns, rows):
    order = []
    used_positions = set()
    stream_index = 0
    morton_index = 0

    limit = max(columns, rows)
    limit = 1 << math.ceil(math.log2(max(1, limit)))

    while stream_index < tile_count and morton_index < limit * limit:
        x, y = morton_decode(morton_index)
        morton_index += 1

        if x >= columns or y >= rows:
            continue

        if (x, y) in used_positions:
            continue

        used_positions.add((x, y))
        order.append((stream_index, x, y))
        stream_index += 1

    return order


def assemble_tiles(tiles, columns, rows, order, tile_size):
    canvas = np.zeros(
        (
            rows * tile_size,
            columns * tile_size,
            3,
        ),
        dtype=np.uint8,
    )

    for tile_index, x, y in order:
        if tile_index >= len(tiles):
            break

        y0 = y * tile_size
        x0 = x * tile_size

        canvas[
            y0:y0 + tile_size,
            x0:x0 + tile_size,
        ] = tiles[tile_index]

    return canvas


def save_preview(array, output_path, title):
    image = Image.fromarray(array.astype(np.uint8), mode="RGB")

    image.thumbnail(
        (MAX_PREVIEW_WIDTH, MAX_PREVIEW_HEIGHT),
        Image.Resampling.NEAREST,
    )

    label_height = 44

    canvas = Image.new(
        "RGB",
        (image.width, image.height + label_height),
        "white",
    )

    canvas.paste(image, (0, label_height))

    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), title, fill="black")
    draw.text(
        (8, 23),
        f"source={array.shape[1]}x{array.shape[0]}",
        fill="black",
    )

    canvas.save(output_path)


def process_file(filename, config):
    path = locate_file(filename)

    if path is None:
        print(f"[ABSENT] {filename}")
        return []

    print("=" * 80)
    print(f"Fichier : {path.relative_to(CACHE_ROOT)}")
    print(f"Taille  : {path.stat().st_size:,} octets")
    print(f"Mode    : {config['mode']}")
    print(f"Offset  : {config['offset']}")
    print(f"Largeur : {config['width']}")

    file_output = OUTPUT_ROOT / path.stem
    file_output.mkdir(parents=True, exist_ok=True)

    data = path.read_bytes()
    pixels = decode_rgb888(
        data,
        config["offset"],
        bgr=False,
    )

    width = config["width"]
    saved = []

    raster = build_raster(pixels, width)

    if raster is not None:
        output_path = file_output / "00_raster.png"
        save_preview(
            raster,
            output_path,
            f"{filename} | raster RGB888",
        )
        saved.append(output_path)

    column_major = build_column_major(pixels, width)

    if column_major is not None:
        output_path = file_output / "01_column_major_pixels.png"
        save_preview(
            column_major,
            output_path,
            f"{filename} | pixels en colonnes",
        )
        saved.append(output_path)

    bgr_pixels = decode_rgb888(
        data,
        config["offset"],
        bgr=True,
    )

    bgr_raster = build_raster(bgr_pixels, width)

    if bgr_raster is not None:
        output_path = file_output / "02_raster_BGR.png"
        save_preview(
            bgr_raster,
            output_path,
            f"{filename} | raster BGR888",
        )
        saved.append(output_path)

    for tile_size in TILE_SIZES:
        tiles = split_tiles_from_stream(pixels, tile_size)

        if not tiles:
            continue

        columns, rows = tile_grid_dimensions(
            len(tiles),
            width,
            tile_size,
        )

        print()
        print(
            f"Tuiles {tile_size}x{tile_size}: "
            f"{len(tiles)} tuiles, grille {columns}x{rows}"
        )

        orders = {
            "raster": order_raster(
                len(tiles),
                columns,
                rows,
            ),
            "column": order_column(
                len(tiles),
                columns,
                rows,
            ),
            "zigzag": order_zigzag(
                len(tiles),
                columns,
                rows,
            ),
            "morton": order_morton(
                len(tiles),
                columns,
                rows,
            ),
        }

        for order_name, order in orders.items():
            assembled = assemble_tiles(
                tiles,
                columns,
                rows,
                order,
                tile_size,
            )

            filename_out = (
                f"tile{tile_size:02d}"
                f"__{order_name}.png"
            )

            output_path = file_output / filename_out

            save_preview(
                assembled,
                output_path,
                (
                    f"{filename} | "
                    f"{tile_size}x{tile_size} | "
                    f"{order_name}"
                ),
            )

            saved.append(output_path)

    return saved


def create_contact_sheet(paths):
    if not paths:
        return

    tile_width = 260
    tile_height = 230
    columns = 4

    thumbnails = []

    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((250, 190), Image.Resampling.NEAREST)

        tile = Image.new(
            "RGB",
            (tile_width, tile_height),
            "white",
        )

        x = (tile_width - image.width) // 2
        tile.paste(image, (x, 5))

        draw = ImageDraw.Draw(tile)

        label = f"{path.parent.name}/{path.stem}"

        if len(label) > 38:
            label = label[:35] + "..."

        draw.text(
            (6, 204),
            label,
            fill="black",
        )

        thumbnails.append(tile)

    rows = math.ceil(len(thumbnails) / columns)

    sheet = Image.new(
        "RGB",
        (
            columns * tile_width,
            rows * tile_height,
        ),
        "white",
    )

    for index, tile in enumerate(thumbnails):
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        sheet.paste(tile, (x, y))

    sheet.save(OUTPUT_ROOT / "contact_sheet.png")


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("ITHMB TILE REORDER TEST")
    print("=" * 80)

    all_saved = []

    for filename, config in TARGETS.items():
        saved = process_file(filename, config)
        all_saved.extend(saved)

    create_contact_sheet(all_saved)

    print()
    print("=" * 80)
    print("TERMINÉ")
    print("=" * 80)
    print(f"Images générées : {len(all_saved)}")
    print(f"Dossier          : {OUTPUT_ROOT}")
    print(f"Mosaïque         : {OUTPUT_ROOT / 'contact_sheet.png'}")


if __name__ == "__main__":
    main()
