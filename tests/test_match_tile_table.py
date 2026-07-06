from pathlib import Path
import struct
from parser.ithmb_records import ITHMBRecordParser

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TABLE = CACHE / "F00" / "T149.ithmb"
TABLE_START = 0x1f18
TABLE_REC_SIZE = 24
TABLE_COUNT = 400

print("=" * 100)
print("MATCH TILE TABLE")
print("=" * 100)

data = TABLE.read_bytes()

table = {}

for i in range(TABLE_COUNT):
    off = TABLE_START + i * TABLE_REC_SIZE
    chunk = data[off:off + TABLE_REC_SIZE]

    if len(chunk) < TABLE_REC_SIZE:
        break

    tile_id = struct.unpack_from(">H", chunk, 0)[0]

    if 2200 <= tile_id <= 2600:
        fields_be = [struct.unpack_from(">H", chunk, j)[0] for j in range(0, TABLE_REC_SIZE, 2)]
        fields_le = [struct.unpack_from("<H", chunk, j)[0] for j in range(0, TABLE_REC_SIZE, 2)]

        table[tile_id] = {
            "table_index": i,
            "table_off": off,
            "hex": chunk.hex(" "),
            "be": fields_be,
            "le": fields_le,
        }

print("table entries:", len(table))
print("table id range:", min(table), max(table))
print()

matches = []

for p in sorted(CACHE.glob("F*/T*.ithmb")):
    try:
        tnum = int(p.stem[1:])
    except Exception:
        continue

    if not (154 <= tnum <= 174):
        continue

    recs = ITHMBRecordParser(p).find_records()
    if not recs:
        continue

    print("=" * 100)
    print(p.relative_to(CACHE), "records", len(recs))

    for ri, r in enumerate(recs):
        if len(r.data) < 8:
            continue

        record_tile_id = struct.unpack_from("<H", r.data, 6)[0]

        hit = table.get(record_tile_id)

        if hit:
            matches.append((str(p.relative_to(CACHE)), ri, record_tile_id, hit["table_index"], hit["table_off"]))

            print(
                f"record={ri:02d} "
                f"tile_id={record_tile_id} "
                f"table_idx={hit['table_index']:03d} "
                f"table_off=0x{hit['table_off']:06x} "
                f"be={hit['be']}"
            )
        else:
            print(
                f"record={ri:02d} "
                f"tile_id={record_tile_id} "
                f"NO_TABLE_MATCH"
            )

print("=" * 100)
print("TOTAL MATCHES:", len(matches))
print("=" * 100)

for m in matches[:200]:
    print(m)
