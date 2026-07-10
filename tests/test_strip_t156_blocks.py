from pathlib import Path

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")
OUT = Path("output/T156_stripped.bin")

data = SRC.read_bytes()
out = bytearray()

for off in range(0, len(data), 0x1000):
    block = data[off:off+0x1000]
    if len(block) <= 4:
        continue
    out += block[4:]

OUT.write_bytes(out)

print(f"raw={len(data)} stripped={len(out)} saved={OUT}")
print("first 64 stripped:")
print(" ".join(f"{b:02x}" for b in out[:64]))
