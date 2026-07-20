from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError:
    print("Modules requis : numpy et Pillow")
    print("Installation : sudo apt install python3-numpy python3-pil")
    sys.exit(1)


CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/recovered_photos_quick")

# Recettes qui ressortent de l'analyse :
# 360 RGB888 = 1080 octets + 4 padding = stride 1084
# 180 RGB888 =  540 octets + 4 padding = stride  544
RECIPES = [
    {
        "name": "w360_stride1084",
        "width": 360,
        "stride": 1084,
        "heights": [480, 360, 320, 270, 240],
    },
    {
        "name": "w180_stride544",
        "width": 180,
        "stride": 544,
        "heights": [240, 180, 160, 135, 120],
    },
]

# On essaie seulement les deux ordres les plus utiles.
CHANNEL_ORDERS = {
    "rgb": (0, 1, 2),
    "bgr": (2, 1, 0),
}

# Décalages possibles au début du fichier.
START_OFFSETS = [0, 4]

# Évite de sauvegarder des blocs presque uniformes.
MIN_STD = 8.0
MIN_RANGE = 35

CONTACT_COLUMNS = 5
CONTACT_THUMB_WIDTH = 180
MAX_CONTACT_IMAGES = 500


def locate_ithmb_files() -> list[Path]:
    files = sorted(CACHE_ROOT.rglob("*.ithmb"))
    if not files:
        raise FileNotFoundError(
            f"Aucun fichier .ithmb trouvé sous {CACHE_ROOT}"
        )
    return files


def decode_rows(
    data: bytes,
    width: int,
    stride: int,
    start_offset: int,
    channel_order: tuple[int, int, int],
) -> np.ndarray:
    if start_offset >= len(data):
        return np.empty((0, width, 3), dtype=np.uint8)

    row_count = (len(data) - start_offset) // stride
    if row_count <= 0:
        return np.empty((0, width, 3), dtype=np.uint8)

    usable = data[
        start_offset:
        start_offset + row_count * stride
    ]

    raw = np.frombuffer(usable, dtype=np.uint8)
    rows = raw.reshape(row_count, stride)

    pixel_bytes = rows[:, : width * 3]
    pixels = pixel_bytes.reshape(row_count, width, 3)

    return pixels[:, :, list(channel_order)].copy()


def visual_score(image: np.ndarray) -> tuple[float, float, int]:
    if image.size == 0:
        return 0.0, 0.0, 0

    std = float(np.std(image))
    value_range = int(np.max(image)) - int(np.min(image))

    # Continuité entre pixels voisins.
    horizontal = np.mean(
        np.abs(
            image[:, 1:, :].astype(np.int16)
            - image[:, :-1, :].astype(np.int16)
        )
    )

    vertical = np.mean(
        np.abs(
            image[1:, :, :].astype(np.int16)
            - image[:-1, :, :].astype(np.int16)
        )
    )

    continuity = 255.0 - float((horizontal + vertical) / 2.0)
    score = std + continuity * 0.20

    return score, std, value_range


def save_image(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array, mode="RGB").save(
        path,
        format="JPEG",
        quality=92,
        optimize=True,
    )


