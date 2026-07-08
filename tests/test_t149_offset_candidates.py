from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def u32le_pair(a, b):
    return (a << 16) | b

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 OFFSET CANDIDATES")
    print("=" * 100)
    print(f"file size: {len(data)}")
    print()

    candidates = []

    for i in range(COUNT):
        off = START + i * RECORD_SIZE
        chunk = data[off:off+RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        v = [u16le(chunk, j) for j in range(0, RECORD_SIZE, 2)]

        pairs = {
            "A": (v[2], v[3]),
            "B": (v[4], v[5]),
            "C": (v[6], v[7]),
            "D": (v[8], v[9]),
            "E": (v[10], v[11]),
        }

        for name, (base, sub) in pairs.items():
            off1 = base + sub
            off2 = base | sub
            off3 = u32le_pair(base, sub)
            off4 = u32le_pair(sub, base)

            for mode, cand in [
                ("base+sub", off1),
                ("base|sub", off2),
                ("base<<16|sub", off3),
                ("sub<<16|base", off4),
            ]:
                if 0 <= cand < len(data):
                    candidates.append((mode, name, i, cand, base, sub))

    print(f"valid offset candidates inside T149: {len(candidates)}")
    print()

    c = Counter((mode, name) for mode, name, *_ in candidates)
    print("candidate counts by mode/field:")
    for k, n in c.most_common():
        print(f"{k}: {n}")

    print()
    print("=" * 100)
    print("FIRST 200 CANDIDATES")
    print("=" * 100)

    for mode, name, rec_i, cand, base, sub in candidates[:200]:
        preview = data[cand:cand+16]
        print(
            f"rec={rec_i:03d} field={name} mode={mode:14s} "
            f"base=0x{base:04x} sub=0x{sub:04x} "
            f"off=0x{cand:08x} "
            f"preview={preview.hex()}"
        )

if __name__ == "__main__":
    main()
