from pathlib import Path
import math
import struct
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT = Path("output/global_53_page_alignment.txt")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
CYCLE = 53

T_MIN = 130
T_MAX = 174


def get_t_number(path: Path):
    if not path.stem.startswith("T"):
        return None

    try:
        return int(path.stem[1:])
    except ValueError:
        return None


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def classify_page(page: bytes):
    header = struct.unpack_from(">I", page, 0)[0]
    payload = page[HEADER_SIZE:]

    counts = Counter(payload)
    ent = entropy(payload)

    zero_one = counts.get(0, 0) + counts.get(1, 0)
    zero_one_ratio = zero_one / len(payload)

    if header == 0x0D000000:
        return "D", ent

    if header == 0x00000000:
        return "Z", ent

    if zero_one_ratio >= 0.95:
        return "P", ent

    if ent < 3.0:
        return "L", ent

    if ent < 6.5:
        return "M", ent

    return "H", ent


def circular_distance(left: int, right: int, modulus: int):
    direct = abs(left - right)
    return min(direct, modulus - direct)


def best_phase(page_indexes):
    """
    Trouve la phase modulo 53 qui minimise la distance entre
    les pages observées et une grille théorique répétée tous les 53 blocs.
    """
    if not page_indexes:
        return None

    best = None

    for phase in range(CYCLE):
        distances = [
            circular_distance(page % CYCLE, phase, CYCLE)
            for page in page_indexes
        ]

        exact = sum(distance == 0 for distance in distances)
        within1 = sum(distance <= 1 for distance in distances)
        within2 = sum(distance <= 2 for distance in distances)
        total_distance = sum(distances)

        candidate = {
            "phase": phase,
            "exact": exact,
            "within1": within1,
            "within2": within2,
            "distance": total_distance,
        }

        score = (
            exact,
            within1,
            within2,
            -total_distance,
        )

        if best is None or score > best["score"]:
            candidate["score"] = score
            best = candidate

    return best


files = []

for path in CACHE.rglob("T*.ithmb"):
    number = get_t_number(path)

    if number is None:
        continue

    if not T_MIN <= number <= T_MAX:
        continue

    files.append(path)

files.sort(
    key=lambda path: (
        get_t_number(path),
        str(path.relative_to(CACHE)),
    )
)

global_positions = defaultdict(list)
global_modulo = defaultdict(Counter)
global_marker_gaps = Counter()

report = []

report.append("=" * 150)
report.append("GLOBAL 53-PAGE ALIGNMENT")
report.append("=" * 150)
report.append(f"files={len(files)}")
report.append("")

