from pathlib import Path

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGETS = [
    CACHE / "F05" / "T154.ithmb",
    CACHE / "F06" / "T155.ithmb",
    CACHE / "F23" / "T172.ithmb",
]

sizes = [512, 1024, 2048, 2304, 4096, 4608, 8192, 9216, 14400, 28800, 43200]

for path in TARGETS:
    data = path.read_bytes()
    print("=" * 80)
    print(path.relative_to(CACHE), "size", len(data))

    for rec in sizes:
        best = []

        for start in range(0, min(4096, len(data)), 4):
            remain = len(data) - start
            rem = remain % rec
            count = remain // rec

            if count >= 4:
                best.append((rem, start, count))

        best.sort()

        print(f"record={rec}")
        for rem, start, count in best[:5]:
            print(f"  start=0x{start:04x} count={count} remainder={rem}")
