from __future__ import annotations

import csv
import hashlib
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
OUTPUT_ROOT = Path("output/recovered_previews_exhaustive")

RECIPES = [
    {
        "name": "w360_s1084",
        "width": 360,
        "stride": 1084,
        "heights": (480, 360, 320, 270, 240, 180, 160, 135, 120),
    },
    {
        "name": "w180_s544",
        "width": 180,
        "stride": 544,
        "heights": (240, 180, 160, 135, 120, 96, 90, 80, 72, 60),
    },
]

CHANNEL_ORDERS = {
    "rgb": (0, 1, 2),
    "bgr": (2, 1, 0),
}

# Nombre maximal d'alignements d'octets testés précisément par recette.
# On teste d'abord tous les offsets 0..stride-1 sur un échantillon.
PHASE_SAMPLE_ROWS = 160
PHASE_KEEP = 8

# Recherche glissante : chaque image peut commencer à n'importe quelle rangée.
ROW_STEP = 1

# Filtres volontairement permissifs : on préfère garder trop d'images.
MIN_STD = 7.0
MIN_RANGE = 30
MAX_MEAN_ADJACENT_DIFF = 105.0

# Déduplication par miniature perceptuelle.
HASH_SIZE = 16
MAX_HASH_DISTANCE = 10

CONTACT_COLUMNS = 6
CONTACT_THUMB_WIDTH = 170
CONTACT_BATCH = 300


def locate_ithmb_files() -> list[Path]:
    files = sorted(CACHE_ROOT.rglob("*.ithmb"))
    if not files:
        raise FileNotFoundError(f"Aucun .ithmb trouvé sous {CACHE_ROOT}")
    return files


def decode_rows(
    data: bytes,
    width: int,
    stride: int,
    offset: int,
    order: tuple[int, int, int],
) -> np.ndarray:
    if offset < 0 or offset >= len(data):
        return np.empty((0, width, 3), dtype=np.uint8)

    rows = (len(data) - offset) // stride
    if rows <= 0:
        return np.empty((0, width, 3), dtype=np.uint8)

    raw = np.frombuffer(
        data[offset:offset + rows * stride],
        dtype=np.uint8,
    ).reshape(rows, stride)

    pixels = raw[:, :width * 3].reshape(rows, width, 3)
    return pixels[:, :, list(order)].copy()


