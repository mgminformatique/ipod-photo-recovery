from pathlib import Path
import zlib
import gzip

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    ROOT / "F05" / "T154.ithmb",
    ROOT / "F06" / "T155.ithmb",
    ROOT / "F07" / "T156.ithmb",
    ROOT / "F08" / "T157.ithmb",
    ROOT / "F09" / "T158.ithmb",
]

SIGS = {
    "jpeg": bytes.fromhex("ffd8ff"),
    "png": bytes.fromhex("89504e47"),
    "gif": b"GIF",
    "zlib_7801": bytes.fromhex("7801"),
    "zlib_789c": bytes.fromhex("789c"),
    "zlib_78da": bytes.fromhex("78da"),
    "gzip": bytes.fromhex("1f8b"),
    "bplist": b"bplist",
    "SQLite": b"SQLite",
}

def find_all(data, sig):
    out = []
    start = 0
    while True:
        i = data.find(sig, start)
        if i == -1:
            break
        out.append(i)
        start = i + 1
    return out

def main():
    print("=" * 100)
    print("PAYLOAD SIGNATURE SCAN")
    print("=" * 100)

    for path in FILES:
        data = path.read_bytes()
        print()
        print("=" * 100)
        print(path.relative_to(ROOT), "size", len(data))
        print("-" * 100)

        for name, sig in SIGS.items():
            hits = find_all(data, sig)
            if hits:
                print(f"{name}: {len(hits)} hits")
                print("  " + " ".join(f"0x{x:08x}" for x in hits[:30]))

        print()
        print("try zlib first 200k offsets...")
        found = 0
        for off in range(0, min(len(data), 200000)):
            try:
                out = zlib.decompress(data[off:])
                print(f"zlib OK at 0x{off:08x} out_len={len(out)}")
                found += 1
                if found >= 5:
                    break
            except Exception:
                pass

        if found == 0:
            print("no zlib streams found")

if __name__ == "__main__":
    main()
