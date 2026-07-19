from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    print("Modules requis : numpy et Pillow")
    print("Installation : sudo apt install python3-numpy python3-pil")
    sys.exit(1)


CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/image_evolution")

# Paramètres provenant de nos meilleurs résultats précédents.
KNOWN_PROFILES = {
    "T149.ithmb": {"mode": "RGB888", "offset": 0, "width": 720},
    "T150.ithmb": {"mode": "RGB888", "offset": 0, "width": 720},
    "T154.ithmb": {"mode": "RGB888", "offset": 128, "width": 240},
    "T155.ithmb": {"mode": "RGB888", "offset": 1024, "width": 480},
    "T156.ithmb": {"mode": "RGB565", "offset": 0, "width": 640},
    "T157.ithmb": {"mode": "RGB888", "offset": 0, "width": 320},
    "T161.ithmb": {"mode": "RGB888", "offset": 32, "width": 480},
    "T170.ithmb": {"mode": "RGB888", "offset": 4096, "width": 480},
    "T173.ithmb": {"mode": "RGB888", "offset": 2048, "width": 480},
}

OFFSET_DELTAS = [
    -1024,
    -512,
    -256,
    -128,
    -64,
    -32,
    -16,
    0,
    16,
    32,
    64,
    128,
    256,
    512,
    1024,
]

WIDTH_DELTAS = [
    -32,
    -16,
    -8,
    -4,
    -2,
    0,
    2,
    4,
    8,
    16,
    32,
]

STRIDE_PADDING = [
    -16,
    -8,
    -4,
    -2,
    0,
    2,
    4,
    8,
    16,
]

TILE_SIZES = [4, 8, 16, 32]

THUMB_WIDTH = 300
THUMB_HEIGHT = 240
LABEL_HEIGHT = 54
CONTACT_COLUMNS = 4


@dataclass
class Candidate:
    category: str
    name: str
    array: np.ndarray
    details: str


def locate_file(filename: str) -> Path | None:
    matches = sorted(CACHE_ROOT.rglob(filename))

    if not matches:
        return None

    return matches[0]


def decode_rgb888(
    data: bytes,
    offset: int,
    channel_order: str = "RGB",
) -> np.ndarray:
    if offset < 0 or offset >= len(data):
        return np.empty((0, 3), dtype=np.uint8)

    raw = data[offset:]
    usable = len(raw) - len(raw) % 3

    if usable <= 0:
        return np.empty((0, 3), dtype=np.uint8)

    pixels = np.frombuffer(
        raw[:usable],
        dtype=np.uint8,
    ).reshape(-1, 3).copy()

    orders = {
        "RGB": [0, 1, 2],
        "RBG": [0, 2, 1],
        "GRB": [1, 0, 2],
        "GBR": [1, 2, 0],
        "BRG": [2, 0, 1],
        "BGR": [2, 1, 0],
    }

    pixels = pixels[:, orders[channel_order]]
    return pixels


def decode_rgb565(
    data: bytes,
    offset: int,
    byte_order: str = "little",
    bgr: bool = False,
) -> np.ndarray:
    if offset < 0 or offset >= len(data):
        return np.empty((0, 3), dtype=np.uint8)

    raw = data[offset:]
    usable = len(raw) - len(raw) % 2

    if usable <= 0:
        return np.empty((0, 3), dtype=np.uint8)

    dtype = "<u2" if byte_order == "little" else ">u2"

    values = np.frombuffer(
        raw[:usable],
        dtype=dtype,
    ).astype(np.uint16)

    red = ((values >> 11) & 0x1F) * 255 // 31
    green = ((values >> 5) & 0x3F) * 255 // 63
    blue = (values & 0x1F) * 255 // 31

    if bgr:
        red, blue = blue, red

    return np.stack(
        [red, green, blue],
        axis=1,
    ).astype(np.uint8)


