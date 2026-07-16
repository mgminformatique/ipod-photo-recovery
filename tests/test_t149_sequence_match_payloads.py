from pathlib import Path
import struct
import hashlib

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

PAYLOADS = sorted([
    p for p in ROOT.rglob("*.ithmb")
    if p.name >= "T154.ithmb"
])

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def read_table_value(data, block, index):
    off = block + index * 2
    if off + 2 > len(data):
        return None
    return u16(data, off)

def seq_to_bytes(seq):
    out = bytearray()
    for v in seq:
        if v is None:
            continue
        out += struct.pack("<H", v)
    return bytes(out)

def build_sequences(data):
    seqs = []

    for rec in range(COUNT):
        off = START + rec * RECORD_SIZE
        v = [u16(data, off + j) for j in range(0, RECORD_SIZE, 2)]

        tile_id = v[0]
        idx = v[1]

        a_block, a_start = v[2], v[3]
        b_block, b_end = v[4], v[5]

        seq = []
        if a_block == b_block and b_end >= a_start:
            for i in range(a_start, b_end + 1):
                seq.append(read_table_value(data, a_block, i))

        raw = seq_to_bytes(seq)
        if len(raw) >= 8:
            seqs.append({
                "rec": rec,
                "tile": tile_id,
                "idx": idx,
                "block": a_block,
                "start": a_start,
                "end": b_end,
                "seq": seq,
                "raw": raw,
                "sha1": hashlib.sha1(raw).hexdigest()[:12],
            })

    return seqs

def main():
    data = T149.read_bytes()
    seqs = build_sequences(data)

    print("=" * 100)
    print("T149 SEQUENCE MATCH PAYLOADS")
    print("=" * 100)
    print(f"sequences: {len(seqs)}")
    print()

    for s in seqs[:40]:
        print(
            f"rec={s['rec']:03d} tile={s['tile']} idx={s['idx']:3d} "
            f"block=0x{s['block']:04x} range={s['start']}->{s['end']} "
            f"len={len(s['raw']):4d} sha1={s['sha1']}"
        )

    print()
    print("=" * 100)
    print("EXACT MATCHES IN PAYLOADS")
    print("=" * 100)

    total_hits = 0

    for payload in PAYLOADS:
        pdata = payload.read_bytes()
        rel = payload.relative_to(ROOT)

        for s in seqs:
            raw = s["raw"]
            pos = pdata.find(raw)

            if pos != -1:
                total_hits += 1
                print(
                    f"{rel} hit=0x{pos:08x} "
                    f"rec={s['rec']:03d} tile={s['tile']} idx={s['idx']} "
                    f"len={len(raw)} sha1={s['sha1']}"
                )

    print()
    print(f"total exact hits: {total_hits}")

if __name__ == "__main__":
    main()
