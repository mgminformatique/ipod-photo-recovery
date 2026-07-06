from pathlib import Path
import struct

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    CACHE/"F05"/"T154.ithmb",
    CACHE/"F06"/"T155.ithmb",
    CACHE/"F07"/"T156.ithmb",
    CACHE/"F09"/"T158.ithmb",
    CACHE/"F23"/"T172.ithmb",
]

print("="*100)
print("RECORD LAYOUT SCAN")
print("="*100)

for path in FILES:

    data = path.read_bytes()

    print("="*100)
    print(path.relative_to(CACHE))

    for rec_size in (32,40,48,56,64,72,80,96,112,128):

        print(f"\nrecord size {rec_size}")

        for rec in range(min(8, len(data)//rec_size)):

            off = rec*rec_size

            words = []

            for i in range(0,rec_size,4):

                v = struct.unpack_from("<I",data,off+i)[0]
                words.append(v)

            print(f"{rec:02d} 0x{off:06x} :",end=" ")

            print(" ".join(f"{x:08x}" for x in words))
