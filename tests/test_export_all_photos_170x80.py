from pathlib import Path
import struct
from PIL import Image, ImageDraw

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/all_photos_170x80")
IMAGES_OUT = OUT / "images"
CONTACT_OUT = OUT / "contact_sheets"

IMAGES_OUT.mkdir(parents=True, exist_ok=True)
CONTACT_OUT.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 0x400
HEADER_SIZE = 4
PAYLOAD_SIZE = PAGE_SIZE - HEADER_SIZE

WIDTH = 170
HEIGHT = 80
EXPECTED = WIDTH * HEIGHT * 3

ACTIVE_FIRST = 6
ACTIVE_LAST = 45

TARGET_T_NUMBERS = {130} | set(range(154, 175))
EXCLUDED = {157, 168}

CONTACT_COLUMNS = 5
CONTACT_ROWS = 5
CONTACT_PER_SHEET = CONTACT_COLUMNS * CONTACT_ROWS

THUMB_SCALE = 3
LABEL_HEIGHT = 30


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

    for page_index, marker in markers:
        if (
            clusters
            and page_index == clusters[-1]["end"] + 1
        ):
            clusters[-1]["end"] = page_index
            clusters[-1]["types"].append(marker)
        else:
            clusters.append({
                "start": page_index,
                "end": page_index,
                "types": [marker],
            })

    return clusters


def swap_rgb_bgr(data: bytes):
    converted = bytearray(len(data))

    for offset in range(0, len(data), 3):
        converted[offset] = data[offset + 2]
        converted[offset + 1] = data[offset + 1]
        converted[offset + 2] = data[offset]

    return bytes(converted)


def make_contact_sheet(entries, sheet_number):
    thumb_width = WIDTH * THUMB_SCALE
    thumb_height = HEIGHT * THUMB_SCALE

    cell_width = thumb_width
    cell_height = thumb_height + LABEL_HEIGHT

    sheet = Image.new(
        "RGB",
        (
            CONTACT_COLUMNS * cell_width,
            CONTACT_ROWS * cell_height,
        ),
        "black",
    )

    draw = ImageDraw.Draw(sheet)

    for index, entry in enumerate(entries):
        image = Image.open(entry["path"]).convert("RGB")

        image = image.resize(
            (thumb_width, thumb_height),
            Image.Resampling.NEAREST,
        )

        column = index % CONTACT_COLUMNS
        row = index // CONTACT_COLUMNS

        x = column * cell_width
        y = row * cell_height

        sheet.paste(image, (x, y + LABEL_HEIGHT))

        draw.text(
            (x + 4, y + 7),
            entry["label"],
            fill="white",
        )

    path = CONTACT_OUT / f"contact_{sheet_number:03d}.jpg"

    sheet.save(
        path,
        quality=92,
    )

    print(f"contact sheet: {path}")


files = []

for path in CACHE.rglob("T*.ithmb"):
    number = get_t_number(path)

    if (
        number in TARGET_T_NUMBERS
        and number not in EXCLUDED
    ):
        files.append(path)

files.sort(
    key=lambda path: (
        get_t_number(path),
        str(path),
    )
)

contact_entries = []
total_units = 0
contact_number = 0

print("=" * 110)
print("EXPORT ALL PHOTOS 170x80")
print("=" * 110)
print(f"files found: {len(files)}")
print()

for path in files:
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

        header = struct.unpack_from(">I", page, 0)[0]

        pages.append({
            "index": page_index,
            "header": header,
            "payload": page[HEADER_SIZE:],
        })

    markers = []

    for page in pages:
        marker = marker_type(page["header"])

        if marker:
            markers.append((page["index"], marker))

    clusters = build_clusters(markers)

    relative = path.relative_to(CACHE)
    folder_name = path.parent.name
    file_name = path.stem

    file_units = 0

    for unit_index, (left, right) in enumerate(
        zip(clusters, clusters[1:])
    ):
        unit_start = left["end"] + 1
        unit_end = right["start"] - 1

        unit_page_count = unit_end - unit_start + 1

        if unit_page_count != 52:
            continue

        active_start = unit_start + ACTIVE_FIRST
        active_end = unit_start + ACTIVE_LAST

        data = b"".join(
            pages[page_index]["payload"]
            for page_index in range(
                active_start,
                active_end + 1,
            )
        )

        if len(data) != EXPECTED:
            print(
                f"skip {relative}: "
                f"expected={EXPECTED}, got={len(data)}"
            )
            continue

        base_name = (
            f"{folder_name}_{file_name}_"
            f"unit{unit_index:03d}_"
            f"pages{unit_start:04d}-{unit_end:04d}"
        )

        rgb = Image.frombytes(
            "RGB",
            (WIDTH, HEIGHT),
            data,
        )

        bgr = Image.frombytes(
            "RGB",
            (WIDTH, HEIGHT),
            swap_rgb_bgr(data),
        )

        variants = {
            "RGB": rgb,
            "RGB_180": rgb.transpose(
                Image.Transpose.ROTATE_180
            ),
            "BGR": bgr,
            "BGR_180": bgr.transpose(
                Image.Transpose.ROTATE_180
            ),
        }

        for variant_name, image in variants.items():
            image_path = (
                IMAGES_OUT
                / f"{base_name}_{variant_name}.png"
            )

            image.save(image_path)

            enlarged = image.resize(
                (WIDTH * 5, HEIGHT * 5),
                Image.Resampling.NEAREST,
            )

            enlarged.save(
                IMAGES_OUT
                / f"{base_name}_{variant_name}_5x.png"
            )

        # BGR normal est utilisé dans les planches,
        # car c'est celui qui semblait le plus naturel.
        contact_entries.append({
            "path": IMAGES_OUT / f"{base_name}_BGR.png",
            "label": f"{total_units:03d} {folder_name}/{file_name}",
        })

        total_units += 1
        file_units += 1

        if len(contact_entries) == CONTACT_PER_SHEET:
            make_contact_sheet(
                contact_entries,
                contact_number,
            )

            contact_entries = []
            contact_number += 1

    print(
        f"{relative}: units={file_units}"
    )

if contact_entries:
    make_contact_sheet(
        contact_entries,
        contact_number,
    )

print()
print("=" * 110)
print("FINISHED")
print("=" * 110)
print(f"total photos: {total_units}")
print(f"images:       {IMAGES_OUT}")
print(f"contacts:     {CONTACT_OUT}")
