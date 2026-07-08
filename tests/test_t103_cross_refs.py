from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T103 = ROOT / "F05" / "T103.ithmb"

START = 8
RECORD_SIZE = 24

def main():
    t103 = T103.read_bytes()

    records = []
    for off in range(START, len(t103) - RECORD_SIZE, RECORD_SIZE):
        rec = t103[off:off + RECORD_SIZE]
        if rec != b"\x00" * RECORD_SIZE:
            records.append((off, rec))

    c = Counter(rec for _, rec in records)

    important = [rec for rec, count in c.items() if count >= 10]

    print("=" * 100)
    print("T103 CROSS REFS")
    print("=" * 100)
    print(f"T103 records: {len(records)}")
    print(f"unique records: {len(c)}")
    print(f"important records count>=10: {len(important)}")
    print()

    files = sorted([p for p in ROOT.rglob("*") if p.is_file()])

    for target in files:
        data = target.read_bytes()
        rel = target.relative_to(ROOT)

        if target == T103:
            continue

        hits = []

        for rec in important[:500]:
            off = data.find(rec)
            if off != -1:
                hits.append((off, rec))

        if hits:
            print("-" * 100)
            print(f"file: {rel}")
            print(f"hits: {len(hits)}")
            for off, rec in hits[:20]:
                print(f"  off=0x{off:08x} rec={rec.hex()}")

if __name__ == "__main__":
    main()
