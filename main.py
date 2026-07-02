#!/usr/bin/env python3

from pathlib import Path
import sys
from collections import Counter
import math

from core.binary import BinaryFile
from analysis.ithmb_analyzer import ITHMBAnalyzer
from parser.ithmb_records import ITHMBRecordParser


TITLE = "iPod Photo Recovery"


def entropy(data):
    if not data:
        return 0.0

    c = Counter(data)
    total = len(data)

    return -sum((n / total) * math.log2(n / total) for n in c.values())


def analyze(cache_path):
    root = Path(cache_path)

    if not root.exists():
        print("Erreur : dossier introuvable")
        print(root)
        return

    print("=" * 60)
    print(TITLE)
    print("=" * 60)
    print("Cache :", root)
    print()

    photo_db = root / "Photo Database"

    print("Photo Database")
    print("------------------------------")

    if photo_db.exists():
        db = BinaryFile(photo_db)
        print("Status   : FOUND")
        print("Size     :", db.size, "bytes")
        print("Entropy  :", round(db.entropy(), 3))
    else:
        print("Status   : NOT FOUND")

    print()

    ithmb_files = sorted(root.rglob("*.ithmb"))

    print("ITHMB Files")
    print("------------------------------")
    print("Found :", len(ithmb_files))
    print()

    for ithmb in ithmb_files:
        bf = BinaryFile(ithmb)
        rel = ithmb.relative_to(root)

        print("=" * 60)
        print(rel)
        print("=" * 60)
        print("Size     :", bf.size)
        print("Entropy  :", round(bf.entropy(), 3))
        print()

        analyzer = ITHMBAnalyzer(ithmb)
        candidates = analyzer.candidate_frames()

        print("Best candidates:")

        for c in candidates[:8]:
            print(
                f"  {c['width']}x{c['height']:>3}   "
                f"{c['format']:<10}   "
                f"frames={c['frames']:<4}   "
                f"remainder={c['remainder']}"
            )

        print()


def inventory(cache_path):
    root = Path(cache_path)

    if not root.exists():
        print("Erreur : dossier introuvable")
        print(root)
        return

    print("=" * 100)
    print("iPod Photo Cache Inventory")
    print("=" * 100)
    print("Cache:", root)
    print()

    print(
        f"{'FILE':<25} "
        f"{'SIZE':>10} "
        f"{'ENT':>6} "
        f"{'REC':>5} "
        f"{'SLOTS':<35}"
    )

    print("-" * 100)

    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue

        data = f.read_bytes()
        ent = entropy(data)

        records = []

        if f.suffix.lower() == ".ithmb":
            parser = ITHMBRecordParser(f)
            records = parser.find_records()

        slots = [r.data[6] for r in records]

        if slots:
            slot_text = ",".join(str(s) for s in slots)
        else:
            slot_text = "-"

        print(
            f"{str(f.relative_to(root)):<25} "
            f"{len(data):>10} "
            f"{ent:>6.3f} "
            f"{len(records):>5} "
            f"{slot_text:<35}"
        )


def usage():
    print()
    print("Usage:")
    print()
    print('  python3 main.py analyze "/path/to/iPod Photo Cache"')
    print('  python3 main.py inventory "/path/to/iPod Photo Cache"')
    print()


def main():
    if len(sys.argv) < 3:
        usage()
        return

    command = sys.argv[1]
    cache_path = sys.argv[2]

    if command == "analyze":
        analyze(cache_path)
    elif command == "inventory":
        inventory(cache_path)
    else:
        print("Unknown command:", command)
        usage()


if __name__ == "__main__":
    main()
