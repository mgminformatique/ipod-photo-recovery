from pathlib import Path
import struct

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def read_table_value(data, block, index):
    off = block + index * 2
    if off + 2 > len(data):
        return None
    return u16(data, off)

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 RESOLVE RECORD RANGES")
    print("=" * 100)

    for rec in range(COUNT):
        off = START + rec * RECORD_SIZE
        v = [u16(data, off + j) for j in range(0, RECORD_SIZE, 2)]

        tile_id = v[0]
        idx = v[1]

        a_block, a_start = v[2], v[3]
        b_block, b_end   = v[4], v[5]
        c_block, c_idx   = v[6], v[7]
        d_block, d_idx   = v[8], v[9]
        e_block, e_idx   = v[10], v[11]

        if rec < 160:
            print()
            print(f"REC {rec:03d} tile={tile_id} idx={idx} off=0x{off:08x}")
            print(f"  A range: block=0x{a_block:04x} start={a_start} end={b_end}")

            vals = []
            if a_block == b_block and b_end >= a_start:
                for i in range(a_start, b_end + 1):
                    val = read_table_value(data, a_block, i)
                    vals.append(val)

            print("  expanded:")
            print("   " + " ".join("----" if x is None else f"{x:04x}" for x in vals[:80]))

            print(f"  C: block=0x{c_block:04x} idx={c_idx} val={read_table_value(data, c_block, c_idx)}")
            print(f"  D: block=0x{d_block:04x} idx={d_idx} val={read_table_value(data, d_block, d_idx)}")
            print(f"  E: block=0x{e_block:04x} idx={e_idx} val={read_table_value(data, e_block, e_idx)}")

if __name__ == "__main__":
    main()
