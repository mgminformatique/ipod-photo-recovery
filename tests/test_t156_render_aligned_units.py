from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

ROOT = Path("output/t156_segments")
OUT = Path("output/t156_aligned_units")
OUT.mkdir(parents=True, exist_ok=True)

BLOCK_SIZE = 4092
UNIT_BLOCKS = 13

# Segment 00 est partiel/décalé.
FILES = sorted(ROOT.glob("segment_*.bin"))[1:]

unit_number = 0

for path in FILES:
    data = path.read_bytes()

    blocks = [
        data[off:off + BLOCK_SIZE]
        for off in range(0, len(data), BLOCK_SIZE)
        if len(data[off:off + BLOCK_SIZE]) == BLOCK_SIZE
    ]

    full_units = len(blocks) // UNIT_BLOCKS

    for local_unit in range(full_units):
        unit_blocks = blocks[
            local_unit * UNIT_BLOCKS:
            (local_unit + 1) * UNIT_BLOCKS
        ]

        # Une ligne de 4092 pixels par bloc.
        image = Image.new("L", (BLOCK_SIZE, UNIT_BLOCKS))

        for row, block in enumerate(unit_blocks):
            row_image = Image.frombytes("L", (BLOCK_SIZE, 1), block)
            image.paste(row_image, (0, row))

        # Agrandissement vertical pour rendre les motifs visibles.
        preview = image.resize(
            (1023, UNIT_BLOCKS * 32),
            resample=Image.Resampling.NEAREST
        )
        preview = ImageOps.autocontrast(preview)

        draw = ImageDraw.Draw(preview)
        for row in range(1, UNIT_BLOCKS):
            y = row * 32
            draw.line((0, y, preview.width, y), fill=255)

        name = (
            f"unit_{unit_number:02d}_"
            f"{path.stem}_local_{local_unit:02d}.png"
        )
        preview.save(OUT / name)

        # Extrait également les positions 00–10 sans footer.
        main_data = b"".join(unit_blocks[:11])
        (OUT / name.replace(".png", "_main.bin")).write_bytes(main_data)

        print(
            f"unit={unit_number:02d} "
            f"segment={path.stem} "
            f"local={local_unit:02d} "
            f"main_bytes={len(main_data)}"
        )

        unit_number += 1

print(f"saved {unit_number} aligned units in {OUT}")
