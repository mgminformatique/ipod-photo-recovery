from pathlib import Path

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
]

guid = "00262001-0002-0010-FBB3-AB02A8125552"
needle = guid.encode("utf-16le")

def hexdump(data, offset, length):
    chunk = data[offset:offset + length]
    for i in range(0, len(chunk), 16):
        part = chunk[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in part)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in part)
        print(f"{offset+i:08x}  {hex_part:<48}  {ascii_part}")

for path in FILES:
    p = Path(path)
    data = p.read_bytes()

    print("=" * 80)
    print(p)
    print("Size:", len(data))

    first = data.find(needle)
    print("First GUID:", first, hex(first))

    record_start = first - 16
    print("Record guess start:", record_start, hex(record_start))
    hexdump(data, record_start, 112)

    print()
