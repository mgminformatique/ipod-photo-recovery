from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from PIL import Image, ImageDraw

SRC = Path("output/payload_units_136x130")
OUT = Path("output/payload_geometry_row_drift")
OUT.mkdir(parents=True, exist_ok=True)

PIXELS = 17680

# Toutes les dimensions RGB888 raisonnables de 17680 pixels.
DIMENSIONS = [
    (34, 520),
    (40, 442),
    (52, 340),
    (65, 272),
    (68, 260),
    (80, 221),
    (85, 208),
    (104, 170),
    (130, 136),
    (136, 130),
    (170, 104),
    (208, 85),
    (221, 80),
    (260, 68),
    (272, 65),
    (340, 52),
    (442, 40),
    (520, 34),
]

MAX_SHIFT = 40
PREVIEW_UNITS = 30


def get_source_images():
    results = []

    for folder in sorted(SRC.iterdir()):
        if not folder.is_dir():
            continue

        image_path = folder / "RGB_normal.png"

        if not image_path.exists():
            continue

        image = Image.open(image_path).convert("RGB")
        data = image.tobytes()

        if len(data) != PIXELS * 3:
            continue

        results.append({
            "name": folder.name,
            "data": data,
        })

    return results


def row_mad(array):
    if array.shape[0] < 2:
        return float("inf")

    left = array[:-1].astype(np.int16)
    right = array[1:].astype(np.int16)

    return float(np.abs(left - right).mean())


def horizontal_mad(array):
    if array.shape[1] < 2:
        return float("inf")

    left = array[:, :-1].astype(np.int16)
    right = array[:, 1:].astype(np.int16)

    return float(np.abs(left - right).mean())


def apply_cumulative_shift(array, shift):
    fixed = np.empty_like(array)

    for row_index in range(array.shape[0]):
        fixed[row_index] = np.roll(
            array[row_index],
            shift * row_index,
            axis=0,
        )

    return fixed


sources = get_source_images()

print("=" * 130)
print("PAYLOAD GEOMETRY AND ROW DRIFT")
print("=" * 130)
print(f"units={len(sources)}")
print()

results = []

for width, height in DIMENSIONS:
    if width * height != PIXELS:
        continue

    raw_vertical_scores = []
    horizontal_scores = []

    best_global_shift = None
    best_global_score = None

    arrays = []

    for source in sources:
        array = np.frombuffer(
            source["data"],
            dtype=np.uint8,
        ).reshape(height, width, 3)

        arrays.append(array)

        raw_vertical_scores.append(row_mad(array))
        horizontal_scores.append(horizontal_mad(array))

    raw_vertical_average = float(
        np.mean(raw_vertical_scores)
    )

    horizontal_average = float(
        np.mean(horizontal_scores)
    )

    shift_scores = {}

    for shift in range(-MAX_SHIFT, MAX_SHIFT + 1):
        scores = []

        for array in arrays:
            fixed = apply_cumulative_shift(array, shift)
            scores.append(row_mad(fixed))

        average_score = float(np.mean(scores))
        shift_scores[shift] = average_score

        if (
            best_global_score is None
            or average_score < best_global_score
        ):
            best_global_score = average_score
            best_global_shift = shift

    improvement = (
        raw_vertical_average - best_global_score
    )

    results.append({
        "width": width,
        "height": height,
        "raw_vertical": raw_vertical_average,
        "horizontal": horizontal_average,
        "shift": best_global_shift,
        "shifted_vertical": best_global_score,
        "improvement": improvement,
        "shift_scores": shift_scores,
    })


results.sort(
    key=lambda row: (
        row["shifted_vertical"],
        row["raw_vertical"],
    )
)

print("=" * 130)
print("GEOMETRY RANKING")
print("=" * 130)

for rank, result in enumerate(results, start=1):
    print(
        f"rank={rank:02d} "
        f"size={result['width']:3d}x{result['height']:3d} "
        f"raw_vertical={result['raw_vertical']:8.3f} "
        f"horizontal={result['horizontal']:8.3f} "
        f"best_shift={result['shift']:+4d} "
        f"shifted_vertical={result['shifted_vertical']:8.3f} "
        f"improvement={result['improvement']:8.3f}"
    )


best = results[0]

print()
print("=" * 130)
print("BEST RESULT")
print("=" * 130)
print(f"size={best['width']}x{best['height']}")
print(f"best cumulative shift={best['shift']:+d} pixels per row")
print(f"raw vertical MAD={best['raw_vertical']:.4f}")
print(f"corrected vertical MAD={best['shifted_vertical']:.4f}")
print(f"improvement={best['improvement']:.4f}")
print()

print("Best shifts for winning geometry:")

for shift, score in sorted(
    best["shift_scores"].items(),
    key=lambda item: item[1],
)[:15]:
    print(
        f"  shift={shift:+4d} "
        f"score={score:8.4f}"
    )


# Génération d’une planche avec la meilleure géométrie.
thumb_width = best["width"] * 2
thumb_height = best["height"] * 2
label_height = 28

columns = 4
rows = (
    min(len(sources), PREVIEW_UNITS)
    + columns - 1
) // columns

contact = Image.new(
    "RGB",
    (
        columns * thumb_width,
        rows * (thumb_height + label_height),
    ),
    "white",
)

for index, source in enumerate(
    sources[:PREVIEW_UNITS]
):
    array = np.frombuffer(
        source["data"],
        dtype=np.uint8,
    ).reshape(
        best["height"],
        best["width"],
        3,
    )

    fixed = apply_cumulative_shift(
        array,
        best["shift"],
    )

    image = Image.fromarray(
        fixed.astype(np.uint8),
        "RGB",
    )

    image = image.resize(
        (thumb_width, thumb_height),
        Image.Resampling.NEAREST,
    )

    cell = Image.new(
        "RGB",
        (
            thumb_width,
            thumb_height + label_height,
        ),
        "white",
    )

    cell.paste(image, (0, label_height))

    draw = ImageDraw.Draw(cell)
    draw.text(
        (4, 5),
        source["name"],
        fill="black",
    )

    x = (index % columns) * thumb_width
    y = (index // columns) * (
        thumb_height + label_height
    )

    contact.paste(cell, (x, y))


contact_path = OUT / (
    f"best_{best['width']}x{best['height']}_"
    f"shift_{best['shift']:+d}_contact.png"
)

contact.save(contact_path)

print()
print(f"saved contact sheet: {contact_path}")
