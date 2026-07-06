from pathlib import Path
from PIL import Image

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/ithmb_tiles_4096")
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    CACHE / "F05" / "T154.ithmb",
    CACHE / "F06" / "T155.ithmb",
    CACHE / "F23" / "T172.ithmb",
]

def save_gray(tile, name):
    # 4092 bytes = proche de 64x64 moins 4 bytes
    w, h = 64, 64
    data = tile[: w * h]
    if len(data) < w * h:
        data += bytes([0]) * (w * h - len(data))
    img = Image.frombytes("L", (w, h), data)
    img.save(OUT / f"{name}.png")

for path in TARGETS:
    raw = path.read_bytes()
    tag = f"{path.parent.name}_{path.stem}"

    print("=" * 80)
    print(path.relative_to(CACHE), "size", len(raw))

    for block_idx, off in enumerate(range(0, len(raw), 4096)):
        block = raw[off:off+4096]
        if len(block) < 16:
            continue

        header = block[:4]
        payload = block[4:]

        if block_idx < 80:
            name = f"{tag}_block_{block_idx:03d}_hdr_{header.hex()}"
            save_gray(payload, name)

        if block_idx < 20:
            print(
                f"block={block_idx:03d} "
                f"off=0x{off:08x} "
                f"header={header.hex(' ')} "
                f"payload_first={payload[:12].hex(' ')}"
            )

print("Sortie:", OUT)
