from pathlib import Path
import zlib
import gzip
import bz2
import lzma

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

SIGNATURES = {
    b"\x1f\x8b": "gzip",
    b"\x78\x01": "zlib low",
    b"\x78\x9c": "zlib default",
    b"\x78\xda": "zlib best",
    b"BZh": "bzip2",
    b"\xfd7zXZ\x00": "xz",
    b"\x04\x22\x4d\x18": "lz4 frame",
    b"bplist": "binary plist",
    b"SQLite": "sqlite",
}

def try_decompress(name, chunk):
    try:
        if name.startswith("zlib"):
            return zlib.decompress(chunk)
        if name == "gzip":
            return gzip.decompress(chunk)
        if name == "bzip2":
            return bz2.decompress(chunk)
        if name == "xz":
            return lzma.decompress(chunk)
    except Exception:
        return None
    return None

def ascii_preview(data):
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in data[:200])

def main():
    data = DB.read_bytes()

    print("=" * 100)
    print("COMPRESSION SIGNATURES")
    print("=" * 100)
    print(f"file: {DB}")
    print(f"size: {len(data)}")
    print()

    print("SIGNATURE SEARCH")
    print("-" * 100)

    found = []

    for sig, name in SIGNATURES.items():
        start = 0
        while True:
            off = data.find(sig, start)
            if off == -1:
                break
            found.append((off, name, sig))
            print(f"found {name:12s} at 0x{off:08x} sig={sig.hex()}")
            start = off + 1

    if not found:
        print("no known compression/file signatures found")

    print()
    print("=" * 100)
    print("TRY DECOMPRESS FROM FOUND OFFSETS")
    print("=" * 100)

    for off, name, sig in found:
        if name in ["gzip", "bzip2", "xz"] or name.startswith("zlib"):
            out = try_decompress(name, data[off:])
            print()
            print("-" * 100)
            print(f"try {name} from 0x{off:08x}")
            if out is None:
                print("decompress failed")
            else:
                print(f"decompressed size: {len(out)}")
                print("first 200 ascii:")
                print(ascii_preview(out))
                print("first 64 hex:")
                print(" ".join(f"{x:02x}" for x in out[:64]))

    print()
    print("=" * 100)
    print("BRUTE ZLIB EVERY OFFSET FIRST 4096")
    print("=" * 100)

    hits = 0
    for off in range(0, min(len(data), 4096)):
        try:
            out = zlib.decompress(data[off:])
            if len(out) > 32:
                print(f"zlib success at 0x{off:08x}, out size={len(out)}")
                print(ascii_preview(out))
                hits += 1
                if hits >= 20:
                    break
        except Exception:
            pass

    if hits == 0:
        print("no zlib stream found in first 4096 bytes")


if __name__ == "__main__":
    main()
