from pathlib import Path

from core.binary import BinaryFile
from decoder.ycbcr422_interlaced import decode_interlaced_shared

bf = BinaryFile("/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb")

out = Path("output/ycbcr422_interlaced")
out.mkdir(parents=True, exist_ok=True)

width = 120
height = 120
frame_size = width * height * 2

offsets = [0, 88, 176, 280, 376, 608, 928]
orders = [
    "Y_Cb_Y_Cr",
    "Y_Cr_Y_Cb",
    "Cb_Y_Cr_Y",
    "Cr_Y_Cb_Y",
]

for base_offset in offsets:
    for frame in range(16):
        frame_offset = base_offset + frame * frame_size

        for order in orders:
            img = decode_interlaced_shared(
                bf.data,
                width,
                height,
                offset=frame_offset,
                order=order,
            )

            if img is None:
                continue

            img.save(out / f"T113_off{base_offset}_frame{frame:02d}_{order}.png")

print("Fait:", out)
