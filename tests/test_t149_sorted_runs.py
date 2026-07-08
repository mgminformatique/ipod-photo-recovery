from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0x7200

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    vals = [(off, u16le(data, off)) for off in range(START, len(data)-1, 2)]

    print("=" * 100)
    print("T149 SORTED RUNS")
    print("=" * 100)

    run_start_off, run_start_val = vals[0]
    prev_off, prev_val = vals[0]
    run_len = 1

    for off, v in vals[1:]:
        if v >= prev_val:
            run_len += 1
        else:
            if run_len >= 16:
                print(
                    f"off=0x{run_start_off:08x} "
                    f"len={run_len:5d} "
                    f"first=0x{run_start_val:04x} "
                    f"last=0x{prev_val:04x}"
                )
            run_start_off, run_start_val = off, v
            run_len = 1

        prev_off, prev_val = off, v

if __name__ == "__main__":
    main()
