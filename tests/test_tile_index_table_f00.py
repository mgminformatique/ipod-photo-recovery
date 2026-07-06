from pathlib import Path
import struct

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
p = CACHE / "F00" / "T149.ithmb"
data = p.read_bytes()

START = 0x1f00
REC = 24
COUNT = 80

print("F00/T149 TILE INDEX TABLE?")
print("start", hex(START), "record", REC)

for i in range(COUNT):
    off = START + i * REC
    chunk = data[off:off+REC]
    if len(chunk) < REC:
        break

    u16le = [struct.unpack_from("<H", chunk, j)[0] for j in range(0, REC, 2)]
    u16be = [struct.unpack_from(">H", chunk, j)[0] for j in range(0, REC, 2)]

    print("="*80)
    print(f"rec {i:02d} off=0x{off:06x}")
    print("hex:", chunk.hex(" "))
    print("u16LE:", u16le)
    print("u16BE:", u16be)
