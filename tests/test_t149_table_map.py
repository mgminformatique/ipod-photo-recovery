from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def dump_u16_table(data, start, end, width=8):
    print(f"ZONE 0x{start:08x}-0x{end:08x}")
    print("-" * 100)

    for off in range(start, end, width * 2):
        vals = []
        for p in range(off, min(off + width * 2, end), 2):
            vals.append(u16le(data, p))

        hexvals = " ".join(f"{v:04x}" for v in vals)
        decvals = " ".join(f"{v:5d}" for v in vals)

        print(f"0x{off:08x}: {hexvals:<45} | {decvals}")

def find_runs(data, start, end):
    vals = []
    for off in range(start, end - 1, 2):
        vals.append((off, u16le(data, off)))

    runs = []
    if not vals:
        return runs

    run_start_off, run_start_val = vals[0]
    prev_off, prev_val = vals[0]
    run_len = 1

    for off, v in vals[1:]:
        if v == prev_val + 1:
            run_len += 1
        else:
            if run_len >= 4:
                runs.append((run_start_off, run_start_val, prev_val, run_len))
            run_start_off, run_start_val = off, v
            run_len = 1

        prev_off, prev_val = off, v

    if run_len >= 4:
        runs.append((run_start_off, run_start_val, prev_val, run_len))

    return runs

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 TABLE MAP")
    print("=" * 100)
    print(f"file size: {len(data)}")
    print()

    zones = [
        (0x4900, 0x4b00, "C-table zone"),
        (0x7700, 0x7900, "A/B/D/E index zone"),
        (0x7900, 0x7b00, "next index zone"),
        (0x7b00, 0x7d00, "next index zone"),
    ]

    for start, end, name in zones:
        print()
        print("=" * 100)
        print(name)
        print("=" * 100)

        dump_u16_table(data, start, end, width=8)

        print()
        print("ascending +1 runs:")
        runs = find_runs(data, start, end)
        for off, first, last, ln in runs[:40]:
            print(
                f"off=0x{off:08x} "
                f"{first:04x}->{last:04x} "
                f"dec {first}->{last} "
                f"len={ln}"
            )

        print()
        values = [u16le(data, off) for off in range(start, end - 1, 2)]
        c = Counter(values)

        print("top values:")
        for v, n in c.most_common(20):
            print(f"0x{v:04x} {v:5d} count={n}")

if __name__ == "__main__":
    main()
