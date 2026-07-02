import zlib
from pathlib import Path

data = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database").read_bytes()

for offset in range(0, len(data), 16):
    chunk = data[offset:]

    try:
        out = zlib.decompress(chunk, wbits=-15)  # raw deflate
        if len(out) > 100:
            print("RAW DEFLATE OK offset", offset, "size", len(out))
            Path(f"output/photo_db_raw_deflate_{offset}.bin").write_bytes(out)
            break
    except Exception:
        pass

print("done")
