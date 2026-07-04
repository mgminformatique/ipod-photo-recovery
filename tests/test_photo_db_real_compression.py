from pathlib import Path
import zlib, gzip

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
OUT = Path("output/photo_db_real_compression")
OUT.mkdir(parents=True, exist_ok=True)

data = DB.read_bytes()

SIGNATURES = [
    (b"\x78\x01", "zlib_7801", "zlib"),
    (b"\x78\x9c", "zlib_789c", "zlib"),
    (b"\x78\xda", "zlib_78da", "zlib"),
    (b"\x1f\x8b", "gzip", "gzip"),
]

print("REAL COMPRESSION SIGNATURE TEST")
print("DB size:", len(data))

for sig, name, kind in SIGNATURES:
    start = 0
    while True:
        off = data.find(sig, start)
        if off == -1:
            break

        chunk = data[off:]

        print("=" * 80)
        print(f"{name} at 0x{off:x}")

        try:
            if kind == "zlib":
                obj = zlib.decompressobj()
                out = obj.decompress(chunk)
                used = len(chunk) - len(obj.unused_data)
            else:
                out = gzip.decompress(chunk)
                used = "unknown"

            print("OK")
            print("out len:", len(out))
            print("used:", used)
            print("first64:", out[:64].hex(" "))

            out_file = OUT / f"{name}_off_{off:x}_len_{len(out)}.bin"
            out_file.write_bytes(out)

        except Exception as e:
            print("FAILED:", e)

        start = off + 1
