from pathlib import Path
import struct

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

hits = []

for off in range(0, len(data) - 2):
    v = struct.unpack_from("<H", data, off)[0]
    if v != 0 and v % 2304 == 0:
        hits.append((off, v))

print("mod2304 hits:", len(hits))

for off, v in hits:
    start = max(0, off - 16)
    end = min(len(data), off + 18)
    chunk = data[start:end]

    print("=" * 80)
    print(f"offset=0x{off:08x} value={v}")
    print(chunk.hex(" "))
