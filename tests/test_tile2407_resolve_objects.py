from pathlib import Path
import struct
import hashlib

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

TILE_ID = 2407

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

MARKER_HEADERS = {
    0x00000000: "ZERO",
    0x0D000000: "0D",
}


def get_t_number(path: Path):
    try:
        return int(path.stem[1:])
    except (ValueError, IndexError):
        return None


print("=" * 120)
print(f"RESOLVE TILE ID {TILE_ID}")
print("=" * 120)

hits = []

for path in sorted(CACHE.rglob("T*.ithmb")):
    raw = path.read_bytes()
    full_pages = len(raw) // PAGE_SIZE

    if full_pages == 0:
        continue

    pages = []

    for page_index in range(full_pages):
        start = page_index * PAGE_SIZE
        page = raw[start:start + PAGE_SIZE]

        pages.append({
            "index": page_index,
            "header": struct.unpack_from(">I", page, 0)[0],
            "payload": page[HEADER_SIZE:],
        })

    first_header = pages[0]["header"]

    marker_indexes = [
        page["index"]
        for page in pages
        if page["header"] in MARKER_HEADERS
    ]

    for table_page in pages:
        if table_page["header"] != 0x0D000000:
            continue

        payload = table_page["payload"]

        for record_index in range(RECORD_COUNT):
            start = RECORD_START + record_index * RECORD_SIZE
            record = payload[start:start + RECORD_SIZE]

            if len(record) != RECORD_SIZE:
                continue

            tile_id = struct.unpack_from("<H", record, 0x04)[0]

            if tile_id != TILE_ID:
                continue

            f56 = struct.unpack_from(">H", record, 0x56)[0]
            reference = struct.unpack_from(">I", record, 0x6C)[0]

            referenced_page = reference - first_header

            hit = {
                "path": path,
                "relative": str(path.relative_to(CACHE)),
                "pages": pages,
                "markers": marker_indexes,
                "table_page": table_page["index"],
                "record": record_index,
                "first_header": first_header,
                "reference": reference,
                "referenced_page": referenced_page,
                "f56": f56,
            }

            hits.append(hit)


print(f"hits={len(hits)}")
print()

for hit_index, hit in enumerate(hits):
    pages = hit["pages"]
    markers = hit["markers"]
    referenced_page = hit["referenced_page"]

    print("-" * 120)
    print(
        f"hit={hit_index:02d} "
        f"file={hit['relative']} "
        f"table_page={hit['table_page']} "
        f"record={hit['record']}"
    )
    print(
        f"first_header=0x{hit['first_header']:08x} "
        f"reference=0x{hit['reference']:08x} "
        f"resolved_page={referenced_page} "
        f"f56={hit['f56']}"
    )

    if not 0 <= referenced_page < len(pages):
        print("resolved page is outside this file")
        continue

    referenced_header = pages[referenced_page]["header"]

    print(
        f"resolved_header=0x{referenced_header:08x} "
        f"type={MARKER_HEADERS.get(referenced_header, 'NORMAL')}"
    )

    previous_marker = max(
        (index for index in markers if index < referenced_page),
        default=None,
    )

    next_marker = min(
        (index for index in markers if index > referenced_page),
        default=None,
    )

    print(
        f"previous_marker={previous_marker} "
        f"next_marker={next_marker}"
    )

    # Objet avant le marqueur référencé.
    before_start = (
        previous_marker + 1
        if previous_marker is not None
        else 0
    )
    before_end = referenced_page
    before_pages = pages[before_start:before_end]
    before_data = b"".join(page["payload"] for page in before_pages)

    # Objet après le marqueur référencé.
    after_start = referenced_page + 1
    after_end = (
        next_marker
        if next_marker is not None
        else len(pages)
    )
    after_pages = pages[after_start:after_end]
    after_data = b"".join(page["payload"] for page in after_pages)

    print()
    print("OBJECT BEFORE REFERENCE")
    print(
        f"pages={before_start}-{before_end - 1} "
        f"count={len(before_pages)} "
        f"bytes={len(before_data)} "
        f"sha1={hashlib.sha1(before_data).hexdigest()}"
    )

    print()
    print("OBJECT AFTER REFERENCE")
    print(
        f"pages={after_start}-{after_end - 1} "
        f"count={len(after_pages)} "
        f"bytes={len(after_data)} "
        f"sha1={hashlib.sha1(after_data).hexdigest()}"
    )

    print()
    print("NEARBY MARKERS")

    nearby = [
        index
        for index in markers
        if abs(index - referenced_page) <= 120
    ]

    for index in nearby:
        print(
            f"  page={index:4d} "
            f"header=0x{pages[index]['header']:08x} "
            f"type={MARKER_HEADERS[pages[index]['header']]}"
        )

print()
print("=" * 120)
print("CROSS-FILE SUMMARY")
print("=" * 120)

for hit in hits:
    print(
        f"{hit['relative']:18s} "
        f"table_page={hit['table_page']:4d} "
        f"record={hit['record']} "
        f"reference=0x{hit['reference']:08x} "
        f"resolved_page={hit['referenced_page']:4d} "
        f"f56={hit['f56']}"
    )
