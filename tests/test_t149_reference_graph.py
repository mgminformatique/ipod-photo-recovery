from pathlib import Path
import struct
from collections import Counter, defaultdict

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
T149 = ROOT / "F00" / "T149.ithmb"

START = 0x1f17
RECORD_SIZE = 24
COUNT = 432

def u16le(b, off):
    return struct.unpack_from("<H", b, off)[0]

def read_u16_at(data, off):
    if off + 2 > len(data):
        return None
    return u16le(data, off)

def main():
    data = T149.read_bytes()

    print("=" * 100)
    print("T149 REFERENCE GRAPH")
    print("=" * 100)
    print(f"file size: {len(data)}")
    print()

    ref_counts = Counter()
    field_counts = defaultdict(Counter)

    print("FIRST 120 RECORD REFERENCES")
    print("-" * 100)

    for i in range(COUNT):
        off = START + i * RECORD_SIZE
        chunk = data[off:off + RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        v = [u16le(chunk, j) for j in range(0, RECORD_SIZE, 2)]

        tile_id = v[0]
        idx = v[1]

        fields = {
            "A": (v[2], v[3]),
            "B": (v[4], v[5]),
            "C": (v[6], v[7]),
            "D": (v[8], v[9]),
            "E": (v[10], v[11]),
        }

        resolved = {}

        for name, (base, sub) in fields.items():
            ptr = base + sub
            val = read_u16_at(data, ptr)
            resolved[name] = (base, sub, ptr, val)

            ref_counts[(base, sub, ptr, val)] += 1
            field_counts[name][(base, sub, ptr, val)] += 1

        if i < 120:
            print()
            print(f"record #{i:03d} off=0x{off:08x} tile={tile_id} idx={idx}")
            for name in ["A", "B", "C", "D", "E"]:
                base, sub, ptr, val = resolved[name]
                print(
                    f"  {name}: base=0x{base:04x} sub=0x{sub:04x} "
                    f"ptr=0x{ptr:08x} val_at_ptr=0x{val:04x} dec={val}"
                )

    print()
    print("=" * 100)
    print("TOP REFERENCES OVERALL")
    print("=" * 100)

    for (base, sub, ptr, val), count in ref_counts.most_common(80):
        print(
            f"count={count:4d} "
            f"base=0x{base:04x} sub=0x{sub:04x} "
            f"ptr=0x{ptr:08x} val=0x{val:04x} dec={val}"
        )

    print()
    print("=" * 100)
    print("TOP REFERENCES BY FIELD")
    print("=" * 100)

    for field in ["A", "B", "C", "D", "E"]:
        print()
        print("-" * 100)
        print(f"FIELD {field}")
        for (base, sub, ptr, val), count in field_counts[field].most_common(30):
            print(
                f"count={count:4d} "
                f"base=0x{base:04x} sub=0x{sub:04x} "
                f"ptr=0x{ptr:08x} val=0x{val:04x} dec={val}"
            )

if __name__ == "__main__":
    main()
