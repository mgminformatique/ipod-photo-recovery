from pathlib import Path

ROOT = Path("output/t156_1k_objects")

BYTES_PER_PIXEL = {
    1: "GRAY8 / indexed",
    2: "RGB565 / YUV422 packed",
    3: "RGB888",
    4: "RGBA8888",
}

print("=" * 100)
print("T156 OBJECT SIZE FACTORIZATION")
print("=" * 100)

files = sorted(ROOT.glob("*count_52.bin"))

print(f"complete objects: {len(files)}")
print()

for path in files[:1]:
    size = path.stat().st_size

    print(f"object: {path.name}")
    print(f"bytes: {size}")
    print()

    for bpp, label in BYTES_PER_PIXEL.items():
        if size % bpp != 0:
            continue

        pixels = size // bpp

        print("-" * 100)
        print(f"{bpp} byte(s) per pixel: {label}")
        print(f"pixels={pixels}")
        print("factor pairs:")

        pairs = []

        for width in range(1, int(pixels ** 0.5) + 1):
            if pixels % width == 0:
                height = pixels // width
                pairs.append((width, height))

        for width, height in pairs:
            if width >= 32 and height >= 32:
                ratio = max(width, height) / min(width, height)

                print(
                    f"  {width:4d} x {height:4d} "
                    f"ratio={ratio:.3f}"
                )