def decode_pixels(
    data: bytes,
    mode: str,
    offset: int,
) -> np.ndarray:
    if mode == "RGB888":
        return decode_rgb888(data, offset, "RGB")

    if mode == "BGR888":
        return decode_rgb888(data, offset, "BGR")

    if mode == "RGB565":
        return decode_rgb565(
            data,
            offset,
            byte_order="little",
            bgr=False,
        )

    if mode == "BGR565":
        return decode_rgb565(
            data,
            offset,
            byte_order="little",
            bgr=True,
        )

    if mode == "RGB565_BE":
        return decode_rgb565(
            data,
            offset,
            byte_order="big",
            bgr=False,
        )

    raise ValueError(f"Mode inconnu : {mode}")


def raster_from_pixels(
    pixels: np.ndarray,
    width: int,
) -> np.ndarray | None:
    if width <= 0 or len(pixels) < width:
        return None

    height = len(pixels) // width

    if height <= 0:
        return None

    used = width * height

    return pixels[:used].reshape(
        height,
        width,
        3,
    )


def column_major_from_pixels(
    pixels: np.ndarray,
    width: int,
) -> np.ndarray | None:
    if width <= 0 or len(pixels) < width:
        return None

    height = len(pixels) // width

    if height <= 0:
        return None

    used = width * height

    return pixels[:used].reshape(
        width,
        height,
        3,
    ).transpose(1, 0, 2)


def raster_with_stride(
    pixels: np.ndarray,
    visible_width: int,
    stored_width: int,
) -> np.ndarray | None:
    if visible_width <= 0 or stored_width <= 0:
        return None

    if visible_width > stored_width:
        return None

    rows = len(pixels) // stored_width

    if rows <= 0:
        return None

    used = rows * stored_width

    source = pixels[:used].reshape(
        rows,
        stored_width,
        3,
    )

    return source[:, :visible_width, :]


def reverse_alternate_rows(
    image: np.ndarray,
) -> np.ndarray:
    output = image.copy()
    output[1::2] = output[1::2, ::-1]
    return output


def reverse_alternate_columns(
    image: np.ndarray,
) -> np.ndarray:
    output = image.copy()
    output[:, 1::2] = output[::-1, 1::2]
    return output


def swap_row_pairs(
    image: np.ndarray,
) -> np.ndarray:
    output = image.copy()
    limit = image.shape[0] - image.shape[0] % 2

    output[:limit:2] = image[1:limit:2]
    output[1:limit:2] = image[:limit:2]

    return output


def swap_column_pairs(
    image: np.ndarray,
) -> np.ndarray:
    output = image.copy()
    limit = image.shape[1] - image.shape[1] % 2

    output[:, :limit:2] = image[:, 1:limit:2]
    output[:, 1:limit:2] = image[:, :limit:2]

    return output


def even_rows_then_odd(
    image: np.ndarray,
) -> np.ndarray:
    rows = np.concatenate(
        [image[0::2], image[1::2]],
        axis=0,
    )
    return rows


def restore_interlaced_rows(
    image: np.ndarray,
) -> np.ndarray:
    height = image.shape[0]
    first_count = (height + 1) // 2

    first = image[:first_count]
    second = image[first_count:]

    output = np.empty_like(image)
    output[0::2] = first
    output[1::2] = second

    return output


def even_columns_then_odd(
    image: np.ndarray,
) -> np.ndarray:
    columns = np.concatenate(
        [image[:, 0::2], image[:, 1::2]],
        axis=1,
    )
    return columns


def restore_interlaced_columns(
    image: np.ndarray,
) -> np.ndarray:
    width = image.shape[1]
    first_count = (width + 1) // 2

    first = image[:, :first_count]
    second = image[:, first_count:]

    output = np.empty_like(image)
    output[:, 0::2] = first
    output[:, 1::2] = second

    return output


def deinterleave_pixel_groups(
    pixels: np.ndarray,
    group_count: int,
) -> np.ndarray:
    usable = len(pixels) - len(pixels) % group_count

    if usable <= 0:
        return pixels.copy()

    grouped = pixels[:usable].reshape(
        group_count,
        -1,
        3,
    )

    output = grouped.transpose(
        1,
        0,
        2,
    ).reshape(-1, 3)

    if usable < len(pixels):
        output = np.concatenate(
            [output, pixels[usable:]],
            axis=0,
        )

    return output


