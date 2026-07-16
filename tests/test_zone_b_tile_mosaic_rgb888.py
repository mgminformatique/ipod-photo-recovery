from pathlib import Path
import struct
from PIL import Image, ImageOps

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

TILE_MIN = 2304
TILE_MAX = 2431

TILE_W = 20
TILE_H = 17

OUT = Path("output/zone_b_tile_mosaic")
OUT.mkdir(parents=True, exist_ok=True)


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


tiles = {}

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    page_count = len(raw) // PAGE_SIZE

    for table_page in range(page_count):
        page = raw[
            table_page * PAGE_SIZE:
            (table_page + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        if struct.unpack_from(">I", page, 0)[0] != 0x0D000000:
            continue

        table_payload = page[HEADER_SIZE:]

        for record_index in range(RECORD_COUNT):
            start = RECORD_START + record_index * RECORD_SIZE
            record = table_payload[start:start + RECORD_SIZE]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]
            f56 = struct.unpack_from(">H", record, 0x56)[0]

            if not TILE_MIN <= tile_id <= TILE_MAX:
                continue

            if f56 % 9:
                continue

            data_page = f56 // 9

            # Zone B observée précédemment.
            if not 251 <= data_page <= 384:
                continue

            if not 0 <= data_page < page_count:
                continue

            raw_page = raw[
                data_page * PAGE_SIZE:
                (data_page + 1) * PAGE_SIZE
            ]

            payload = raw_page[HEADER_SIZE:]

            if len(payload) != TILE_W * TILE_H * 3:
                continue

            tiles[tile_id] = {
                "data": payload,
                "file": str(path.relative_to(CACHE)),
                "page": data_page,
            }


print("=" * 100)
print("ZONE B TILE MOSAIC RGB888")
print("=" * 100)
print(f"tiles found: {len(tiles)}/128")

missing = [
    tile_id
    for tile_id in range(TILE_MIN, TILE_MAX + 1)
    if tile_id not in tiles
]

print(f"missing: {missing or 'none'}")


def decode_tile(payload: bytes, order: str) -> Image.Image:
    image = Image.frombytes("RGB", (TILE_W, TILE_H), payload)

    if order == "RGB":
        return image

    r, g, b = image.split()

    if order == "BGR":
        return Image.merge("RGB", (b, g, r))

    raise ValueError(order)


def build_mosaic(cols: int, rows: int, order: str, snake: bool):
    mosaic = Image.new(
        "RGB",
        (cols * TILE_W, rows * TILE_H),
        (0, 0, 0),
    )

    for tile_id in range(TILE_MIN, TILE_MAX + 1):
        index = tile_id - TILE_MIN

        row = index // cols
        col = index % cols

        if row >= rows:
            continue

        if snake and row % 2 == 1:
            col = cols - 1 - col

        entry = tiles.get(tile_id)

        if entry is None:
            continue

        tile = decode_tile(entry["data"], order)
        mosaic.paste(tile, (col * TILE_W, row * TILE_H))

    suffix = "snake" if snake else "row"

    path = OUT / (
        f"zone_b_{cols}x{rows}_tiles_"
        f"{mosaic.width}x{mosaic.height}_"
        f"{order}_{suffix}.png"
    )

    mosaic.save(path)

    # Version agrandie pour inspection.
    enlarged = mosaic.resize(
        (mosaic.width * 4, mosaic.height * 4),
        Image.Resampling.NEAREST,
    )

    enlarged.save(
        OUT / (
            f"zone_b_{cols}x{rows}_tiles_"
            f"{order}_{suffix}_4x.png"
        )
    )

    print(f"saved: {path}")


for cols, rows in [(16, 8), (8, 16)]:
    for order in ["RGB", "BGR"]:
        for snake in [False, True]:
            build_mosaic(cols, rows, order, snake)
