from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def ascii_preview(chunk):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in chunk)

def dump(data, off, size=128):
    print("-" * 100)
    print(f"offset 0x{off:08x}")
    for p in range(off, min(off + size, len(data)), 16):
        chunk = data[p:p+16]
        hx = " ".join(f"{x:02x}" for x in chunk)
        u16 = " ".join(f"{u16le(data, q):04x}" for q in range(p, min(p+16, len(data)-1), 2))
        print(f"0x{p:08x}: {hx:<47} | {u16:<39} | {ascii_preview(chunk)}")

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 FOLLOW POINTER")
    print("=" * 100)
    print(f"file size: {len(data)}")

    offsets = [
        0x4900, 0x4a00, 0x4b00, 0x4c00,
        0x7700, 0x7800, 0x7900, 0x7a00,
        0x7b00, 0x7c00, 0x7d00, 0x7e00,
        0x7f00, 0x8000, 0x8100, 0x8200,
        0x8300, 0x8400,
    ]

    for off in offsets:
        dump(data, off, 128)

if __name__ == "__main__":
    main()
