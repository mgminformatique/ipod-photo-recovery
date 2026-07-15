from pathlib import Path
from PIL import Image

SRC = Path("output/T156_object01_active_core.bin")
OUT = Path("output/t156_active_core_bitplanes")
OUT.mkdir(parents=True, exist_ok=True)

WIDTH = 240
HEIGHT = 170

data = SRC.read_bytes()

expected = WIDTH * HEIGHT

if len(data) != expected:
    raise SystemExit(
        f"Bad size: got {len(data)}, expected {expected}"
    )

print("=" * 100)
print("T156 ACTIVE CORE BITPLANES")
print("=" * 100)
print(f"source bytes: {len(data)}")
print(f"dimensions: {WIDTH}x{HEIGHT}")
print()

for bit in range(8):
    pixels = bytes(
        255 if (value >> bit) & 1 else 0
        for value in data
    )

    image = Image.frombytes("L", (WIDTH, HEIGHT), pixels)

    path = OUT / f"bitplane_{bit}.png"
    image.save(path)

    ones = sum((value >> bit) & 1 for value in data)

    print(
        f"bit={bit} "
        f"ones={ones}/{len(data)} "
        f"{ones / len(data) * 100:6.2f}% "
        f"saved={path}"
    )
