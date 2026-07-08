from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0xC218
BLOCK_VALUES = 256
VALUE_SIZE = 2
BLOCK_SIZE = BLOCK_VALUES * VALUE_SIZE

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 EXTRACT LUT")
    print("=" * 100)

    for block_i in range(16):
        start = START + block_i * BLOCK_SIZE
        end = start + BLOCK_SIZE

        if end > len(data):
            break

        vals = [u16le(data, off) for off in range(start, end, 2)]

        print()
        print("-" * 100)
        print(f"BLOCK #{block_i} range=0x{start:08x}-0x{end:08x}")
        print(f"first=0x{vals[0]:04x} last=0x{vals[-1]:04x}")
        print(f"unique={len(set(vals))}")

        expected_seq = all(vals[i] == vals[0] + i for i in range(len(vals)))
        print(f"perfect +1 sequence: {expected_seq}")

        print("first 32:")
        print(" ".join(f"{v:04x}" for v in vals[:32]))

        print("last 32:")
        print(" ".join(f"{v:04x}" for v in vals[-32:]))

        print("index,value,delta first 40:")
        for i, v in enumerate(vals[:40]):
            print(f"{i:03d} 0x{v:04x} delta={v - vals[0]}")

if __name__ == "__main__":
    main()
