from pathlib import Path
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

sizes = [
    512,
    768,
    1024,
    1536,
    2048,
    2304,
    3072,
    4096,
    4608,
    6144,
    8192,
]

for target in sorted(CACHE.glob("F*/T*.ithmb")):

    data = target.read_bytes()

    print("=" * 80)
    print(target.relative_to(CACHE), len(data))

    for s in sizes:

        if len(data) % s:
            continue

        headers = Counter()

        for off in range(0, len(data), s):
            headers[data[off:off+8]] += 1

        common = headers.most_common(5)

        print(
            f"record={s:5} "
            f"records={len(data)//s:5} "
            f"unique_headers={len(headers):5}"
        )

        for h, c in common:
            print("   ", h.hex(), c)
