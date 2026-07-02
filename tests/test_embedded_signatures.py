from pathlib import Path

root = Path("/home/murph/Desktop/iPod Photo Cache")

signatures = {
    "JPEG": b"\xff\xd8\xff",
    "PNG": b"\x89PNG",
    "BMP": b"BM",
    "GIF": b"GIF8",
    "TIFF_LE": b"II*\x00",
    "TIFF_BE": b"MM\x00*",
    "WEBP": b"WEBP",
    "JFIF": b"JFIF",
    "EXIF": b"Exif",
}

for f in sorted(root.rglob("*")):
    if not f.is_file():
        continue

    data = f.read_bytes()
    hits = []

    for name, sig in signatures.items():
        pos = data.find(sig)
        if pos != -1:
            hits.append(f"{name}@{pos}")

    if hits:
        print(f"{f.relative_to(root)} | {f.stat().st_size} bytes | {' '.join(hits)}")
