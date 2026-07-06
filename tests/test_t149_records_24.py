from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
FILE = ROOT / "F00" / "T149.ithmb"

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def u32le(b, off):
    return struct.unpack_from("<I", b, off)[0]

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 24-BYTE RECORDS")
    print("=" * 100)

    # zone où on voit tile=2304 répété aux 24 bytes
    start = 0x1f17
    record_size = 24

    # on aligne pour que tile soit au début du record temporairement
    for i in range(80):
        off = start + i * record_size
        chunk = data[off:off+record_size]
        if len(chunk) < record_size:
            break

        vals16 = [u16le(chunk, j) for j in range(0, record_size, 2)]
        vals32 = [u32le(chunk, j) for j in range(0, record_size, 4)]

        print("-" * 100)
        print(f"record #{i} off=0x{off:08x}")
        print("hex:", " ".join(f"{x:02x}" for x in chunk))
        print("u16:", vals16)
        print("u32:", vals32)

if __name__ == "__main__":
    main()
