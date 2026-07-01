from pathlib import Path
from core.binary import BinaryFile
import sys


def analyze(cache_path):
    root = Path(cache_path)
    photo_db = root / "Photo Database"
    ithmb_files = sorted(root.rglob("*.ithmb"))

    print("iPod Photo Recovery - Analyze")
    print("=" * 40)
    print("Cache:", root)
    print("Photo Database:", "YES" if photo_db.exists() else "NO")

    if photo_db.exists():
        db = BinaryFile(photo_db)
        print("Photo Database size:", db.size)
        print("Photo Database entropy:", round(db.entropy(), 3))

    print("")
    print(".ithmb files:", len(ithmb_files))

    for f in ithmb_files[:30]:
        bf = BinaryFile(f)
        rel = f.relative_to(root)
        print(f"{rel} | {bf.size} bytes | entropy {round(bf.entropy(), 3)}")


def main():
    if len(sys.argv) < 3:
        print('Usage: python3 main.py analyze "/path/to/iPod Photo Cache"')
        return

    if sys.argv[1] == "analyze":
        analyze(sys.argv[2])
    else:
        print("Unknown command:", sys.argv[1])


if __name__ == "__main__":
    main()
