from pathlib import Path

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
db = (CACHE / "Photo Database").read_bytes()

print("Testing XOR relation between Photo Database and .ithmb files")

for f in sorted(CACHE.rglob("*.ithmb")):
    data = f.read_bytes()

    n = min(4096, len(db), len(data))
    x = bytes(db[i] ^ data[i] for i in range(n))

    printable = sum(1 for b in x if 32 <= b <= 126)
    zeros = x.count(0)

    if printable > n * 0.35 or zeros > n * 0.05:
        print(
            f"{f.relative_to(CACHE)} "
            f"printable={printable}/{n} "
            f"zeros={zeros}"
        )

print("done")
