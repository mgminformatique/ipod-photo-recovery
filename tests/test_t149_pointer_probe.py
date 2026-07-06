from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F00" / "T149.ithmb"

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def ascii_preview(data):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in data)

def dump(data, off, size=64):
    chunk = data[off:off+size]
    print(f"0x{off:08x}: " + " ".join(f"{x:02x}" for x in chunk))
    print("ascii:", ascii_preview(chunk))

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 POINTER PROBE")
    print("=" * 100)
    print(f"file size: {len(data)}")
    print()

    refs = set()

    for i in range(COUNT):
        off = START + i * RECORD_SIZE
        chunk = data[off:off + RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        vals = [u16le(chunk, j) for j in range(0, RECORD_SIZE, 2)]

        # fields A/B/C/D/E are pairs:
        # (vals[2],vals[3]), (vals[4],vals[5]), etc.
        for base_idx in [2, 4, 6, 8, 10]:
            base = vals[base_idx]
            sub = vals[base_idx + 1]
            refs.add((base, sub))

    print(f"unique refs: {len(refs)}")
    print()

    bases = sorted(set(base for base, sub in refs))

    print("BASES FOUND")
    print("-" * 100)
    for b in bases:
        subs = sorted(sub for base, sub in refs if base == b)
        print(
            f"base=0x{b:04x} dec={b:5d} "
            f"sub_count={len(subs):3d} "
            f"min_sub={min(subs):3d} max_sub={max(subs):3d} "
            f"first_subs={subs[:20]}"
        )

    print()
    print("=" * 100)
    print("DUMP AT BASE OFFSETS")
    print("=" * 100)

    for b in bases:
        if b < len(data):
            print()
            print("-" * 100)
            print(f"base 0x{b:04x} as file offset")
            dump(data, b, 96)
        else:
            print(f"base 0x{b:04x} outside file")

    print()
    print("=" * 100)
    print("DUMP AT BASE + SUB FOR FIRST REFS")
    print("=" * 100)

    for base, sub in sorted(refs)[:120]:
        off = base + sub
        if off < len(data):
            print()
            print("-" * 100)
            print(f"ref base=0x{base:04x} sub={sub} -> off=0x{off:08x}")
            dump(data, off, 32)

if __name__ == "__main__":
    main()
