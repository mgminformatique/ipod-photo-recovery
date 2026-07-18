from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

SRC = Path("output/payload_units_136x130")
OUT = Path("output/ranked_stride180")
BEST_OUT = OUT / "best"
CONTACT_OUT = OUT / "contacts"

BEST_OUT.mkdir(parents=True, exist_ok=True)
CONTACT_OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 170
HEIGHT = 80
STRIDE = 180

TOP_PER_UNIT = 5
MIN_START_DISTANCE = 120

CONTACT_COLUMNS = 5
CONTACT_ROWS = 4
CONTACT_PER_SHEET = CONTACT_COLUMNS * CONTACT_ROWS

SCALE = 3
LABEL_HEIGHT = 50


def reconstruct(pixels: np.ndarray, start: int):
    required = start + (HEIGHT - 1) * STRIDE + WIDTH

    if required > len(pixels):
        return None

    image = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)

    for row in range(HEIGHT):
        row_start = start + row * STRIDE
        image[row] = pixels[row_start:row_start + WIDTH]

    return image


def grayscale(image: np.ndarray):
    image_f = image.astype(np.float32)

    return (
        image_f[:, :, 0] * 0.299
        + image_f[:, :, 1] * 0.587
        + image_f[:, :, 2] * 0.114
    )


def score_image(image: np.ndarray):
    gray = grayscale(image)

    horizontal_difference = np.abs(
        gray[:, 1:] - gray[:, :-1]
    )

    vertical_difference = np.abs(
        gray[1:] - gray[:-1]
    )

    horizontal_mean = float(horizontal_difference.mean())
    vertical_mean = float(vertical_difference.mean())

    variance = float(gray.var())
    dynamic_range = float(
        np.percentile(gray, 95)
        - np.percentile(gray, 5)
    )

    # Différence moyenne entre les moyennes de lignes consécutives.
    # Une valeur très élevée indique souvent des bandes horizontales.
    row_means = gray.mean(axis=1)

    row_band_score = float(
        np.abs(row_means[1:] - row_means[:-1]).mean()
    )

    # Variance des gradients : une vraie scène a normalement des
    # contours localisés plutôt qu'un gradient uniforme partout.
    edge_variance = float(
        np.concatenate([
            horizontal_difference.ravel(),
            vertical_difference.ravel(),
        ]).var()
    )

    # Pourcentage de pixels presque uniformes.
    flat_pixels = (
        (horizontal_difference[:, :-1] < 2.0)
        if horizontal_difference.shape[1] > 1
        else horizontal_difference < 2.0
    )

    flat_ratio = float(flat_pixels.mean())

    # Continuité verticale raisonnable :
    # trop élevée = mauvais alignement;
    # trop faible = image vide ou uniforme.
    continuity_penalty = abs(vertical_mean - 8.0)

    # Le score le plus bas gagne.
    score = (
        continuity_penalty * 2.0
        + row_band_score * 1.8
        + abs(horizontal_mean - 7.0) * 0.8
        - min(variance, 2500.0) * 0.003
        - min(dynamic_range, 180.0) * 0.05
        - min(edge_variance, 2500.0) * 0.001
    )

    # Fortes pénalités pour les fenêtres presque vides.
    if variance < 40:
        score += 40

    if dynamic_range < 18:
        score += 30

    if flat_ratio > 0.90:
        score += 20

    return {
        "score": score,
        "horizontal": horizontal_mean,
        "vertical": vertical_mean,
        "variance": variance,
        "range": dynamic_range,
        "bands": row_band_score,
        "flat": flat_ratio,
    }


def make_contact_sheet(entries, sheet_number):
    thumb_width = WIDTH * SCALE
    thumb_height = HEIGHT * SCALE

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
            (x + 4, y + 4),
            entry["label"],
            fill="white",
        )

    output_path = CONTACT_OUT / f"contact_{sheet_number:03d}.jpg"
    sheet.save(output_path, quality=94)

    print(f"contact: {output_path}")