def tile_positions_raster(
    columns: int,
    rows: int,
) -> list[tuple[int, int]]:
    return [
        (x, y)
        for y in range(rows)
        for x in range(columns)
    ]


def tile_positions_column(
    columns: int,
    rows: int,
) -> list[tuple[int, int]]:
    return [
        (x, y)
        for x in range(columns)
        for y in range(rows)
    ]


def tile_positions_zigzag(
    columns: int,
    rows: int,
) -> list[tuple[int, int]]:
    positions = []

    for y in range(rows):
        xs = range(columns)

        if y % 2:
            xs = reversed(range(columns))

        for x in xs:
            positions.append((x, y))

    return positions


def morton_xy(index: int) -> tuple[int, int]:
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


def tile_positions_morton(
    columns: int,
    rows: int,
) -> list[tuple[int, int]]:
    positions = []
    index = 0
    maximum = 1

    while maximum < max(columns, rows):
        maximum *= 2

    while len(positions) < columns * rows:
        x, y = morton_xy(index)
        index += 1

        if x < columns and y < rows:
            positions.append((x, y))

        if index > maximum * maximum * 4:
            break

    return positions


def reassemble_tiles(
    image: np.ndarray,
    tile_size: int,
    position_builder: Callable[
        [int, int],
        list[tuple[int, int]],
    ],
    rotate_tiles: int = 0,
    flip_tiles_x: bool = False,
    flip_tiles_y: bool = False,
) -> np.ndarray | None:
    height, width, _ = image.shape

    columns = width // tile_size
    rows = height // tile_size

    if columns <= 0 or rows <= 0:
        return None

    cropped_width = columns * tile_size
    cropped_height = rows * tile_size

    cropped = image[
        :cropped_height,
        :cropped_width,
    ]

    source_tiles = []

    for y in range(rows):
        for x in range(columns):
            tile = cropped[
                y * tile_size:(y + 1) * tile_size,
                x * tile_size:(x + 1) * tile_size,
            ].copy()

            if rotate_tiles:
                tile = np.rot90(tile, rotate_tiles)

            if flip_tiles_x:
                tile = tile[:, ::-1]

            if flip_tiles_y:
                tile = tile[::-1]

            source_tiles.append(tile)

    positions = position_builder(columns, rows)

    if len(positions) < len(source_tiles):
        return None

    output = np.zeros_like(cropped)

    for tile, (x, y) in zip(source_tiles, positions):
        output[
            y * tile_size:(y + 1) * tile_size,
            x * tile_size:(x + 1) * tile_size,
        ] = tile

    return output


def add_candidate(
    candidates: list[Candidate],
    category: str,
    name: str,
    array: np.ndarray | None,
    details: str,
) -> None:
    if array is None:
        return

    if array.ndim != 3:
        return

    if array.shape[0] < 2 or array.shape[1] < 2:
        return

    candidates.append(
        Candidate(
            category=category,
            name=name,
            array=array,
            details=details,
        )
    )


