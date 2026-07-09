from pathlib import Path
import struct
from collections import Counter

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

FILES = [
    ROOT / "F05" / "T154.ithmb",
    ROOT / "F06" / "T155.ithmb",
    ROOT / "F07" / "T156.ithmb",
    ROOT / "F08" / "T157.ithmb",
    ROOT / "F09" / "T158.ithmb",
]

def u32le(b, off):
    return struct.unpack_from("<I", b, off)[0]

def main():
    print("=" * 100)
    print("PAYLOAD U32 STRUCTURE")
    print("=" * 100)

    for path in FILES:
        data = path.read_bytes()
        size = len(data)

        print()
        print("=" * 100)
        print(path.relative_to(ROOT), "size", size)
        print("-" * 100)

        candidates = []

        for off in range(0, min(size - 4, 65536), 4):
            v = u32le(data, off)

            if 0 < v < size and v % 4 == 0:
                candidates.append((off, v))

        print(f"u32 offset-like values in first 64k: {len(candidates)}")

        for off, v in candidates[:120]:
            print(f"0x{off:08x}: 0x{v:08x} ({v})")

        print()
        print("runs of increasing offset-like u32 values:")
        run = []
        last_v = None

        for off, v in candidates:
            if last_v is not None and v > last_v:
                run.append((off, v))
            else:
                if len(run) >= 8:
                    print(f"run len={len(run)} start_file_off=0x{run[0][0]:08x}")
                    print("  " + " ".join(f"{v:08x}" for _, v in run[:30]))
                run = [(off, v)]
            last_v = v

        if len(run) >= 8:
            print(f"run len={len(run)} start_file_off=0x{run[0][0]:08x}")
            print("  " + " ".join(f"{v:08x}" for _, v in run[:30]))

if __name__ == "__main__":
    main()