for path in files:
    raw = path.read_bytes()
    page_count = len(raw) // PAGE_SIZE

    symbols = []
    entropies = []

    for page_index in range(page_count):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        symbol, ent = classify_page(page)

        symbols.append(symbol)
        entropies.append(ent)

    positions = defaultdict(list)

    for page_index, symbol in enumerate(symbols):
        positions[symbol].append(page_index)
        global_positions[symbol].append(
            (
                str(path.relative_to(CACHE)),
                page_index,
            )
        )
        global_modulo[symbol][page_index % CYCLE] += 1

    separators = sorted(
        set(
            positions["Z"]
            + positions["D"]
        )
    )

    gaps = [
        right - left
        for left, right in zip(separators, separators[1:])
    ]

    global_marker_gaps.update(gaps)

    zero_phase = best_phase(positions["Z"])
    table_phase = best_phase(positions["D"])
    separator_phase = best_phase(separators)

    report.append("=" * 150)
    report.append(str(path.relative_to(CACHE)))
    report.append("=" * 150)

    report.append(
        f"pages={page_count} "
        f"Z={len(positions['Z'])} "
        f"D={len(positions['D'])} "
        f"P={len(positions['P'])} "
        f"L={len(positions['L'])} "
        f"M={len(positions['M'])} "
        f"H={len(positions['H'])}"
    )

    if zero_phase:
        report.append(
            "best Z phase: "
            f"phase={zero_phase['phase']:02d} "
            f"exact={zero_phase['exact']}/{len(positions['Z'])} "
            f"within1={zero_phase['within1']}/{len(positions['Z'])} "
            f"within2={zero_phase['within2']}/{len(positions['Z'])} "
            f"distance={zero_phase['distance']}"
        )
    else:
        report.append("best Z phase: none")

    if table_phase:
        report.append(
            "best D phase: "
            f"phase={table_phase['phase']:02d} "
            f"exact={table_phase['exact']}/{len(positions['D'])} "
            f"within1={table_phase['within1']}/{len(positions['D'])} "
            f"within2={table_phase['within2']}/{len(positions['D'])} "
            f"distance={table_phase['distance']}"
        )
    else:
        report.append("best D phase: none")

    if separator_phase:
        report.append(
            "best separator phase: "
            f"phase={separator_phase['phase']:02d} "
            f"exact={separator_phase['exact']}/{len(separators)} "
            f"within1={separator_phase['within1']}/{len(separators)} "
            f"within2={separator_phase['within2']}/{len(separators)} "
            f"distance={separator_phase['distance']}"
        )
    else:
        report.append("best separator phase: none")

    report.append("")
    report.append("SEPARATOR MODULO 53")
    report.append("-" * 150)

    separator_modulo = Counter(
        page % CYCLE
        for page in separators
    )

    if separator_modulo:
        for remainder, count in separator_modulo.most_common():
            report.append(
                f"remainder={remainder:02d} "
                f"count={count:4d}"
            )
    else:
        report.append("none")

    report.append("")
    report.append("SEPARATOR GAPS")
    report.append("-" * 150)

    gap_counts = Counter(gaps)

    if gap_counts:
        for gap, count in gap_counts.most_common(20):
            report.append(
                f"gap={gap:4d} "
                f"count={count:4d} "
                f"multiple53={gap % CYCLE == 0}"
            )
    else:
        report.append("none")

    report.append("")
    report.append("SEPARATOR LIST")
    report.append("-" * 150)

    for page_index in separators:
        report.append(
            f"page={page_index:04d} "
            f"type={symbols[page_index]} "
            f"mod53={page_index % CYCLE:02d} "
            f"entropy={entropies[page_index]:.4f}"
        )

    report.append("")


report.append("=" * 150)
report.append("GLOBAL MODULO DISTRIBUTIONS")
report.append("=" * 150)

for symbol in ["Z", "D", "P", "L", "M", "H"]:
    report.append("")
    report.append(f"TYPE {symbol}")
    report.append("-" * 150)

    total = sum(global_modulo[symbol].values())

    for remainder, count in global_modulo[symbol].most_common():
        percentage = count / total * 100 if total else 0.0

        report.append(
            f"remainder={remainder:02d} "
            f"count={count:5d}/{total:5d} "
            f"{percentage:6.2f}%"
        )


report.append("")
report.append("=" * 150)
report.append("GLOBAL Z/D SEPARATOR GAP DISTRIBUTION")
report.append("=" * 150)

for gap, count in global_marker_gaps.most_common(100):
    report.append(
        f"gap={gap:4d} "
        f"count={count:5d} "
        f"gap_mod53={gap % CYCLE:02d} "
        f"multiple53={gap % CYCLE == 0}"
    )


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(report) + "\n")

print("=" * 110)
print("GLOBAL 53-PAGE ALIGNMENT")
print("=" * 110)
print(f"files: {len(files)}")
print(f"saved: {OUTPUT}")
print()

print("Top global Z modulo-53 positions:")
for remainder, count in global_modulo["Z"].most_common(15):
    print(
        f"  remainder={remainder:02d} "
        f"count={count}"
    )

print()
print("Top global separator gaps:")
for gap, count in global_marker_gaps.most_common(20):
    print(
        f"  gap={gap:4d} "
        f"count={count:4d} "
        f"mod53={gap % CYCLE:02d}"
    )
