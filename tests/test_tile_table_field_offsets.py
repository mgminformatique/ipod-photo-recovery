from pathlib import Path
import struct

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TABLE = CACHE / "F00" / "T149.ithmb"
TABLE_START = 0x1f18
TABLE_REC_SIZE = 24
TABLE_COUNT = 400

TARGETS = sorted(CACHE.glob("F*/T*.ithmb"))

SCALES = [1, 2, 4, 8, 16, 24, 32, 48, 64, 128, 256, 512, 1024, 2048]

data = TABLE.read_bytes()

entries = []

for i in range(TABLE_COUNT):
    off = TABLE_START + i * TABLE_REC_SIZE
    chunk = data[off:off + TABLE_REC_SIZE]

    if len(chunk) < TABLE_REC_SIZE:
        break

    fields = [struct.unpack_from(">H", chunk, j)[0] for j in range(0, TABLE_REC_SIZE, 2)]
    tile_id = fields[0]

    if 2304 <= tile_id <= 2600:
        entries.append((tile_id, off, fields))

print("=" * 100)
print("TILE TABLE FIELD/OFFSET TEST")
print("=" * 100)
print("entries:", len(entries))

for target in TARGETS:
    size = target.stat().st_size
    rel = target.relative_to(CACHE)

    hits = []

    for tile_id, table_off, fields in entries:
        for field_index, value in enumerate(fields):
            if value == 0:
                continue

            for scale in SCALES:
                calculated = value * scale

                if 0 <= calculated < size:
                    hits.append((tile_id, field_index, value, scale, calculated))

    if not hits:
        continue

    print("=" * 100)
    print(rel, "size", size, "hits", len(hits))

    for tile_id, field_index, value, scale, calculated in hits[:120]:
        print(
            f"tile={tile_id} "
            f"field={field_index} "
            f"value={value} "
            f"scale={scale} "
            f"offset=0x{calculated:06x}"
        )

print("done")