def phase_score(
    data: bytes,
    width: int,
    stride: int,
    offset: int,
) -> float:
    rows = min(PHASE_SAMPLE_ROWS, (len(data) - offset) // stride)
    if rows < 8:
        return float("inf")

    raw = np.frombuffer(
        data[offset:offset + rows * stride],
        dtype=np.uint8,
    ).reshape(rows, stride)

    px = raw[:, :width * 3].reshape(rows, width, 3).astype(np.int16)

    horizontal = np.mean(np.abs(px[:, 1:] - px[:, :-1]))
    vertical = np.mean(np.abs(px[1:] - px[:-1]))

    # Un alignement correct a généralement plus de continuité.
    return float(horizontal + vertical)


def best_phases(data: bytes, width: int, stride: int) -> list[int]:
    scores = []

    for offset in range(stride):
        score = phase_score(data, width, stride, offset)
        if np.isfinite(score):
            scores.append((score, offset))

    scores.sort()
    selected = []

    # Évite de garder plusieurs offsets presque identiques.
    for score, offset in scores:
        if all(min(abs(offset - old), stride - abs(offset - old)) >= 3 for old in selected):
            selected.append(offset)
        if len(selected) >= PHASE_KEEP:
            break

    return selected


def image_metrics(array: np.ndarray) -> tuple[float, int, float]:
    std = float(np.std(array))
    value_range = int(np.max(array)) - int(np.min(array))

    arr = array.astype(np.int16)
    horizontal = float(np.mean(np.abs(arr[:, 1:] - arr[:, :-1])))
    vertical = float(np.mean(np.abs(arr[1:] - arr[:-1])))
    adjacent = (horizontal + vertical) / 2.0

    return std, value_range, adjacent


def dhash(array: np.ndarray) -> int:
    image = Image.fromarray(array, mode="RGB").convert("L")
    image = image.resize((HASH_SIZE + 1, HASH_SIZE), Image.Resampling.BILINEAR)
    values = np.asarray(image, dtype=np.int16)
    bits = values[:, 1:] > values[:, :-1]

    value = 0
    for bit in bits.ravel():
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def save_jpeg(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array, mode="RGB").save(
        path,
        "JPEG",
        quality=90,
        optimize=True,
    )


def contact_sheet(paths: list[Path], destination: Path) -> None:
    if not paths:
        return

    cells = []

    for path in paths:
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue

        ratio = CONTACT_THUMB_WIDTH / max(1, image.width)
        h = max(1, int(image.height * ratio))
        image.thumbnail((CONTACT_THUMB_WIDTH, h), Image.Resampling.LANCZOS)

        cell = Image.new("RGB", (CONTACT_THUMB_WIDTH, h + 25), "white")
        cell.paste(image, ((CONTACT_THUMB_WIDTH - image.width) // 2, 0))
        ImageDraw.Draw(cell).text((3, h + 5), path.stem[:25], fill="black")
        cells.append(cell)

    if not cells:
        return

    cell_h = max(cell.height for cell in cells)
    rows = (len(cells) + CONTACT_COLUMNS - 1) // CONTACT_COLUMNS
    sheet = Image.new(
        "RGB",
        (CONTACT_COLUMNS * CONTACT_THUMB_WIDTH, rows * cell_h),
        "white",
    )

    for index, cell in enumerate(cells):
        x = (index % CONTACT_COLUMNS) * CONTACT_THUMB_WIDTH
        y = (index // CONTACT_COLUMNS) * cell_h
        sheet.paste(cell, (x, y))

    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, "JPEG", quality=88)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    files = locate_ithmb_files()

    accepted_hashes: list[int] = []
    records: list[dict] = []
    saved_paths: list[Path] = []

    print("=" * 105)
    print("RÉCUPÉRATION EXHAUSTIVE DES APERÇUS ITHMB")
    print("=" * 105)
    print(f"Fichiers : {len(files)}")
    print("Chaque rangée de départ est testée; cette analyse peut être longue.")
    print()

    for file_no, path in enumerate(files, 1):
        data = path.read_bytes()
        relative = path.relative_to(CACHE_ROOT)
        label = f"{path.parent.name}_{path.stem}"

        print(f"[{file_no:02d}/{len(files):02d}] {relative} ({len(data):,} octets)")

        for recipe in RECIPES:
            width = recipe["width"]
            stride = recipe["stride"]
            phases = best_phases(data, width, stride)

            print(f"    {recipe['name']} phases={phases}")

            for phase in phases:
                for channel_name, order in CHANNEL_ORDERS.items():
                    decoded = decode_rows(data, width, stride, phase, order)
                    total_rows = len(decoded)

                    for height in recipe["heights"]:
                        if total_rows < height:
                            continue

                        # Toutes les positions possibles, pas uniquement des blocs
                        # non chevauchants depuis le début du fichier.
                        for start_row in range(0, total_rows - height + 1, ROW_STEP):
                            image = decoded[start_row:start_row + height]
                            std, value_range, adjacent = image_metrics(image)

                            if std < MIN_STD:
                                continue
                            if value_range < MIN_RANGE:
                                continue
                            if adjacent > MAX_MEAN_ADJACENT_DIFF:
                                continue

                            image_hash = dhash(image)

                            duplicate = False
                            for old_hash in accepted_hashes:
                                if hamming(image_hash, old_hash) <= MAX_HASH_DISTANCE:
                                    duplicate = True
                                    break

                            if duplicate:
                                continue

                            accepted_hashes.append(image_hash)

                            number = len(records) + 1
                            output_path = (
                                OUTPUT_ROOT
                                / "images"
                                / f"{number:06d}_{label}_{recipe['name']}"
                                  f"_p{phase}_{channel_name}_r{start_row}_h{height}.jpg"
                            )
                            save_jpeg(image, output_path)
                            saved_paths.append(output_path)

                            records.append(
                                {
                                    "number": number,
                                    "source": str(relative),
                                    "recipe": recipe["name"],
                                    "width": width,
                                    "height": height,
                                    "stride": stride,
                                    "phase": phase,
                                    "channel": channel_name,
                                    "start_row": start_row,
                                    "std": f"{std:.5f}",
                                    "range": value_range,
                                    "adjacent_diff": f"{adjacent:.5f}",
                                    "dhash": f"{image_hash:0{HASH_SIZE * HASH_SIZE // 4}x}",
                                    "output": str(output_path),
                                }
                            )

                            if number % 100 == 0:
                                print(f"      images distinctes sauvegardées : {number}")

    csv_path = OUTPUT_ROOT / "index.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "number", "source", "recipe", "width", "height", "stride",
            "phase", "channel", "start_row", "std", "range",
            "adjacent_diff", "dhash", "output",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    # Planches de 300 images pour pouvoir parcourir des milliers de résultats.
    contact_dir = OUTPUT_ROOT / "contacts"
    for batch_start in range(0, len(saved_paths), CONTACT_BATCH):
        batch = saved_paths[batch_start:batch_start + CONTACT_BATCH]
        first = batch_start + 1
        last = batch_start + len(batch)
        contact_sheet(
            batch,
            contact_dir / f"CONTACT_{first:06d}-{last:06d}.jpg",
        )

    summary = OUTPUT_ROOT / "summary.txt"
    summary.write_text(
        "\n".join(
            [
                "=" * 105,
                "RÉCUPÉRATION EXHAUSTIVE DES APERÇUS ITHMB",
                "=" * 105,
                "",
                f"Fichiers analysés       : {len(files)}",
                f"Images distinctes       : {len(records)}",
                f"Index                    : {csv_path}",
                f"Planches-contact        : {contact_dir}",
                "",
                "Première planche :",
                f"{contact_dir / 'CONTACT_000001-000300.jpg'}",
            ]
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 105)
    print("TERMINÉ")
    print("=" * 105)
    print(f"Images distinctes : {len(records)}")
    print(f"Index             : {csv_path}")
    print(f"Contacts          : {contact_dir}")
    print()
    print("Ouvre la première planche avec :")
    print(
        f"  xdg-open "
        f"{contact_dir / 'CONTACT_000001-000300.jpg'}"
    )


if __name__ == "__main__":
    main()
