from pathlib import Path
import math
import struct
from collections import Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT = Path("output/global_payload_structure_map.txt")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
PAYLOAD_SIZE = PAGE_SIZE - HEADER_SIZE

T_NUMBERS = set(range(130, 175))

SYMBOL_NAMES = {
    "D": "0D_TABLE",
    "Z": "ZERO_MARKER",
    "P": "PADDING",
    "L": "LOW_ENTROPY",
    "M": "MEDIUM_ENTROPY",
    "H": "HIGH_ENTROPY",
    "?": "UNKNOWN",
}


def get_t_number(path: Path):
    name = path.stem

    if not name.startswith("T"):
        return None

    try:
        return int(name[1:])
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
    if len(page) != PAGE_SIZE:
        return "?", {
            "header": None,
            "entropy": 0.0,
            "unique": 0,
            "dominant_byte": None,
            "dominant_ratio": 0.0,
            "zero_one_ratio": 0.0,
        }

    header = struct.unpack_from(">I", page, 0)[0]
    payload = page[HEADER_SIZE:]

    counts = Counter(payload)
    ent = entropy(payload)

    dominant_byte, dominant_count = counts.most_common(1)[0]
    dominant_ratio = dominant_count / len(payload)

    zero_one_count = counts.get(0, 0) + counts.get(1, 0)
    zero_one_ratio = zero_one_count / len(payload)

    if header == 0x0D000000:
        symbol = "D"
    elif header == 0x00000000:
        symbol = "Z"
    elif zero_one_ratio >= 0.95:
        symbol = "P"
    elif ent < 3.0:
        symbol = "L"
    elif ent < 6.5:
        symbol = "M"
    else:
        symbol = "H"

    return symbol, {
        "header": header,
        "entropy": ent,
        "unique": len(counts),
        "dominant_byte": dominant_byte,
        "dominant_ratio": dominant_ratio,
        "zero_one_ratio": zero_one_ratio,
    }


def build_runs(symbols):
    if not symbols:
        return []

    runs = []

    start = 0
    current = symbols[0]

    for index in range(1, len(symbols)):
        if symbols[index] == current:
            continue

        runs.append({
            "symbol": current,
            "start": start,
            "end": index - 1,
            "count": index - start,
        })

        start = index
        current = symbols[index]

    runs.append({
        "symbol": current,
        "start": start,
        "end": len(symbols) - 1,
        "count": len(symbols) - start,
    })

    return runs


def format_map(symbols, width=80):
    lines = []

    for start in range(0, len(symbols), width):
        chunk = symbols[start:start + width]
        end = start + len(chunk) - 1

        lines.append(
            f"{start:04d}-{end:04d}  {''.join(chunk)}"
        )

    return lines


files = []

for path in CACHE.rglob("T*.ithmb"):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS:
        continue

    files.append(path)

files.sort(
    key=lambda path: (
        get_t_number(path),
        str(path.relative_to(CACHE)),
    )
)

global_symbol_counts = Counter()
global_page_count = 0
global_run_counts = Counter()

output = []

output.append("=" * 140)
output.append("GLOBAL PAYLOAD STRUCTURE MAP")
output.append("=" * 140)
output.append(f"cache: {CACHE}")
output.append(f"files: {len(files)}")
output.append("")

output.append("LEGEND")
output.append("-" * 140)

for symbol, name in SYMBOL_NAMES.items():
    output.append(f"{symbol} = {name}")

output.append("")

