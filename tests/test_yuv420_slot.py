from pathlib import Path

from core.binary import BinaryFile
from decoder.yuv420_slot import decode_yuv420_slot

bf = BinaryFile("/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb")

out = Path("output/yuv420_slot")
out.mkdir(parents=True, exist_ok=True)

width = 120
height = 120

slot_size = width * height * 2

offsets = [
    0,
    88,
    176,
    264,
    352,
    440,
    528,
    616,
    704,
    792,
    880,
    968,
    1024,
]

orders = ["CbCr", "CrCb"]

for base_offset in offsets:
    for frame_index in range(16):
        frame_offset = base_offset + frame_index * slot_size

        for order in orders:
            img = decode_yuv420_slot(
                bf.data,
                width,
                height,
                offset=frame_offset,
                cbcr_order=order,
            )

            if img is None:
                continue

            img.save(out / f"T113_off{base_offset}_frame{frame_index:02d}_{order}.png")

print("Fait:", out)
