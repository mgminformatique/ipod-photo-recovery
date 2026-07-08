from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

T103 = ROOT / "F05" / "T103.ithmb"
T149 = ROOT / "F00" / "T149.ithmb"

RECORD103 = 24
RECORD149 = 24

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def score_alignment(data, size):
    best = None

    for start in range(size):
        c = Counter()

        for off in range(start, len(data) - size, size):
            c[data[off:off+size]] += 1

        repeats = sum(v for v in c.values() if v > 1)

        if best is None or repeats > best[0]:
            best = (repeats, start)

    return best

def main():

    t103 = T103.read_bytes()
    t149 = T149.read_bytes()

    rep103, start103 = score_alignment(t103, RECORD103)
    rep149, start149 = score_alignment(t149, RECORD149)

    print("=" * 100)
    print("T103 vs T149")
    print("=" * 100)

    print()
    print(f"T103 best alignment : {start103}")
    print(f"T149 best alignment : {start149}")

    print()
    print("FIRST 40 RECORDS")
    print("-" * 100)

    for i in range(40):

        o103 = start103 + i * RECORD103
        o149 = start149 + i * RECORD149

        r103 = t103[o103:o103+RECORD103]
        r149 = t149[o149:o149+RECORD149]

        print(
            f"{i:03d} | "
            f"T103={r103.hex()} | "
            f"T149 tile={u16le(r149,0):5d} "
            f"u16={ [u16le(r149,j) for j in range(0,24,2)] }"
        )

if __name__ == "__main__":
    main()