def build_candidates(
    data: bytes,
    mode: str,
    base_offset: int,
    base_width: int,
) -> list[Candidate]:
    candidates: list[Candidate] = []

    base_pixels = decode_pixels(
        data,
        mode,
        base_offset,
    )

    base_image = raster_from_pixels(
        base_pixels,
        base_width,
    )

    if base_image is None:
        return candidates

    add_candidate(
        candidates,
        "baseline",
        "00_original",
        base_image,
        f"{mode}, offset={base_offset}, width={base_width}",
    )

    # Transformations simples de l'image de référence.
    direct_transforms = {
        "rotation_90": np.rot90(base_image, 1),
        "rotation_180": np.rot90(base_image, 2),
        "rotation_270": np.rot90(base_image, 3),
        "flip_horizontal": base_image[:, ::-1],
        "flip_vertical": base_image[::-1],
        "transpose": base_image.transpose(1, 0, 2),
        "alternate_rows": reverse_alternate_rows(base_image),
        "alternate_columns": reverse_alternate_columns(base_image),
        "swap_row_pairs": swap_row_pairs(base_image),
        "swap_column_pairs": swap_column_pairs(base_image),
        "even_rows_then_odd": even_rows_then_odd(base_image),
        "restore_interlaced_rows": restore_interlaced_rows(base_image),
        "even_columns_then_odd": even_columns_then_odd(base_image),
        "restore_interlaced_columns": restore_interlaced_columns(base_image),
    }

    for name, image in direct_transforms.items():
        add_candidate(
            candidates,
            "geometry",
            name,
            image,
            f"Transformation géométrique de la référence",
        )

    # Ordre des canaux.
    if mode in {"RGB888", "BGR888"}:
        for order in [
            "RGB",
            "RBG",
            "GRB",
            "GBR",
            "BRG",
            "BGR",
        ]:
            pixels = decode_rgb888(
                data,
                base_offset,
                order,
            )

            image = raster_from_pixels(
                pixels,
                base_width,
            )

            add_candidate(
                candidates,
                "channels",
                f"channel_{order}",
                image,
                f"Canaux={order}",
            )

    # Pixels lus par colonnes.
    column_image = column_major_from_pixels(
        base_pixels,
        base_width,
    )

    add_candidate(
        candidates,
        "pixel_order",
        "column_major",
        column_image,
        "Pixels remplis colonne par colonne",
    )

    # Dé-entrelacement du flux avant le rendu.
    for group_count in [2, 4, 8, 16]:
        deinterleaved = deinterleave_pixel_groups(
            base_pixels,
            group_count,
        )

        image = raster_from_pixels(
            deinterleaved,
            base_width,
        )

        add_candidate(
            candidates,
            "pixel_order",
            f"deinterleave_{group_count}",
            image,
            f"Groupes de pixels={group_count}",
        )

    # Variation de largeur autour de notre meilleur résultat.
    for delta in WIDTH_DELTAS:
        width = base_width + delta

        if width <= 8:
            continue

        image = raster_from_pixels(
            base_pixels,
            width,
        )

        add_candidate(
            candidates,
            "width",
            f"width_{width}",
            image,
            f"Largeur={width}, delta={delta:+d}",
        )

    # Variation contrôlée de l'offset.
    for delta in OFFSET_DELTAS:
        offset = base_offset + delta

        if offset < 0 or offset >= len(data):
            continue

        pixels = decode_pixels(
            data,
            mode,
            offset,
        )

        image = raster_from_pixels(
            pixels,
            base_width,
        )

        add_candidate(
            candidates,
            "offset",
            f"offset_{offset}",
            image,
            f"Offset={offset}, delta={delta:+d}",
        )

    # Variation du stride : largeur visible identique,
    # mais plus ou moins de pixels stockés par rangée.
    for padding in STRIDE_PADDING:
        stored_width = base_width + padding

        if stored_width < base_width:
            # Un stride inférieur n'a du sens qu'en testant
            # cette valeur comme largeur réelle.
            image = raster_from_pixels(
                base_pixels,
                stored_width,
            )
        else:
            image = raster_with_stride(
                base_pixels,
                base_width,
                stored_width,
            )

        add_candidate(
            candidates,
            "stride",
            f"stride_{stored_width}",
            image,
            (
                f"Largeur visible={base_width}, "
                f"largeur stockée={stored_width}"
            ),
        )

    # Réorganisation des blocs.
    tile_orders = {
        "raster": tile_positions_raster,
        "column": tile_positions_column,
        "zigzag": tile_positions_zigzag,
        "morton": tile_positions_morton,
    }

    for tile_size in TILE_SIZES:
        for order_name, builder in tile_orders.items():
            image = reassemble_tiles(
                base_image,
                tile_size,
                builder,
            )

            add_candidate(
                candidates,
                "tiles",
                f"tile_{tile_size}_{order_name}",
                image,
                f"Tuiles={tile_size}x{tile_size}, ordre={order_name}",
            )

        # Quelques variantes intra-tuile ciblées.
        for rotation in [1, 2, 3]:
            image = reassemble_tiles(
                base_image,
                tile_size,
                tile_positions_raster,
                rotate_tiles=rotation,
            )

            add_candidate(
                candidates,
                "tiles_internal",
                f"tile_{tile_size}_rotate_{rotation * 90}",
                image,
                (
                    f"Tuiles={tile_size}x{tile_size}, "
                    f"rotation interne={rotation * 90}°"
                ),
            )

        image = reassemble_tiles(
            base_image,
            tile_size,
            tile_positions_raster,
            flip_tiles_x=True,
        )

        add_candidate(
            candidates,
            "tiles_internal",
            f"tile_{tile_size}_flip_x",
            image,
            f"Tuiles={tile_size}x{tile_size}, miroir horizontal interne",
        )

        image = reassemble_tiles(
            base_image,
            tile_size,
            tile_positions_raster,
            flip_tiles_y=True,
        )

        add_candidate(
            candidates,
            "tiles_internal",
            f"tile_{tile_size}_flip_y",
            image,
            f"Tuiles={tile_size}x{tile_size}, miroir vertical interne",
        )

    return candidates


