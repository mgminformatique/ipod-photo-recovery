from pathlib import Path
import zlib

SRC = Path("output/T156_object01_active_core.bin")

data = SRC.read_bytes()

OFFSETS = [
    0x6320,
    0x9CE3,
]

print("=" * 100)
print("T156 VALIDATE ZLIB HITS")
print("=" * 100)
print(f"source bytes: {len(data)}")
print()

for offset in OFFSETS:
    chunk = data[offset:]

    print("-" * 100)
    print(f"offset=0x{offset:08x}")
    print(f"first 32 bytes: {chunk[:32].hex(' ')}")

    try:
        obj = zlib.decompressobj()
        decoded = obj.decompress(chunk)
        decoded += obj.flush()

        consumed = len(chunk) - len(obj.unused_data)

        print("result: VALID ZLIB STREAM")
        print(f"decoded bytes: {len(decoded)}")
        print(f"consumed bytes: {consumed}")
        print(f"unused bytes: {len(obj.unused_data)}")
        print(f"eof reached: {obj.eof}")
        print(f"decoded first 64: {decoded[:64].hex(' ')}")

    except zlib.error as error:
        print("result: INVALID ZLIB")
        print(f"error: {error}")

    print()
