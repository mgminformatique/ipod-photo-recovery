from pathlib import Path
import struct
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
target = CACHE / "F12" / "T161.ithmb"

records = ITHMBRecordParser(target).find_records()

print("idx,start,u16_00,u8_06,u16_88,u32_88")

for i, r in enumerate(records):
    d = r.data
    print(
        i,
        r.record_start,
        struct.unpack_from("<H", d, 0)[0],
        d[6],
        struct.unpack_from("<H", d, 88)[0],
        struct.unpack_from("<I", d, 88)[0],
    )
