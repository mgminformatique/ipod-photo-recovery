from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

TABLE = ROOT / "F07" / "T105.ithmb"
PAYLOAD = ROOT / "F07" / "T156.ithmb"

RECORD_SIZE = 24

def u16le(b, o): return struct.unpack_from("<H", b, o)[0]
def u16be(b, o): return struct.unpack_from(">H", b, o)[0]
def u32le(b, o): return struct.unpack_from("<I", b, o)[0]
def u32be(b, o): return struct.unpack_from(">I", b, o)[0]

def main():
    data = TABLE.read_bytes()
    payload_size = PAYLOAD.stat().st_size

    print("=" * 100)
    print("24-BYTE RECORD STRUCTURE ANALYZER")
    print("=" * 100)
    print(f"table: {TABLE}")
    print(f"table size: {len(data)}")
    print(f"payload: {PAYLOAD}")
    print(f"payload size: {payload_size}")
    print()

    starts = []
    for start in range(24):
        records = (len(data) - start) // RECORD_SIZE
        zero_tail = 0
        repeated = 0
        prev = None

        for i in range(records):
            r = data[start + i*RECORD_SIZE:start + (i+1)*RECORD_SIZE]
            if r[-8:] == b"\x00" * 8:
                zero_tail += 1
            if prev == r:
                repeated += 1
            prev = r

        starts.append((zero_tail, repeated, start, records))

    print("ALIGNMENT CANDIDATES")
    print("-" * 100)
    for zero_tail, repeated, start, records in sorted(starts, reverse=True)[:10]:
        print(f"start={start:2d} records={records:5d} zero_tail={zero_tail:5d} repeated={repeated:5d}")

    best_start = sorted(starts, reverse=True)[0][2]
    records = (len(data) - best_start) // RECORD_SIZE

    print()
    print("=" * 100)
    print(f"BEST START = {best_start}")
    print("=" * 100)

    field_counters = [Counter() for _ in range(12)]

    for i in range(records):
        off = best_start + i * RECORD_SIZE
        for f in range(12):
            field_counters[f][u16le(data, off + f*2)] += 1

    print()
    print("U16 FIELD SUMMARY")
    print("-" * 100)
    for f, c in enumerate(field_counters):
        vals = list(c.keys())
        print(
            f"field{f:02d} unique={len(vals):5d} "
            f"min={min(vals):5d} max={max(vals):5d} "
            f"top={c.most_common(5)}"
        )

    print()
    print("FIRST 80 RECORDS")
    print("-" * 100)

    for i in range(min(records, 80)):
        off = best_start + i * RECORD_SIZE
        raw = data[off:off+RECORD_SIZE]
        u16 = [u16le(raw, j) for j in range(0, 24, 2)]
        u32 = [u32le(raw, j) for j in range(0, 24, 4)]

        offset_like = [
            v for v in u32
            if 0 <= v < payload_size
        ]

        print()
        print(f"rec={i:05d} off=0x{off:08x} raw={raw.hex()}")
        print(f"  u16LE={u16}")
        print(f"  u32LE={u32}")
        print(f"  offset_like_u32={offset_like}")

    print()
    print("FIELD DELTAS FIRST 80")
    print("-" * 100)

    prev = None
    for i in range(min(records, 80)):
        off = best_start + i * RECORD_SIZE
        vals = [u16le(data, off + f*2) for f in range(12)]

        if prev is not None:
            delta = [vals[j] - prev[j] for j in range(12)]
            print(f"rec={i-1:05d}->{i:05d} delta={delta}")

        prev = vals

if __name__ == "__main__":
    main()
