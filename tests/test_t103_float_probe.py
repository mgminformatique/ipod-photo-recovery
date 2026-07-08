from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F05" / "T103.ithmb"

START = 8
RECORD_SIZE = 24

def f32(b, off):
    return struct.unpack_from("<f", b, off)[0]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T103 FLOAT PROBE")
    print("=" * 100)

    for i in range(80):
        off = START + i * RECORD_SIZE
        chunk = data[off:off+RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        floats = [f32(chunk, j) for j in range(0, 24, 4)]

        print(
            f"#{i:04d} off=0x{off:08x} "
            f"floats={['%.6f' % x for x in floats]} "
            f"hex={chunk.hex()}"
        )

if __name__ == "__main__":
    main()
