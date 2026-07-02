#!/usr/bin/env python3

from pathlib import Path
import sys

from core.binary import BinaryFile
from analysis.ithmb_analyzer import ITHMBAnalyzer


TITLE = "iPod Photo Recovery"


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

    # ------------------------------------------------------------
    # Photo Database
    # ------------------------------------------------------------

    photo_db = root / "Photo Database"

    if photo_db.exists():
        db = BinaryFile(photo_db)

        print("Photo Database")
        print("------------------------------")
        print("Status   : FOUND")
        print("Size     :", db.size, "bytes")
        print("Entropy  :", round(db.entropy(), 3))
    else:
        print("Photo Database")
        print("------------------------------")
        print("Status   : NOT FOUND")

    print()

    # ------------------------------------------------------------
    # ITHMB
    # ------------------------------------------------------------

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


def usage():
    print()
    print("Usage:")
    print()
    print('python3 main.py analyze "/path/to/iPod Photo Cache"')
    print()


def main():

    if len(sys.argv) < 3:
        usage()
        return

    command = sys.argv[1]

    if command == "analyze":
        analyze(sys.argv[2])
    else:
        print("Unknown command:", command)


if __name__ == "__main__":
    main()
