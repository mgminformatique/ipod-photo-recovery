from pathlib import Path
import struct

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")
OUT = Path("output/T156_strip1k.bin")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

raw = SRC.read_bytes()
stripped = bytearray()
headers = []

for off in range(0, len(raw), PAGE_SIZE):
    page = raw[off:off + PAGE_SIZE]

    if len(page) != PAGE_SIZE:
        break

    header = struct.unpack(">I", page[:HEADER_SIZE])[0]
    headers.append(header)
    stripped += page[HEADER_SIZE:]

OUT.write_bytes(stripped)

normal_pairs = 0
good_plus1 = 0
marker_headers = []

for index, header in enumerate(headers):
    if header in {0x00000000, 0x0D000000}:
        marker_headers.append((index, header))

    if index == 0:
        continue

    previous = headers[index - 1]

    if previous in {0x00000000, 0x0D000000}:
        continue

    if header in {0x00000000, 0x0D000000}:
        continue

    normal_pairs += 1

    if header == previous + 1:
        good_plus1 += 1

print("=" * 100)
print("T156 STRIP 1K HEADERS")
print("=" * 100)
print(f"raw bytes: {len(raw)}")
print(f"full pages: {len(headers)}")
print(f"stripped bytes: {len(stripped)}")
print(f"remaining bytes: {len(raw) % PAGE_SIZE}")
print()
print(
    f"normal +1 pairs: {good_plus1}/{normal_pairs} "
    f"({good_plus1 / normal_pairs * 100:.2f}%)"
    if normal_pairs
    else "normal +1 pairs: none"
)
print()
print("marker headers:")
for index, value in marker_headers:
    print(
        f"page={index:04d} "
        f"file_offset=0x{index * PAGE_SIZE:08x} "
        f"value=0x{value:08x}"
    )
print()
print(f"saved: {OUT}")
print("first 64 stripped bytes:")
print(" ".join(f"{value:02x}" for value in stripped[:64]))
