from pathlib import Path
import struct

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
]

guid = "00262001-0002-0010-FBB3-AB02A8125552"
needle = guid.encode("utf-16le")

for path in FILES:
    p = Path(path)
    data = p.read_bytes()

    print("=" * 80)
    print(p.name)

    pos = 0
    while True:
        idx = data.find(needle, pos)
        if idx == -1:
            break

        record_start = idx - 16
        record = data[record_start:record_start + 112]

        print()
        print("record_start:", record_start, hex(record_start))

        for off in range(0, 112, 4):
            val = struct.unpack_from("<I", record, off)[0]
            print(f"  +{off:02d} u32={val}")

        pos = idx + 2
