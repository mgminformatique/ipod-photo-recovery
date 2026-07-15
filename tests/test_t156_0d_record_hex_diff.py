from pathlib import Path
import struct

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

PAGE_A = 358
PAGE_B = 783

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8
ROW_SIZE = 16


def read_marker_payload(raw: bytes, page_index: int) -> bytes:
    start = page_index * PAGE_SIZE
    page = raw[start:start + PAGE_SIZE]

    if len(page) != PAGE_SIZE:
        raise SystemExit(
            f"Page {page_index} incomplete: {len(page)} bytes"
        )

    header = struct.unpack_from(">I", page, 0)[0]

    if header != 0x0D000000:
        raise SystemExit(
            f"Page {page_index}: expected 0x0D000000, "
            f"found 0x{header:08x}"
        )

    return page[HEADER_SIZE:]


def ascii_view(data: bytes) -> str:
    return "".join(
        chr(value) if 32 <= value <= 126 else "."
        for value in data
    )


raw = SRC.read_bytes()

payload_a = read_marker_payload(raw, PAGE_A)
payload_b = read_marker_payload(raw, PAGE_B)

print("=" * 128)
print("T156 0D RECORD HEX DIFF")
print("=" * 128)
print(f"page A: {PAGE_A}")
print(f"page B: {PAGE_B}")
print(f"record start: 0x{RECORD_START:03x}")
print(f"record size:  0x{RECORD_SIZE:02x} ({RECORD_SIZE})")
print(f"records:      {RECORD_COUNT}")
print()

for record_index in range(RECORD_COUNT):
    start = RECORD_START + record_index * RECORD_SIZE
    end = start + RECORD_SIZE

    record_a = payload_a[start:end]
    record_b = payload_b[start:end]

    changed = [
        offset
        for offset, (left, right) in enumerate(zip(record_a, record_b))
        if left != right
    ]

    print("=" * 128)
    print(
        f"RECORD {record_index:02d} "
        f"payload range=0x{start:03x}-0x{end - 1:03x} "
        f"changed={len(changed)}/{RECORD_SIZE}"
    )

    if changed:
        print(
            "changed fields: "
            + ", ".join(f"0x{offset:02x}" for offset in changed)
        )
    else:
        print("changed fields: none")

    print("-" * 128)

    for row_start in range(0, RECORD_SIZE, ROW_SIZE):
        row_end = min(row_start + ROW_SIZE, RECORD_SIZE)

        row_a = record_a[row_start:row_end]
        row_b = record_b[row_start:row_end]

        marker = [
            "^^" if left != right else "  "
            for left, right in zip(row_a, row_b)
        ]

        print(
            f"+0x{row_start:02x} A: "
            + " ".join(f"{value:02x}" for value in row_a)
            + f"  |{ascii_view(row_a)}|"
        )

        print(
            f"      B: "
            + " ".join(f"{value:02x}" for value in row_b)
            + f"  |{ascii_view(row_b)}|"
        )

        print(
            "         "
            + " ".join(marker)
        )

    print()
    print("CHANGED VALUES AS POSSIBLE FIELDS")
    print("-" * 128)

    # Montre chaque différence seule, puis comme partie
    # de champs 16 et 32 bits voisins.
    for offset in changed:
        print(
            f"byte +0x{offset:02x}: "
            f"0x{record_a[offset]:02x} -> "
            f"0x{record_b[offset]:02x}"
        )

        for field_size, fmt_be, fmt_le in [
            (2, ">H", "<H"),
            (4, ">I", "<I"),
        ]:
            field_start = offset - (offset % field_size)

            if field_start + field_size > RECORD_SIZE:
                continue

            a_be = struct.unpack_from(fmt_be, record_a, field_start)[0]
            b_be = struct.unpack_from(fmt_be, record_b, field_start)[0]

            a_le = struct.unpack_from(fmt_le, record_a, field_start)[0]
            b_le = struct.unpack_from(fmt_le, record_b, field_start)[0]

            print(
                f"  aligned u{field_size * 8} +0x{field_start:02x}: "
                f"BE 0x{a_be:0{field_size * 2}x}"
                f" -> 0x{b_be:0{field_size * 2}x}; "
                f"LE 0x{a_le:0{field_size * 2}x}"
                f" -> 0x{b_le:0{field_size * 2}x}"
            )

    print()

print("=" * 128)
print("CROSS-RECORD FIELD SEQUENCES")
print("=" * 128)

for field_offset in [0x04, 0x57, 0x6E]:
    values_a = []
    values_b = []

    for record_index in range(RECORD_COUNT):
        start = RECORD_START + record_index * RECORD_SIZE
        record_a = payload_a[start:start + RECORD_SIZE]
        record_b = payload_b[start:start + RECORD_SIZE]

        if field_offset == 0x6E:
            values_a.append(
                struct.unpack_from(">H", record_a, field_offset)[0]
            )
            values_b.append(
                struct.unpack_from(">H", record_b, field_offset)[0]
            )
        else:
            values_a.append(record_a[field_offset])
            values_b.append(record_b[field_offset])

    print()
    print(f"field +0x{field_offset:02x}")

    print(
        "A: "
        + " ".join(f"{value:04x}" for value in values_a)
    )

    print(
        "B: "
        + " ".join(f"{value:04x}" for value in values_b)
    )

    print(
        "B-A: "
        + " ".join(
            f"{right - left:+6d}"
            for left, right in zip(values_a, values_b)
        )
    )
