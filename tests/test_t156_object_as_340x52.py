from pathlib import Path
from PIL import Image

SRC = Path(
    "output/t156_1k_objects/"
    "object_01_pages_0040-0091_count_52.bin"
)

OUT = Path("output/t156_object_340x52")
OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 340
HEIGHT = 52
BPP = 3

EXPECTED = WIDTH * HEIGHT * BPP

data = SRC.read_bytes()

print("=" * 100)
print("T156 OBJECT AS 340x52 RGB888")
print("=" * 100)
print(f"source bytes: {len(data)}")
print(f"expected:     {EXPECTED}")

if len(data) != EXPECTED:
    raise SystemExit(
        f"Bad size: expected {EXPECTED}, got {len(data)}"
    )

ORDERS = {
    "RGB": (0, 1, 2),
    "RBG": (0, 2, 1),
    "GRB": (1, 0, 2),
    "GBR": (1, 2, 0),
    "BRG": (2, 0, 1),
    "BGR": (2, 1, 0),
}


def reorder_channels(raw: bytes, order):
    converted = bytearray(len(raw))

    for offset in range(0, len(raw), 3):
        pixel = raw[offset:offset + 3]

        converted[offset + 0] = pixel[order[0]]
        converted[offset + 1] = pixel[order[1]]
        converted[offset + 2] = pixel[order[2]]

    return bytes(converted)


for name, order in ORDERS.items():
    converted = reorder_channels(data, order)

    image = Image.frombytes(
        "RGB",
        (WIDTH, HEIGHT),
        converted,
    )

    normal_path = OUT / f"object01_340x52_{name}.png"
    image.save(normal_path)

    reversed_rows = image.transpose(
        Image.Transpose.FLIP_TOP_BOTTOM
    )

    reversed_path = OUT / (
        f"object01_340x52_{name}_rows_reversed.png"
    )
    reversed_rows.save(reversed_path)

    enlarged = image.resize(
        (WIDTH * 3, HEIGHT * 3),
        Image.Resampling.NEAREST,
    )

    enlarged.save(
        OUT / f"object01_340x52_{name}_3x.png"
    )

    print(f"saved: {normal_path}")
    print(f"saved: {reversed_path}")

print()
print(f"results: {OUT}")
