from pathlib import Path
import struct
from collections import defaultdict, Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


rows = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    for page_index in range(full_pages):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        header = struct.unpack_from(">I", page, 0)[0]

        if header != 0x0D000000:
            continue

        payload = page[HEADER_SIZE:]

        for record_index in range(RECORD_COUNT):
            start = RECORD_START + record_index * RECORD_SIZE
            record = payload[start:start + RECORD_SIZE]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]
            f56 = struct.unpack_from(">H", record, 0x56)[0]

            if f56 % 9 != 0:
                raise SystemExit(
                    f"Non-divisible f56 in {path}: "
                    f"tile={tile_id} f56={f56}"
                )

            index9 = f56 // 9
            base_id = tile_id - index9

            rows.append({
                "file": str(path.relative_to(CACHE)),
                "t_number": t_number,
                "page": page_index,
                "record": record_index,
                "tile_id": tile_id,
                "f56": f56,
                "index9": index9,
                "base_id": base_id,
            })


print("=" * 130)
print("PAYLOAD F56 BASE TRANSITIONS")
print("=" * 130)
print(f"records={len(rows)}")
print()

by_tile = defaultdict(list)

for row in rows:
    by_tile[row["tile_id"]].append(row)

print("=" * 130)
print("PRIMARY ROW PER TILE")
print("=" * 130)

previous_base = None
run_start = None
run_end = None
run_rows = []

runs = []

for tile_id in sorted(by_tile):
    tile_rows = sorted(
        by_tile[tile_id],
        key=lambda row: (
            row["base_id"],
            row["t_number"],
            row["page"],
        )
    )

    bases = Counter(row["base_id"] for row in tile_rows)
    primary_base, primary_count = bases.most_common(1)[0]

    primary_rows = [
        row
        for row in tile_rows
        if row["base_id"] == primary_base
    ]

    sample = primary_rows[0]

    print(
        f"tile={tile_id:4d} "
        f"index9={sample['index9']:4d} "
        f"base={primary_base:4d} "
        f"base_count={primary_count}/{len(tile_rows)} "
        f"file={sample['file']} "
        f"page={sample['page']:4d} "
        f"record={sample['record']}"
    )

    if previous_base is None:
        run_start = tile_id
        run_end = tile_id
        run_rows = [sample]
        previous_base = primary_base
        continue

    if primary_base == previous_base and tile_id == run_end + 1:
        run_end = tile_id
        run_rows.append(sample)
        continue

    runs.append({
        "start": run_start,
        "end": run_end,
        "base": previous_base,
        "rows": run_rows,
    })

    run_start = tile_id
    run_end = tile_id
    run_rows = [sample]
    previous_base = primary_base

if run_start is not None:
    runs.append({
        "start": run_start,
        "end": run_end,
        "base": previous_base,
        "rows": run_rows,
    })


print()
print("=" * 130)
print("BASE RUNS")
print("=" * 130)

for run in runs:
    count = run["end"] - run["start"] + 1
    first_index9 = run["rows"][0]["index9"]
    last_index9 = run["rows"][-1]["index9"]

    print(
        f"tiles={run['start']}-{run['end']} "
        f"count={count:3d} "
        f"base={run['base']:4d} "
        f"index9={first_index9}-{last_index9}"
    )


print()
print("=" * 130)
print("ALL BASES PER TILE")
print("=" * 130)

for tile_id in sorted(by_tile):
    tile_rows = by_tile[tile_id]
    bases = Counter(row["base_id"] for row in tile_rows)

    if len(bases) <= 1:
        continue

    print(f"tile={tile_id}")

    for base_id, count in bases.most_common():
        print(
            f"  base={base_id:4d} "
            f"count={count}"
        )

        for row in tile_rows:
            if row["base_id"] != base_id:
                continue

            print(
                f"    file={row['file']} "
                f"page={row['page']:4d} "
                f"record={row['record']} "
                f"f56={row['f56']:4d} "
                f"index9={row['index9']:4d}"
            )


print()
print("=" * 130)
print("BASE DIFFERENCES")
print("=" * 130)

unique_bases = sorted(set(row["base_id"] for row in rows))

print(
    "bases: "
    + " ".join(str(value) for value in unique_bases)
)

for left, right in zip(unique_bases, unique_bases[1:]):
    print(
        f"{left:4d} -> {right:4d} "
        f"delta={right-left:+4d}"
    )
