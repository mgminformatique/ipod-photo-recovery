from pathlib import Path
import csv
import math
import sys

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    print("Modules manquants. Installe-les avec :")
    print("python3 -m pip install numpy pillow")
    sys.exit(1)


CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/ithmb_inspector")
PREVIEW_ROOT = OUTPUT_ROOT / "previews"

TOP_PER_FILE = 3
MAX_DECODE_PIXELS = 2_500_000
MAX_PREVIEW_SIDE = 900

# Offsets raisonnables : début brut, petits headers et pages de 512/4096 octets.
OFFSETS = [
    0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64,
    128, 256, 512, 1024, 2048, 4096
]

# Largeurs communes aux anciennes miniatures Apple et écrans iPod/iPhone.
WIDTHS = [
    40, 48, 56, 64, 72, 80, 88, 96,
    100, 112, 120, 128, 132, 144, 150, 160,
    176, 180, 192, 200, 220, 240, 256, 280,
    300, 320, 352, 360, 400, 480, 512, 640,
    720, 768, 800, 960, 1024
]


def find_ithmb_files():
    return sorted(
        CACHE_ROOT.rglob("*.ithmb"),
        key=lambda p: (
            p.parent.name.lower(),
            p.name.lower()
        )
    )


def decode_16(raw, mode):
    values = np.frombuffer(raw, dtype="<u2")

    if mode == "RGB565":
        r = ((values >> 11) & 0x1F) * 255 // 31
        g = ((values >> 5) & 0x3F) * 255 // 63
        b = (values & 0x1F) * 255 // 31

    elif mode == "BGR565":
        b = ((values >> 11) & 0x1F) * 255 // 31
        g = ((values >> 5) & 0x3F) * 255 // 63
        r = (values & 0x1F) * 255 // 31

    elif mode == "RGB555":
        r = ((values >> 10) & 0x1F) * 255 // 31
        g = ((values >> 5) & 0x1F) * 255 // 31
        b = (values & 0x1F) * 255 // 31

    elif mode == "BGR555":
        b = ((values >> 10) & 0x1F) * 255 // 31
        g = ((values >> 5) & 0x1F) * 255 // 31
        r = (values & 0x1F) * 255 // 31

    elif mode == "ARGB1555":
        r = ((values >> 10) & 0x1F) * 255 // 31
        g = ((values >> 5) & 0x1F) * 255 // 31
        b = (values & 0x1F) * 255 // 31

    else:
        raise ValueError(mode)

    return np.stack((r, g, b), axis=1).astype(np.uint8)


def decode_24(raw, mode):
    values = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)

    if mode == "RGB888":
        return values.copy()

    if mode == "BGR888":
        return values[:, ::-1].copy()

    raise ValueError(mode)


FORMATS = [
    ("RGB565", 2),
    ("BGR565", 2),
    ("RGB555", 2),
    ("BGR555", 2),
    ("ARGB1555", 2),
    ("RGB888", 3),
    ("BGR888", 3),
]


def decode_pixels(data, offset, mode, bpp):
    available = len(data) - offset
    usable = available - (available % bpp)

    if usable <= 0:
        return None

    usable = min(usable, MAX_DECODE_PIXELS * bpp)
    raw = data[offset:offset + usable]

    if bpp == 2:
        return decode_16(raw, mode)

    return decode_24(raw, mode)


