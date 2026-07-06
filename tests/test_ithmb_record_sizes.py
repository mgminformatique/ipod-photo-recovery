from pathlib import Path

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

CANDIDATES = [
    (56, 56, 2),
    (64, 64, 2),
    (72, 72, 2),
    (80, 80, 2),
    (100, 100, 2),
    (130, 88, 2),
    (160, 120, 2),
    (176, 132, 2),
    (220, 176, 2),
    (320, 240, 2),
    (640, 480, 2),
]

def main():
    print("=" * 100)
    print("ITHMB RECORD SIZE TEST")
    print("=" * 100)

    files = sorted(ROOT.rglob("*.ithmb"))

    for p in files:
        size = p.stat().st_size
        rel = p.relative_to(ROOT)

        print()
        print("-" * 100)
        print(f"{rel} size={size}")

        found = False
        for w, h, bpp in CANDIDATES:
            rec = w * h * bpp
            if rec and size % rec == 0:
                print(f"  MATCH {w}x{h} bpp={bpp} rec={rec} count={size // rec}")
                found = True

        if not found:
            print("  no simple RGB565 match")

if __name__ == "__main__":
    main()
