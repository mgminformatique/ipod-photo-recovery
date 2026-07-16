from pathlib import Path
import struct
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

T_NUMBERS = set(range(154, 175)) | {130}
EXCLUDED = {157, 168}

TRANSFORMS = {
    "f56": lambda f56, index9: f56,
    "f56_x4": lambda f56, index9: f56 * 4,
    "f56_x112": lambda f56, index9: f56 * 112,
    "f56_x1024": lambda f56, index9: f56 * 1024,
    "index9": lambda f56, index9: index9,
    "index9_x4": lambda f56, index9: index9 * 4,
    "index9_x112": lambda f56, index9: index9 * 112,
    "index9_x1024": lambda f56, index9: index9 * 1024,
}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


summary = defaultdict(Counter)
examples = defaultdict(list)

for path in sorted(CACHE.rglob("T*.ithmb")):
    t_number = get_t_number(path)

    if t_number not in T_NUMBERS or t_number in EXCLUDED:
        continue

    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    headers = {}

    for page_index in range(full_pages):
        off = page_index * PAGE_SIZE
        page = raw[off:off + PAGE_SIZE]

        if len(page) != PAGE_SIZE:
            continue

        headers[off] = struct.unpack_from(">I", page, 0)[0]

    for page_index in range(full_pages):
        page_off = page_index * PAGE_SIZE
        page = raw[page_off:page_off + PAGE_SIZE]

        if len(page) != PAGE_SIZE:
            continue

        if struct.unpack_from(">I", page, 0)[0] != 0x0D000000:
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
                continue

            index9 = f56 // 9

            for name, transform in TRANSFORMS.items():
                offset = transform(f56, index9)

                if offset >= len(raw):
                    kind = "OUTSIDE"
                elif offset in headers:
                    header = headers[offset]

                    if header == 0x00000000:
                        kind = "PAGE_ZERO"
                    elif header == 0x0D000000:
                        kind = "PAGE_0D"
                    else:
                        kind = "PAGE_NORMAL"
                else:
                    first4 = raw[offset:offset + 4]

                    if first4 == b"\x00\x00\x00\x00":
                        kind = "ZERO_BYTES"
                    elif first4 == b"\x0d\x00\x00\x00":
                        kind = "0D_BYTES"
                    else:
                        kind = "INSIDE_DATA"

                summary[name][kind] += 1

                if len(examples[(name, kind)]) < 8:
                    examples[(name, kind)].append(
                        (
                            str(path.relative_to(CACHE)),
                            tile_id,
                            f56,
                            index9,
                            offset,
                        )
                    )

print("=" * 120)
print("PAYLOAD F56 OFFSET CANDIDATES")
print("=" * 120)

for name in TRANSFORMS:
    counts = summary[name]
    total = sum(counts.values())

    print()
    print("-" * 120)
    print(name)
    print(f"total={total}")

    for kind, count in counts.most_common():
        print(
            f"  {kind:12s} "
            f"{count:4d}/{total:4d} "
            f"{count / total * 100:6.2f}%"
        )

        for file, tile_id, f56, index9, offset in examples[(name, kind)]:
            print(
                f"    file={file:18s} "
                f"tile={tile_id:4d} "
                f"f56={f56:4d} "
                f"index9={index9:4d} "
                f"offset=0x{offset:08x}"
            )
