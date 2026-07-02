import zlib
import gzip
from pathlib import Path

data = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database").read_bytes()

starts = [
    7473,
    24299,
    111505,
    113324,
    120692,
    122370,
    78969,
    105264,
]

for start in starts:
    print("=" * 60)
    print("Trying offset:", start)
    chunk = data[start:]

    # zlib
    try:
        out = zlib.decompress(chunk)
        print("ZLIB OK:", len(out), "bytes")
        Path(f"output/photo_db_zlib_{start}.bin").write_bytes(out)
    except Exception as e:
        print("ZLIB failed:", e)

    # gzip
    try:
        out = gzip.decompress(chunk)
        print("GZIP OK:", len(out), "bytes")
        Path(f"output/photo_db_gzip_{start}.bin").write_bytes(out)
    except Exception as e:
        print("GZIP failed:", e)
