from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

def u32le(b, off):
    if off + 4 > len(b):
        return None
    return struct.unpack_from("<I", b, off)[0]

def ascii_preview(data):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in data)

def main():
    data = DB.read_bytes()

    print("=" * 100)
    print("DATABASE SIGNATURE")
    print("=" * 100)
    print(f"size: {len(data)} bytes")
    print()

    print("FIRST 512 BYTES HEX + ASCII")
    print("-" * 100)

    for off in range(0, min(512, len(data)), 16):
        chunk = data[off:off+16]
        hx = " ".join(f"{x:02x}" for x in chunk)
        asc = ascii_preview(chunk)
        print(f"0x{off:08x}: {hx:<48} {asc}")

    print()
    print("=" * 100)
    print("FIRST 64 U32LE VALUES")
    print("=" * 100)

    for off in range(0, 256, 4):
        v = u32le(data, off)
        print(f"0x{off:08x}: {v:10d} 0x{v:08x}")

    print()
    print("=" * 100)
    print("ASCII-LIKE STRINGS")
    print("=" * 100)

    cur = bytearray()
    strings = []

    for i, x in enumerate(data):
        if 32 <= x <= 126:
            cur.append(x)
        else:
            if len(cur) >= 4:
                strings.append((i - len(cur), bytes(cur).decode("ascii", errors="ignore")))
            cur = bytearray()

    for off, s in strings[:200]:
        print(f"0x{off:08x}: {s}")

    print()
    print(f"string count >=4 chars: {len(strings)}")


if __name__ == "__main__":
    main()