def make_contact_sheet(
    image_paths: list[Path],
    output_path: Path,
    columns: int = CONTACT_COLUMNS,
) -> None:
    if not image_paths:
        return

    selected = image_paths[:MAX_CONTACT_IMAGES]
    thumbs = []

    for path in selected:
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue

        ratio = CONTACT_THUMB_WIDTH / max(1, image.width)
        thumb_height = max(1, int(image.height * ratio))

        image.thumbnail(
            (CONTACT_THUMB_WIDTH, thumb_height),
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new(
            "RGB",
            (CONTACT_THUMB_WIDTH, thumb_height + 28),
            "white",
        )

        x = (CONTACT_THUMB_WIDTH - image.width) // 2
        canvas.paste(image, (x, 0))

        draw = ImageDraw.Draw(canvas)
        label = path.stem[:28]
        draw.text((4, thumb_height + 6), label, fill="black")

        thumbs.append(canvas)

    if not thumbs:
        return

    cell_width = max(image.width for image in thumbs)
    cell_height = max(image.height for image in thumbs)
    rows = (len(thumbs) + columns - 1) // columns

    sheet = Image.new(
        "RGB",
        (columns * cell_width, rows * cell_height),
        "white",
    )

    for index, image in enumerate(thumbs):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        sheet.paste(image, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="JPEG", quality=90)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    ithmb_files = locate_ithmb_files()

    rows_csv = []
    all_saved_paths = []

    print("=" * 100)
    print("RÉCUPÉRATION RAPIDE DES PHOTOS ITHMB")
    print("=" * 100)
    print(f"Fichiers .ithmb : {len(ithmb_files)}")
    print(f"Sortie          : {OUTPUT_ROOT}")
    print()

    for file_index, path in enumerate(ithmb_files, start=1):
        data = path.read_bytes()
        relative = path.relative_to(CACHE_ROOT)
        file_label = f"{path.parent.name}_{path.stem}"

        print(
            f"[{file_index:02d}/{len(ithmb_files):02d}] "
            f"{relative} ({len(data):,} octets)"
        )

        for recipe in RECIPES:
            width = int(recipe["width"])
            stride = int(recipe["stride"])

            for start_offset in START_OFFSETS:
                for channel_name, channel_order in CHANNEL_ORDERS.items():
                    decoded = decode_rows(
                        data=data,
                        width=width,
                        stride=stride,
                        start_offset=start_offset,
                        channel_order=channel_order,
                    )

                    if len(decoded) == 0:
                        continue

                    for height in recipe["heights"]:
                        image_count = len(decoded) // height
                        if image_count == 0:
                            continue

                        group_paths = []

                        group_dir = (
                            OUTPUT_ROOT
                            / recipe["name"]
                            / f"offset_{start_offset}"
                            / channel_name
                            / file_label
                            / f"h{height}"
                        )

                        for image_index in range(image_count):
                            start_row = image_index * height
                            end_row = start_row + height
                            image_array = decoded[start_row:end_row]

                            score, std, value_range = visual_score(image_array)

                            if std < MIN_STD or value_range < MIN_RANGE:
                                continue

                            filename = (
                                f"{file_label}"
                                f"_img_{image_index:04d}"
                                f"_rows_{start_row:06d}-{end_row:06d}"
                                f".jpg"
                            )

                            output_path = group_dir / filename
                            save_image(image_array, output_path)

                            group_paths.append(output_path)
                            all_saved_paths.append(output_path)

                            rows_csv.append(
                                {
                                    "source": str(relative),
                                    "recipe": recipe["name"],
                                    "width": width,
                                    "height": height,
                                    "stride": stride,
                                    "start_offset": start_offset,
                                    "channel_order": channel_name,
                                    "image_index": image_index,
                                    "start_row": start_row,
                                    "end_row": end_row,
                                    "score": f"{score:.6f}",
                                    "std": f"{std:.6f}",
                                    "range": value_range,
                                    "output": str(output_path),
                                }
                            )

                        if group_paths:
                            contact_path = (
                                group_dir
                                / f"CONTACT_{file_label}_{recipe['name']}"
                                  f"_off{start_offset}_{channel_name}_h{height}.jpg"
                            )
                            make_contact_sheet(group_paths, contact_path)

    rows_csv.sort(
        key=lambda row: float(row["score"]),
        reverse=True,
    )

    csv_path = OUTPUT_ROOT / "recovered_index.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "source",
            "recipe",
            "width",
            "height",
            "stride",
            "start_offset",
            "channel_order",
            "image_index",
            "start_row",
            "end_row",
            "score",
            "std",
            "range",
            "output",
        ]

        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_csv)

    # Une planche globale des meilleurs résultats.
    best_paths = [
        Path(row["output"])
        for row in rows_csv[:300]
    ]

    make_contact_sheet(
        best_paths,
        OUTPUT_ROOT / "BEST_300_CONTACT.jpg",
    )

    summary_path = OUTPUT_ROOT / "summary.txt"

    with summary_path.open("w", encoding="utf-8") as report:
        report.write("=" * 100 + "\n")
        report.write("RÉCUPÉRATION RAPIDE DES PHOTOS ITHMB\n")
        report.write("=" * 100 + "\n\n")
        report.write(f"Fichiers analysés : {len(ithmb_files)}\n")
        report.write(f"Images sauvegardées : {len(rows_csv)}\n")
        report.write(f"Index CSV : {csv_path}\n")
        report.write(
            f"Planche principale : "
            f"{OUTPUT_ROOT / 'BEST_300_CONTACT.jpg'}\n\n"
        )

        report.write("MEILLEURS RÉSULTATS\n")
        report.write("-" * 100 + "\n")

        for row in rows_csv[:100]:
            report.write(
                f"score={row['score']} | "
                f"{row['source']} | "
                f"{row['recipe']} | "
                f"h={row['height']} | "
                f"offset={row['start_offset']} | "
                f"{row['channel_order']} | "
                f"{row['output']}\n"
            )

    print()
    print("=" * 100)
    print("TERMINÉ")
    print("=" * 100)
    print(f"Images sauvegardées : {len(rows_csv)}")
    print(f"Planche principale  : {OUTPUT_ROOT / 'BEST_300_CONTACT.jpg'}")
    print(f"Résumé              : {summary_path}")
    print()
    print("Ouvre d'abord :")
    print(f"  xdg-open {OUTPUT_ROOT / 'BEST_300_CONTACT.jpg'}")


if __name__ == "__main__":
    main()
