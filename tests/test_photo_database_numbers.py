import struct
from pathlib import Path

db_path = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
cache_root = Path("/home/murph/Desktop/iPod Photo Cache")

data = db_path.read_bytes()
ithmb_files = sorted(cache_root.rglob("*.ithmb"))
ithmb_sizes = {f.stat().st_size: f.relative_to(cache_root) for f in ithmb_files}

interesting = {
    88, 120, 130, 176, 220, 240, 320, 480, 720,
    14400, 21600, 22880, 28800, 34320, 43200,
    77440, 115200, 153600, 230400, 345600, 460800, 518400, 691200
}

print("Searching Photo Database numbers...")
print("DB size:", len(data))
print("ITHMB sizes loaded:", len(ithmb_sizes))
print()

hits = []

for off in range(0, len(data) - 4):
    le = struct.unpack_from("<I", data, off)[0]
    be = struct.unpack_from(">I", data, off)[0]

    if le in interesting:
        hits.append((off, "LE", le, "interesting"))

    if be in interesting:
        hits.append((off, "BE", be, "interesting"))

    if le in ithmb_sizes:
        hits.append((off, "LE", le, f"ithmb size {ithmb_sizes[le]}"))

    if be in ithmb_sizes:
        hits.append((off, "BE", be, f"ithmb size {ithmb_sizes[be]}"))

for h in hits[:200]:
    off, endian, value, kind = h
    print(f"offset=0x{off:08x} {endian} value={value} {kind}")

print()
print("Total hits:", len(hits))