folders = sorted(
    folder
    for folder in SRC.iterdir()
    if folder.is_dir()
)

contact_entries = []
sheet_number = 0
report = []
processed = 0

print("=" * 130)
print("RANK PHOTO WINDOWS — STRIDE 180")
print("=" * 130)
print(f"folders={len(folders)}")
print()

for folder in folders:
    source = folder / "RGB_normal.png"

    if not source.exists():
        continue

    raw = Image.open(source).convert("RGB").tobytes()

    pixels = np.frombuffer(
        raw,
        dtype=np.uint8,
    ).reshape(-1, 3)

    max_start = (
        len(pixels)
        - ((HEIGHT - 1) * STRIDE + WIDTH)
    )

    candidates = []

    # Recherche au pixel près.
    for start in range(max_start + 1):
        image = reconstruct(pixels, start)

        if image is None:
            continue

        stats = score_image(image)

        candidates.append({
            "start": start,
            "image": image.copy(),
            **stats,
        })

    candidates.sort(key=lambda item: item["score"])

    selected = []

    for candidate in candidates:
        # Évite cinq fenêtres pratiquement identiques.
        if any(
            abs(candidate["start"] - previous["start"])
            < MIN_START_DISTANCE
            for previous in selected
        ):
            continue

        selected.append(candidate)

        if len(selected) == TOP_PER_UNIT:
            break

    print(f"unit={processed:03d} {folder.name}")

    for rank, candidate in enumerate(selected, start=1):
        filename = (
            f"{folder.name}_"
            f"rank{rank}_"
            f"start{candidate['start']:04d}_"
            f"score{candidate['score']:.3f}.png"
        )

        output_path = BEST_OUT / filename

        Image.fromarray(
            candidate["image"],
            "RGB",
        ).save(output_path)

        enlarged_path = BEST_OUT / filename.replace(
            ".png",
            "_5x.png",
        )

        Image.fromarray(
            candidate["image"],
            "RGB",
        ).resize(
            (WIDTH * 5, HEIGHT * 5),
            Image.Resampling.NEAREST,
        ).save(enlarged_path)

        label = (
            f"{processed:03d} r{rank} "
            f"start={candidate['start']} "
            f"score={candidate['score']:.1f}\n"
            f"var={candidate['variance']:.0f} "
            f"range={candidate['range']:.0f} "
            f"bands={candidate['bands']:.1f}"
        )

        contact_entries.append({
            "path": output_path,
            "label": label,
        })

        report.append(
            f"unit={processed:03d} "
            f"folder={folder.name} "
            f"rank={rank} "
            f"start={candidate['start']} "
            f"score={candidate['score']:.4f} "
            f"horizontal={candidate['horizontal']:.4f} "
            f"vertical={candidate['vertical']:.4f} "
            f"variance={candidate['variance']:.4f} "
            f"dynamic_range={candidate['range']:.4f} "
            f"bands={candidate['bands']:.4f} "
            f"flat={candidate['flat']:.4f} "
            f"file={output_path}"
        )

        print(
            f"  rank={rank} "
            f"start={candidate['start']:4d} "
            f"score={candidate['score']:8.3f} "
            f"variance={candidate['variance']:8.2f} "
            f"range={candidate['range']:7.2f} "
            f"bands={candidate['bands']:6.2f}"
        )

        if len(contact_entries) == CONTACT_PER_SHEET:
            make_contact_sheet(contact_entries, sheet_number)
            contact_entries = []
            sheet_number += 1

    processed += 1


if contact_entries:
    make_contact_sheet(contact_entries, sheet_number)


report_path = OUT / "report.txt"
report_path.write_text("\n".join(report) + "\n")

print()
print("=" * 130)
print("FINISHED")
print("=" * 130)
print(f"units processed: {processed}")
print(f"best images:     {BEST_OUT}")
print(f"contact sheets:  {CONTACT_OUT}")
print(f"report:          {report_path}")
