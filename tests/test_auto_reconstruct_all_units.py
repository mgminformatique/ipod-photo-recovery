from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

SRC = Path("output/payload_units_136x130")
OUT = Path("output/auto_reconstructed_units")
BEST_OUT = OUT / "best"
CONTACT_OUT = OUT / "contacts"

BEST_OUT.mkdir(parents=True, exist_ok=True)
CONTACT_OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 170
HEIGHT = 80

STRIDES = range(170, 191)

# On avance par pixels dans les marges possibles.
START_OFFSETS = range(0, 4201, 20)

TOP_PER_UNIT = 3

CONTACT_COLUMNS = 4
CONTACT_ROWS = 4
CONTACT_PER_SHEET = CONTACT_COLUMNS * CONTACT_ROWS

SCALE = 3
LABEL_HEIGHT = 44


def vertical_mad(image: np.ndarray) -> float:
    if image.shape[0] < 2:
        return 999999.0

    upper = image[:-1].astype(np.int16)
    lower = image[1:].astype(np.int16)

    return float(np.abs(upper - lower).mean())


def horizontal_mad(image: np.ndarray) -> float:
    if image.shape[1] < 2:
        return 999999.0

    left = image[:, :-1].astype(np.int16)
    right = image[:, 1:].astype(np.int16)

    return float(np.abs(left - right).mean())


def edge_penalty(image: np.ndarray) -> float:
    """
    Pénalise les grosses coupures entre la fin d'une ligne
    et le début de la suivante.
    """
    right_edge = image[:-1, -1].astype(np.int16)
    next_left = image[1:, 0].astype(np.int16)

    return float(np.abs(right_edge - next_left).mean())


def reconstruction_score(image: np.ndarray) -> float:
    vertical = vertical_mad(image)
    horizontal = horizontal_mad(image)
    edges = edge_penalty(image)

    # La continuité verticale est prioritaire.
    return (
        vertical
        + horizontal * 0.20
        + edges * 0.15
    )


def reconstruct(
    pixels: np.ndarray,
    start: int,
    stride: int,
):
    required = start + (HEIGHT - 1) * stride + WIDTH

    if required > len(pixels):
        return None

    result = np.empty(
        (HEIGHT, WIDTH, 3),
        dtype=np.uint8,
    )

    for row in range(HEIGHT):
        row_start = start + row * stride
        row_end = row_start + WIDTH

        result[row] = pixels[row_start:row_end]

    return result


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

    output_path = (
        CONTACT_OUT
        / f"contact_{sheet_number:03d}.jpg"
    )

    sheet.save(output_path, quality=92)

    print(f"contact: {output_path}")


folders = sorted(
    folder
    for folder in SRC.iterdir()
    if folder.is_dir()
)

contact_entries = []
sheet_number = 0
processed = 0

report_lines = []

print("=" * 120)
print("AUTO RECONSTRUCT ALL UNITS")
print("=" * 120)
print(f"folders={len(folders)}")
print()

for folder in folders:
    source = folder / "RGB_normal.png"

    if not source.exists():
        continue

    raw = Image.open(source).convert("RGB").tobytes()

    pixels_rgb = np.frombuffer(
        raw,
        dtype=np.uint8,
    ).reshape(-1, 3)

    channel_variants = {
        "RGB": pixels_rgb,
        "BGR": pixels_rgb[:, [2, 1, 0]],
    }

    candidates = []

    for order_name, pixels in channel_variants.items():
        for stride in STRIDES:
            for start in START_OFFSETS:
                image = reconstruct(
                    pixels,
                    start,
                    stride,
                )

                if image is None:
                    continue

                score = reconstruction_score(image)

                candidates.append({
                    "score": score,
                    "start": start,
                    "stride": stride,
                    "order": order_name,
                    "rotation": 0,
                    "image": image.copy(),
                })

                rotated = np.rot90(image, 2)
                rotated_score = reconstruction_score(rotated)

                candidates.append({
                    "score": rotated_score,
                    "start": start,
                    "stride": stride,
                    "order": order_name,
                    "rotation": 180,
                    "image": rotated.copy(),
                })

    candidates.sort(key=lambda item: item["score"])

    # Évite que les trois meilleurs soient presque identiques.
    selected = []

    for candidate in candidates:
        duplicate = False

        for previous in selected:
            if (
                candidate["order"] == previous["order"]
                and candidate["rotation"] == previous["rotation"]
                and abs(
                    candidate["stride"]
                    - previous["stride"]
                ) <= 1
                and abs(
                    candidate["start"]
                    - previous["start"]
                ) <= 40
            ):
                duplicate = True
                break

        if duplicate:
            continue

        selected.append(candidate)

        if len(selected) == TOP_PER_UNIT:
            break

    for rank, candidate in enumerate(selected, start=1):
        filename = (
            f"{folder.name}_"
            f"rank{rank}_"
            f"{candidate['order']}_"
            f"rot{candidate['rotation']}_"
            f"start{candidate['start']}_"
            f"stride{candidate['stride']}_"
            f"score{candidate['score']:.3f}.png"
        )

        output_path = BEST_OUT / filename

        Image.fromarray(
            candidate["image"],
            "RGB",
        ).save(output_path)

        label = (
            f"{processed:03d} rank{rank} "
            f"{candidate['order']} "
            f"rot={candidate['rotation']} "
            f"start={candidate['start']} "
            f"stride={candidate['stride']}"
        )

        contact_entries.append({
            "path": output_path,
            "label": label,
        })

        report_lines.append(
            f"unit={processed:03d} "
            f"folder={folder.name} "
            f"rank={rank} "
            f"score={candidate['score']:.4f} "
            f"order={candidate['order']} "
            f"rotation={candidate['rotation']} "
            f"start={candidate['start']} "
            f"stride={candidate['stride']} "
            f"file={output_path}"
        )

        if len(contact_entries) == CONTACT_PER_SHEET:
            make_contact_sheet(
                contact_entries,
                sheet_number,
            )

            contact_entries = []
            sheet_number += 1

    best = selected[0]

    print(
        f"unit={processed:03d} "
        f"{folder.name} "
        f"score={best['score']:.3f} "
        f"start={best['start']} "
        f"stride={best['stride']} "
        f"{best['order']} "
        f"rot={best['rotation']}"
    )

    processed += 1


if contact_entries:
    make_contact_sheet(
        contact_entries,
        sheet_number,
    )


report_path = OUT / "report.txt"
report_path.write_text(
    "\n".join(report_lines) + "\n"
)

print()
print("=" * 120)
print("FINISHED")
print("=" * 120)
print(f"units processed: {processed}")
print(f"best images:     {BEST_OUT}")
print(f"contact sheets:  {CONTACT_OUT}")
print(f"report:          {report_path}")