def sanitize_filename(value: str) -> str:
    allowed = []

    for character in value:
        if character.isalnum() or character in "-_":
            allowed.append(character)
        else:
            allowed.append("_")

    return "".join(allowed)


def save_candidate(
    candidate: Candidate,
    output_directory: Path,
    index: int,
) -> Path:
    category_directory = (
        output_directory
        / sanitize_filename(candidate.category)
    )

    category_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{index:03d}_"
        f"{sanitize_filename(candidate.name)}.png"
    )

    output_path = category_directory / filename

    image = Image.fromarray(
        candidate.array.astype(np.uint8),
        mode="RGB",
    )

    image.save(output_path)
    return output_path


def make_thumbnail(
    candidate: Candidate,
    index: int,
) -> Image.Image:
    source = Image.fromarray(
        candidate.array.astype(np.uint8),
        mode="RGB",
    )

    source = ImageOps.contain(
        source,
        (THUMB_WIDTH - 10, THUMB_HEIGHT - 10),
        Image.Resampling.NEAREST,
    )

    cell = Image.new(
        "RGB",
        (
            THUMB_WIDTH,
            THUMB_HEIGHT + LABEL_HEIGHT,
        ),
        "white",
    )

    x = (THUMB_WIDTH - source.width) // 2
    y = (THUMB_HEIGHT - source.height) // 2
    cell.paste(source, (x, y))

    draw = ImageDraw.Draw(cell)

    title = f"{index:03d} | {candidate.name}"
    details = candidate.details

    if len(title) > 42:
        title = title[:39] + "..."

    if len(details) > 48:
        details = details[:45] + "..."

    draw.text(
        (5, THUMB_HEIGHT + 5),
        title,
        fill="black",
    )

    draw.text(
        (5, THUMB_HEIGHT + 25),
        details,
        fill="black",
    )

    return cell


