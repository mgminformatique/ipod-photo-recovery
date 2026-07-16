from pathlib import Path
import struct

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

START = 0x1f17
RECORD_SIZE = 24
COUNT = 60

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def vals_at(data, off, size=24):
    if off + size > len(data):
        return []
    return [u16(data, off + i) for i in range(0, size, 2)]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 DEREF EXPANDED OFFSETS")
    print("=" * 100)

    for rec in range(COUNT):
        roff = START + rec * RECORD_SIZE
        v = [u16(data, roff + j) for j in range(0, RECORD_SIZE, 2)]

        tile_id, idx = v[0], v[1]
        a_block, a_start = v[2], v[3]
        b_block, b_end = v[4], v[5]

        if a_block != b_block or b_end < a_start:
            continue

        print()
        print("-" * 100)
        print(f"REC {rec:03d} tile={tile_id} idx={idx} range block=0x{a_block:04x} {a_start}->{b_end}")

        for i in range(a_start, b_end + 1):
            ptr = u16(data, a_block + i * 2)

            if ptr == 0 or ptr >= len(data):
                continue

            deref = vals_at(data, ptr, 24)
            print(
                f"  table_idx={i:03d} ptr=0x{ptr:04x} "
                f"deref_u16={deref}"
            )

if __name__ == "__main__":
    main()
