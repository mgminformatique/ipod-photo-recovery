from pathlib import Path
import struct
import math
from collections import Counter, defaultdict

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


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def classify(data: bytes):
    ent = entropy(data)
    zero_one = data.count(0) + data.count(1)
    zero_one_ratio = zero_one / len(data)

    if zero_one_ratio >= 0.95:
        return "PADDING", ent

    if ent < 2.0:
        return "VERY_LOW", ent

    if ent < 4.5:
        return "LOW", ent

    if ent < 6.5:
        return "MEDIUM", ent

    return "HIGH", ent


def page_zone(page_index: int):
    if page_index < 251:
        return "ZONE_A_000_250"

    if page_index < 385:
        return "ZONE_B_251_384"

    return "ZONE_C_385_PLUS"


rows = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    page_count = len(raw) // PAGE_SIZE

    for table_page in range(page_count):
        page = raw[
            table_page * PAGE_SIZE:
            (table_page + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        if struct.unpack_from(">I", page, 0)[0] != 0x0D000000:
            continue

        table_payload = page[HEADER_SIZE:]

        for record_index in range(RECORD_COUNT):
            start = RECORD_START + record_index * RECORD_SIZE
            record = table_payload[start:start + RECORD_SIZE]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]
            f56 = struct.unpack_from(">H", record, 0x56)[0]

            if f56 % 9:
                continue

            page_index = f56 // 9

            if not 0 <= page_index < page_count:
                continue

            raw_page = raw[
                page_index * PAGE_SIZE:
                (page_index + 1) * PAGE_SIZE
            ]

            header = struct.unpack_from(">I", raw_page, 0)[0]
            payload = raw_page[HEADER_SIZE:]

            profile, ent = classify(payload)

            counts = Counter(payload)
            mean = sum(payload) / len(payload)

            variance = sum(
                (value - mean) ** 2
                for value in payload
            ) / len(payload)

            rows.append({
                "file": str(path.relative_to(CACHE)),
                "tile": tile_id,
                "page": page_index,
                "zone": page_zone(page_index),
                "profile": profile,
                "entropy": ent,
                "unique": len(counts),
                "mean": mean,
                "variance": variance,
                "zeros": counts[0],
                "ones": counts[1],
                "header": header,
            })


print("=" * 125)
print("PAYLOAD PAGE PROFILE CLUSTERS")
print("=" * 125)
print(f"rows={len(rows)}")
print()

print("=" * 125)
print("GLOBAL PROFILE DISTRIBUTION")
print("=" * 125)

global_profiles = Counter(row["profile"] for row in rows)

for profile, count in global_profiles.most_common():
    print(
        f"{profile:10s} "
        f"{count:3d}/{len(rows):3d} "
        f"{count / len(rows) * 100:6.2f}%"
    )

print()
print("=" * 125)
print("PROFILE DISTRIBUTION BY PAGE ZONE")
print("=" * 125)

by_zone = defaultdict(list)

for row in rows:
    by_zone[row["zone"]].append(row)

for zone in sorted(by_zone):
    zone_rows = by_zone[zone]
    profiles = Counter(row["profile"] for row in zone_rows)

    print()
    print("-" * 125)
    print(zone)
    print(f"rows={len(zone_rows)}")

    for profile, count in profiles.most_common():
        print(
            f"  {profile:10s} "
            f"{count:3d}/{len(zone_rows):3d} "
            f"{count / len(zone_rows) * 100:6.2f}%"
        )

    print(
        f"  entropy average = "
        f"{sum(row['entropy'] for row in zone_rows) / len(zone_rows):.4f}"
    )

    print(
        f"  unique average  = "
        f"{sum(row['unique'] for row in zone_rows) / len(zone_rows):.2f}"
    )

    print(
        f"  mean average    = "
        f"{sum(row['mean'] for row in zone_rows) / len(zone_rows):.2f}"
    )

    print(
        f"  variance average= "
        f"{sum(row['variance'] for row in zone_rows) / len(zone_rows):.2f}"
    )


print()
print("=" * 125)
print("PADDING / VERY LOW PAGES")
print("=" * 125)

for row in rows:
    if row["profile"] not in {"PADDING", "VERY_LOW"}:
        continue

    print(
        f"file={row['file']:18s} "
        f"tile={row['tile']:4d} "
        f"page={row['page']:4d} "
        f"zone={row['zone']:15s} "
        f"profile={row['profile']:8s} "
        f"entropy={row['entropy']:6.3f} "
        f"unique={row['unique']:3d} "
        f"zero={row['zeros']:4d} "
        f"one={row['ones']:4d} "
        f"header=0x{row['header']:08x}"
    )


print()
print("=" * 125)
print("ENTROPY HISTOGRAM BY ZONE")
print("=" * 125)

for zone in sorted(by_zone):
    histogram = Counter()

    for row in by_zone[zone]:
        bucket = min(int(row["entropy"]), 7)
        histogram[bucket] += 1

    print(zone)

    for bucket in range(8):
        print(
            f"  entropy {bucket}.0-{bucket}.99: "
            f"{histogram[bucket]:3d}"
        )