def create_contact_sheet(
    candidates: list[Candidate],
    output_path: Path,
) -> None:
    if not candidates:
        return

    rows = math.ceil(
        len(candidates) / CONTACT_COLUMNS
    )

    cell_width = THUMB_WIDTH
    cell_height = THUMB_HEIGHT + LABEL_HEIGHT

    sheet = Image.new(
        "RGB",
        (
            CONTACT_COLUMNS * cell_width,
            rows * cell_height,
        ),
        "white",
    )

    for index, candidate in enumerate(candidates):
        thumbnail = make_thumbnail(
            candidate,
            index,
        )

        x = (index % CONTACT_COLUMNS) * cell_width
        y = (index // CONTACT_COLUMNS) * cell_height

        sheet.paste(thumbnail, (x, y))

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sheet.save(output_path)


def create_category_sheets(
    candidates: list[Candidate],
    output_directory: Path,
) -> None:
    categories = sorted(
        {candidate.category for candidate in candidates}
    )

    for category in categories:
        subset = [
            candidate
            for candidate in candidates
            if candidate.category == category
        ]

        output_path = (
            output_directory
            / f"contact_{sanitize_filename(category)}.png"
        )

        create_contact_sheet(
            subset,
            output_path,
        )


def write_manifest(
    candidates: list[Candidate],
    output_path: Path,
) -> None:
    lines = [
        "index\tcategory\tname\twidth\theight\tdetails"
    ]

    for index, candidate in enumerate(candidates):
        height, width, _ = candidate.array.shape

        lines.append(
            "\t".join(
                [
                    str(index),
                    candidate.category,
                    candidate.name,
                    str(width),
                    str(height),
                    candidate.details,
                ]
            )
        )

    output_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Affiche l'évolution d'une reconstruction ITHMB "
            "en appliquant une transformation à la fois."
        )
    )

    parser.add_argument(
        "filename",
        nargs="?",
        default="T154.ithmb",
        help="Nom du fichier, par exemple T154.ithmb",
    )

    parser.add_argument(
        "--mode",
        choices=[
            "RGB888",
            "BGR888",
            "RGB565",
            "BGR565",
            "RGB565_BE",
        ],
        help="Remplace le mode du profil connu",
    )

    parser.add_argument(
        "--offset",
        type=int,
        help="Remplace l'offset du profil connu",
    )

    parser.add_argument(
        "--width",
        type=int,
        help="Remplace la largeur du profil connu",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    filename = args.filename

    if not filename.lower().endswith(".ithmb"):
        filename += ".ithmb"

    profile = KNOWN_PROFILES.get(filename)

    if profile is None:
        if (
            args.mode is None
            or args.offset is None
            or args.width is None
        ):
            print(f"Aucun profil connu pour {filename}.")
            print()
            print(
                "Il faut préciser : "
                "--mode, --offset et --width"
            )
            sys.exit(1)

        profile = {
            "mode": args.mode,
            "offset": args.offset,
            "width": args.width,
        }
    else:
        profile = profile.copy()

        if args.mode is not None:
            profile["mode"] = args.mode

        if args.offset is not None:
            profile["offset"] = args.offset

        if args.width is not None:
            profile["width"] = args.width

    path = locate_file(filename)

    if path is None:
        print(f"Fichier introuvable : {filename}")
        print(f"Recherche effectuée dans : {CACHE_ROOT}")
        sys.exit(1)

    data = path.read_bytes()

    output_directory = (
        OUTPUT_ROOT
        / path.stem
        / (
            f"{profile['mode']}"
            f"__offset_{profile['offset']}"
            f"__width_{profile['width']}"
        )
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print("IMAGE EVOLUTION VIEWER")
    print("=" * 80)
    print(f"Fichier : {path}")
    print(f"Taille  : {len(data):,} octets")
    print(f"Mode    : {profile['mode']}")
    print(f"Offset  : {profile['offset']}")
    print(f"Largeur : {profile['width']}")
    print()

    candidates = build_candidates(
        data=data,
        mode=profile["mode"],
        base_offset=profile["offset"],
        base_width=profile["width"],
    )

    if not candidates:
        print("Aucune reconstruction générée.")
        sys.exit(1)

    for index, candidate in enumerate(candidates):
        output_path = save_candidate(
            candidate,
            output_directory,
            index,
        )

        height, width, _ = candidate.array.shape

        print(
            f"[{index:03d}] "
            f"{candidate.category:16s} "
            f"{candidate.name:32s} "
            f"{width}x{height} "
            f"-> {output_path}"
        )

    full_sheet = output_directory / "contact_all.png"

    create_contact_sheet(
        candidates,
        full_sheet,
    )

    create_category_sheets(
        candidates,
        output_directory,
    )

    manifest_path = output_directory / "manifest.tsv"

    write_manifest(
        candidates,
        manifest_path,
    )

    print()
    print("=" * 80)
    print("TERMINÉ")
    print("=" * 80)
    print(f"Reconstructions : {len(candidates)}")
    print(f"Dossier         : {output_directory}")
    print(f"Mosaïque        : {full_sheet}")
    print(f"Manifeste       : {manifest_path}")
    print()
    print("Les mosaïques séparées par catégorie sont :")
    print(f"  {output_directory}/contact_geometry.png")
    print(f"  {output_directory}/contact_offset.png")
    print(f"  {output_directory}/contact_width.png")
    print(f"  {output_directory}/contact_stride.png")
    print(f"  {output_directory}/contact_tiles.png")


if __name__ == "__main__":
    main()