for path in files:
    raw = path.read_bytes()

    full_pages = len(raw) // PAGE_SIZE
    remainder = len(raw) % PAGE_SIZE

    symbols = []
    details = []

    for page_index in range(full_pages):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        symbol, info = classify_page(page)

        symbols.append(symbol)
        details.append(info)

    symbol_counts = Counter(symbols)
    runs = build_runs(symbols)

    global_page_count += full_pages
    global_symbol_counts.update(symbol_counts)

    for run in runs:
        global_run_counts[run["symbol"]] += 1

    normal_headers = [
        info["header"]
        for symbol, info in zip(symbols, details)
        if symbol not in {"D", "Z", "?"}
        and info["header"] is not None
    ]

    plus_one_pairs = 0
    plus_one_total = 0

    for left, right in zip(normal_headers, normal_headers[1:]):
        plus_one_total += 1

        if right == left + 1:
            plus_one_pairs += 1

    average_entropy = (
        sum(info["entropy"] for info in details) / len(details)
        if details
        else 0.0
    )

    output.append("=" * 140)
    output.append(str(path.relative_to(CACHE)))
    output.append("=" * 140)

    output.append(
        f"bytes={len(raw)} "
        f"full_pages={full_pages} "
        f"remainder={remainder} "
        f"avg_entropy={average_entropy:.4f}"
    )

    if plus_one_total:
        output.append(
            f"normal header +1 pairs="
            f"{plus_one_pairs}/{plus_one_total} "
            f"{plus_one_pairs / plus_one_total * 100:.2f}%"
        )
    else:
        output.append("normal header +1 pairs=none")

    output.append(
        "symbol counts: "
        + " ".join(
            f"{symbol}={symbol_counts.get(symbol, 0)}"
            for symbol in ["D", "Z", "P", "L", "M", "H", "?"]
        )
    )

    output.append("")
    output.append("PAGE MAP")
    output.append("-" * 140)

    output.extend(format_map(symbols))

    output.append("")
    output.append("RUNS")
    output.append("-" * 140)

    for run_index, run in enumerate(runs):
        output.append(
            f"run={run_index:03d} "
            f"type={run['symbol']} "
            f"name={SYMBOL_NAMES[run['symbol']]:15s} "
            f"pages={run['start']:04d}-{run['end']:04d} "
            f"count={run['count']:4d}"
        )

    output.append("")
    output.append("SPECIAL PAGES")
    output.append("-" * 140)

    special_found = False

    for page_index, (symbol, info) in enumerate(zip(symbols, details)):
        if symbol not in {"D", "Z", "P", "L"}:
            continue

        special_found = True

        header_text = (
            f"0x{info['header']:08x}"
            if info["header"] is not None
            else "none"
        )

        dominant_text = (
            f"0x{info['dominant_byte']:02x}"
            if info["dominant_byte"] is not None
            else "none"
        )

        output.append(
            f"page={page_index:04d} "
            f"type={symbol} "
            f"header={header_text} "
            f"entropy={info['entropy']:.4f} "
            f"unique={info['unique']:3d} "
            f"dominant={dominant_text} "
            f"dominant_ratio={info['dominant_ratio'] * 100:6.2f}% "
            f"zero_one={info['zero_one_ratio'] * 100:6.2f}%"
        )

    if not special_found:
        output.append("none")

    output.append("")


output.append("=" * 140)
output.append("GLOBAL SUMMARY")
output.append("=" * 140)

output.append(f"files={len(files)}")
output.append(f"pages={global_page_count}")

for symbol in ["D", "Z", "P", "L", "M", "H", "?"]:
    count = global_symbol_counts.get(symbol, 0)

    percentage = (
        count / global_page_count * 100
        if global_page_count
        else 0.0
    )

    output.append(
        f"{symbol} {SYMBOL_NAMES[symbol]:15s} "
        f"pages={count:6d} "
        f"percentage={percentage:6.2f}% "
        f"runs={global_run_counts.get(symbol, 0):5d}"
    )


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(output) + "\n")

print("=" * 100)
print("GLOBAL PAYLOAD STRUCTURE MAP")
print("=" * 100)
print(f"files: {len(files)}")
print(f"pages: {global_page_count}")
print(f"saved: {OUTPUT}")
print()

for symbol in ["D", "Z", "P", "L", "M", "H", "?"]:
    count = global_symbol_counts.get(symbol, 0)

    percentage = (
        count / global_page_count * 100
        if global_page_count
        else 0.0
    )

    print(
        f"{symbol} {SYMBOL_NAMES[symbol]:15s} "
        f"pages={count:6d} "
        f"{percentage:6.2f}%"
    )