def image_score(image_array):
    """
    Une vraie image a généralement des pixels voisins plus semblables que
    des données aléatoires. Le score favorise :
      - la continuité horizontale et verticale;
      - une variance suffisante;
      - l'absence de couleurs totalement aléatoires.
    """
    h, w, _ = image_array.shape

    if h < 16 or w < 16:
        return -999.0

    # Réduction pour rendre le calcul rapide.
    step_y = max(1, h // 180)
    step_x = max(1, w // 180)
    sample = image_array[::step_y, ::step_x].astype(np.int16)

    if sample.shape[0] < 4 or sample.shape[1] < 4:
        return -999.0

    horizontal = np.abs(sample[:, 1:] - sample[:, :-1]).mean()
    vertical = np.abs(sample[1:] - sample[:-1]).mean()

    smoothness = 255.0 - ((horizontal + vertical) / 2.0)
    contrast = float(sample.std())

    # Images totalement plates ou totalement aléatoires sont pénalisées.
    contrast_bonus = min(contrast, 70.0)

    aspect = w / h
    aspect_penalty = 0.0

    if aspect < 0.15 or aspect > 7.0:
        aspect_penalty = 50.0

    return smoothness + contrast_bonus - aspect_penalty


def candidate_dimensions(pixel_count):
    dimensions = []

    for width in WIDTHS:
        height = pixel_count // width

        if height < 16:
            continue

        if height > 5000:
            continue

        used = width * height
        remainder = pixel_count - used
        remainder_ratio = remainder / pixel_count

        # Autorise un petit reste, car certains fichiers peuvent avoir
        # un footer ou une portion de page inutilisée.
        if remainder_ratio <= 0.015:
            dimensions.append((width, height, used, remainder))

    return dimensions


def make_preview(pixels, width, height):
    used = width * height
    array = pixels[:used].reshape(height, width, 3)
    return Image.fromarray(array, mode="RGB"), array


def safe_name(path):
    relative = path.relative_to(CACHE_ROOT)
    return "__".join(relative.parts).replace(".ithmb", "")


def inspect_file(path):
    data = path.read_bytes()
    best = []

    for offset in OFFSETS:
        if offset >= len(data):
            continue

        for mode, bpp in FORMATS:
            pixels = decode_pixels(data, offset, mode, bpp)

            if pixels is None:
                continue

            for width, height, used, remainder in candidate_dimensions(len(pixels)):
                try:
                    _, array = make_preview(pixels, width, height)
                    score = image_score(array)
                except Exception:
                    continue

                result = {
                    "score": score,
                    "path": str(path),
                    "file": path.name,
                    "relative_path": str(path.relative_to(CACHE_ROOT)),
                    "size_bytes": len(data),
                    "mode": mode,
                    "bpp": bpp,
                    "offset": offset,
                    "width": width,
                    "height": height,
                    "used_pixels": used,
                    "remainder_pixels": remainder,
                }

                best.append(result)

    best.sort(key=lambda item: item["score"], reverse=True)
    return best[:TOP_PER_FILE]


def save_candidate(result, rank):
    path = Path(result["path"])
    data = path.read_bytes()

    mode = result["mode"]
    bpp = result["bpp"]
    offset = result["offset"]
    width = result["width"]
    height = result["height"]

    pixels = decode_pixels(data, offset, mode, bpp)
    image, _ = make_preview(pixels, width, height)

    image.thumbnail(
        (MAX_PREVIEW_SIDE, MAX_PREVIEW_SIDE),
        Image.Resampling.NEAREST
    )

    label_height = 55
    canvas = Image.new(
        "RGB",
        (image.width, image.height + label_height),
        "white"
    )

    canvas.paste(image, (0, label_height))

    draw = ImageDraw.Draw(canvas)
    draw.text(
        (8, 6),
        f"{path.name} | #{rank} | {mode}",
        fill="black"
    )
    draw.text(
        (8, 26),
        f"{width}x{height} | offset={offset} | score={result['score']:.2f}",
        fill="black"
    )

    filename = (
        f"{safe_name(path)}"
        f"__rank{rank}"
        f"__{mode}"
        f"__{width}x{height}"
        f"__off{offset}.png"
    )

    output_path = PREVIEW_ROOT / filename
    canvas.save(output_path)

    result["preview"] = str(output_path)


def create_contact_sheet(results):
    if not results:
        return

    thumbnails = []

    for result in results:
        preview = Image.open(result["preview"]).convert("RGB")
        preview.thumbnail((240, 200), Image.Resampling.NEAREST)

        tile = Image.new("RGB", (250, 230), "white")
        x = (250 - preview.width) // 2
        tile.paste(preview, (x, 5))

        draw = ImageDraw.Draw(tile)
        draw.text(
            (6, 208),
            f"{result['file']} #{result['rank']}",
            fill="black"
        )

        thumbnails.append(tile)

    columns = 4
    rows = math.ceil(len(thumbnails) / columns)

    sheet = Image.new(
        "RGB",
        (columns * 250, rows * 230),
        "white"
    )

    for index, tile in enumerate(thumbnails):
        x = (index % columns) * 250
        y = (index // columns) * 230
        sheet.paste(tile, (x, y))

    sheet.save(OUTPUT_ROOT / "contact_sheet.png")


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)

    files = find_ithmb_files()

    print("=" * 80)
    print("ITHMB INSPECTOR — PHASE 1")
    print("=" * 80)
    print(f"Cache : {CACHE_ROOT}")
    print(f"Files : {len(files)}")
    print()

    all_results = []

    for index, path in enumerate(files, 1):
        relative = path.relative_to(CACHE_ROOT)

        print(
            f"[{index:02d}/{len(files):02d}] "
            f"{relative} ({path.stat().st_size:,} bytes)"
        )

        candidates = inspect_file(path)

        if not candidates:
            print("  Aucun candidat.")
            continue

        for rank, result in enumerate(candidates, 1):
            result["rank"] = rank
            save_candidate(result, rank)
            all_results.append(result)

            print(
                f"  #{rank} "
                f"{result['mode']:<8} "
                f"{result['width']:4d}x{result['height']:<5d} "
                f"offset={result['offset']:<4d} "
                f"score={result['score']:.2f}"
            )

    csv_path = OUTPUT_ROOT / "results.csv"

    fields = [
        "rank",
        "file",
        "relative_path",
        "size_bytes",
        "mode",
        "bpp",
        "offset",
        "width",
        "height",
        "used_pixels",
        "remainder_pixels",
        "score",
        "preview",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for result in all_results:
            writer.writerow({
                key: result.get(key, "")
                for key in fields
            })

    create_contact_sheet(all_results)

    print()
    print("=" * 80)
    print("TERMINÉ")
    print("=" * 80)
    print(f"Résultats : {csv_path}")
    print(f"Aperçus   : {PREVIEW_ROOT}")
    print(f"Mosaïque  : {OUTPUT_ROOT / 'contact_sheet.png'}")
    print(f"Candidats : {len(all_results)}")


if __name__ == "__main__":
    main()
