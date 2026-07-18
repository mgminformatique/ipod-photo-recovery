from pathlib import Path
import csv

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/file_signature_scan")
OUT.mkdir(parents=True, exist_ok=True)

SIGNATURES = {
    b"\xff\xd8\xff": "JPEG",
    b"JFIF": "JFIF",
    b"Exif": "EXIF",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"GIF87a": "GIF87a",
    b"GIF89a": "GIF89a",
    b"BM": "BMP",
    b"II\x2a\x00": "TIFF_LE",
    b"MM\x00\x2a": "TIFF_BE",
    b"\x78\x01": "ZLIB_01",
    b"\x78\x9c": "ZLIB_9C",
    b"\x78\xda": "ZLIB_DA",
    b"ftyp": "MP4_FTYP",
    b"RIFF": "RIFF",
    b"PK\x03\x04": "ZIP",
}

rows = []

for path in sorted(ROOT.rglob("*.ithmb")):
    data = path.read_bytes()

    for sig, name in SIGNATURES.items():
        start = 0

        while True:
            pos = data.find(sig, start)

            if pos == -1:
                break

            rows.append({
                "file": str(path),
                "signature": name,
                "offset": pos
            })

            start = pos + 1

csv_path = OUT / "signatures.csv"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["file","signature","offset"]
    )
    writer.writeheader()
    writer.writerows(rows)

print("="*80)
print("SIGNATURES TROUVÉES")
print("="*80)

for row in rows:
    print(
        f"{row['signature']:<10} "
        f"{row['offset']:10d} "
        f"{Path(row['file']).name}"
    )

print()
print("Total:", len(rows))
print(csv_path)
