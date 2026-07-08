from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0xC218

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    refs = []
    for off in range(START, len(data)-1, 2):
        v = u16le(data, off)
        if 0x0800 <= v <= 0x08ff:
            refs.append((off, v))

    print("=" * 100)
    print("T149 08xx REFS")
    print("=" * 100)
    print(f"count: {len(refs)}")
    print()

    for off, v in refs[:300]:
        before = [u16le(data, p) for p in range(max(START, off-12), off, 2)]
        after = [u16le(data, p) for p in range(off+2, min(len(data), off+14), 2)]
        print(
            f"off=0x{off:08x} v=0x{v:04x} "
            f"before={' '.join(f'{x:04x}' for x in before)} "
            f"after={' '.join(f'{x:04x}' for x in after)}"
        )

    print()
    print("TOP 08xx VALUES")
    for v, c in Counter(x for _, x in refs).most_common():
        print(f"0x{v:04x} count={c}")

if __name__ == "__main__":
    main()
