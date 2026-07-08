from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def entropy_simple(chunk):
    if not chunk:
        return 0
    c = Counter(chunk)
    total = len(chunk)
    return len(c), chunk.count(0) / total * 100

def main():
    data = T149.read_bytes()

    print("=" * 120)
    print("T149 MEMORY MAP")
    print("=" * 120)
    print(f"file size: {len(data)}")
    print()

    block_size = 0x100

    print("BLOCK MAP 0x100")
    print("-" * 120)
    print("block_start | zero% | unique_bytes | top_u16")
    print("-" * 120)

    for start in range(0, len(data), block_size):
        end = min(len(data), start + block_size)
        chunk = data[start:end]

        unique_bytes, zero_pct = entropy_simple(chunk)

        vals = []
        for off in range(start, end - 1, 2):
            vals.append(u16le(data, off))

        top = Counter(vals).most_common(5)
        top_txt = " ".join(f"{v:04x}:{n}" for v, n in top)

        print(
            f"0x{start:08x} | "
            f"{zero_pct:6.2f}% | "
            f"{unique_bytes:4d} | "
            f"{top_txt}"
        )

    print()
    print("=" * 120)
    print("KNOWN IMPORTANT ZONES")
    print("=" * 120)

    zones = [
        (0x0000, 0x1f17, "pre-record area"),
        (0x1f17, 0x1f17 + 432 * 24, "432 records x 24"),
        (0x4900, 0x6200, "C referenced table area"),
        (0x7700, 0x9200, "A/B/D/E referenced table area"),
    ]

    for start, end, name in zones:
        chunk = data[start:end]
        unique_bytes, zero_pct = entropy_simple(chunk)

        print()
        print("-" * 120)
        print(f"{name}")
        print(f"range: 0x{start:08x}-0x{end:08x} len={end-start}")
        print(f"zero%={zero_pct:.2f} unique_bytes={unique_bytes}")

        vals = [u16le(data, off) for off in range(start, min(end, len(data)) - 1, 2)]
        for v, n in Counter(vals).most_common(20):
            print(f"  0x{v:04x} {v:5d} count={n}")

if __name__ == "__main__":
    main()
