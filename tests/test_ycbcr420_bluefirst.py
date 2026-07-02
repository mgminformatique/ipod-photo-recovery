from pathlib import Path

from core.binary import BinaryFile
from decoder.ycbcr420_bluefirst import decode_bluefirst_420

bf = BinaryFile("/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb")

out = Path("output/ycbcr420_bluefirst")
out.mkdir(parents=True, exist_ok=True)

width = 120
height = 120

slot_size = width * height * 2

offsets = [0, 88]
orders = [
    "Y_Cb_Cr",
    "Y_Cr_Cb",
    "Cb_Cr_Y",
    "Cr_Cb_Y",
]

for base_offset in offsets:
    for frame in range(16):
        frame_offset = base_offset + frame * slot_size

        for order in orders:
            img = decode_bluefirst_420(
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
