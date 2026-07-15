from pathlib import Path
from collections import Counter
import math

SRC = Path(
    "output/t156_1k_objects/"
    "object_01_pages_0040-0091_count_52.bin"
)
OUT = Path("output/T156_object01_active_core.bin")

PAGE_SIZE = 1020
FIRST_ACTIVE = 6
LAST_ACTIVE = 45

raw = SRC.read_bytes()

pages = [
    raw[offset:offset + PAGE_SIZE]
    for offset in range(0, len(raw), PAGE_SIZE)
]

if len(pages) != 52:
    raise SystemExit(f"Expected 52 pages, got {len(pages)}")

core_pages = pages[FIRST_ACTIVE:LAST_ACTIVE + 1]
core = b"".join(core_pages)

OUT.write_bytes(core)

def entropy(data: bytes) -> float:
    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )

print("=" * 100)
print("T156 ACTIVE CORE EXTRACTION")
print("=" * 100)
print(f"source pages:       {len(pages)}")
print(f"active page range:  {FIRST_ACTIVE}-{LAST_ACTIVE}")
print(f"active pages:       {len(core_pages)}")
print(f"active bytes:       {len(core)}")
print(f"entropy:            {entropy(core):.4f}")
print(f"saved:              {OUT}")
print()

print("first 64 bytes:")
print(" ".join(f"{value:02x}" for value in core[:64]))
print()

print("last 64 bytes:")
print(" ".join(f"{value:02x}" for value in core[-64:]))
print()

signatures = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"GIF87a": "GIF87a",
    b"GIF89a": "GIF89a",
    b"BM": "BMP",
    b"\x78\x01": "zlib low",
    b"\x78\x9c": "zlib default",
    b"\x78\xda": "zlib high",
    b"BZh": "bzip2",
    b"\x1f\x8b": "gzip",
    b"\xfd7zXZ\x00": "xz",
}

print("embedded signatures:")

found = False

for signature, name in signatures.items():
    start = 0

    while True:
        index = core.find(signature, start)

        if index < 0:
            break

        found = True
        print(f"  {name:12s} at 0x{index:08x}")
        start = index + 1

if not found:
    print("  none")
