from pathlib import Path
import struct
from PIL import Image

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/payload_units_136x130")
OUT.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 0x400
HEADER_SIZE = 4

WIDTH = 136
HEIGHT = 130
EXPECTED_BYTES = WIDTH * HEIGHT * 3

TARGET_T_NUMBERS = {130} | set(range(154, 175))
EXCLUDED = {157, 168}

# Limite le nombre d’unités exportées pour ne pas produire
# des milliers d’images.
MAX_UNITS = 30

ORDERS = {
    "RGB": (0, 1, 2),
    "BGR": (2, 1, 0),
    "GRB": (1, 0, 2),
    "GBR": (1, 2, 0),
    "RBG": (0, 2, 1),
    "BRG": (2, 0, 1),
}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


def marker_type(header: int):
    if header == 0x00000000:
        return "Z"

    if header == 0x0D000000:
        return "D"

    return None


def build_clusters(markers):
    clusters = []

    for page_index, kind in markers:
        if clusters and page_index == clusters[-1]["end"] + 1:
            clusters[-1]["end"] = page_index
            clusters[-1]["types"].append(kind)
        else:
            clusters.append({
                "start": page_index,
                "end": page_index,
                "types": [kind],
            })

    return clusters


def reorder_channels(data: bytes, order):
    converted = bytearray(len(data))

    for offset in range(0, len(data), 3):
        pixel = data[offset:offset + 3]

        converted[offset] = pixel[order[0]]
        converted[offset + 1] = pixel[order[1]]
        converted[offset + 2] = pixel[order[2]]

    return bytes(converted)


files = []

for path in CACHE.rglob("T*.ithmb"):
    number = get_t_number(path)

    if number in TARGET_T_NUMBERS and number not in EXCLUDED:
        files.append(path)

files.sort(key=lambda path: (get_t_number(path), str(path)))

saved_units = 0

print("=" * 110)
print("PAYLOAD UNITS AS 136x130 RGB888")
print("=" * 110)

for path in files:
    if saved_units >= MAX_UNITS:
        break

    raw = path.read_bytes()
    page_count = len(raw) // PAGE_SIZE

    pages = []

    for page_index in range(page_count):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        pages.append({
            "index": page_index,
            "header": struct.unpack_from(">I", page, 0)[0],
            "payload": page[HEADER_SIZE:],
        })

    markers = []

    for page in pages:
        kind = marker_type(page["header"])

        if kind:
            markers.append((page["index"], kind))

    clusters = build_clusters(markers)

    file_name = path.stem
    relative_parent = path.parent.name

    for unit_index, (left, right) in enumerate(
        zip(clusters, clusters[1:])
    ):
        if saved_units >= MAX_UNITS:
            break

        start_page = left["end"] + 1
        end_page = right["start"] - 1

        if end_page - start_page + 1 != 52:
            continue

        data = b"".join(
            pages[page_index]["payload"]
            for page_index in range(start_page, end_page + 1)
        )

        if len(data) != EXPECTED_BYTES:
            print(
                f"skip {path}: expected {EXPECTED_BYTES}, "
                f"got {len(data)}"
            )
            continue

        unit_name = (
            f"{relative_parent}_{file_name}_"
            f"unit{unit_index:02d}_"
            f"pages{start_page:04d}-{end_page:04d}"
        )

        unit_dir = OUT / unit_name
        unit_dir.mkdir(parents=True, exist_ok=True)

        for order_name, order in ORDERS.items():
            converted = reorder_channels(data, order)

            image = Image.frombytes(
                "RGB",
                (WIDTH, HEIGHT),
                converted,
            )

            variants = {
                "normal": image,
                "flip_vertical": image.transpose(
                    Image.Transpose.FLIP_TOP_BOTTOM
                ),
                "flip_horizontal": image.transpose(
                    Image.Transpose.FLIP_LEFT_RIGHT
                ),
                "rotate_90": image.transpose(
                    Image.Transpose.ROTATE_90
                ),
                "rotate_270": image.transpose(
                    Image.Transpose.ROTATE_270
                ),
            }

            for variant_name, variant in variants.items():
                output_path = (
                    unit_dir
                    / f"{order_name}_{variant_name}.png"
                )

                variant.save(output_path)

                enlarged = variant.resize(
                    (
                        variant.width * 4,
                        variant.height * 4,
                    ),
                    Image.Resampling.NEAREST,
                )

                enlarged.save(
                    unit_dir
                    / f"{order_name}_{variant_name}_4x.png"
                )

        print(
            f"saved unit={saved_units:02d} "
            f"file={path.relative_to(CACHE)} "
            f"pages={start_page}-{end_page} "
            f"folder={unit_dir}"
        )

        saved_units += 1

print()
print(f"units saved: {saved_units}")
print(f"results: {OUT}")
