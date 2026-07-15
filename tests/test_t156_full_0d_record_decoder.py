from pathlib import Path
import struct
import math
import hashlib
import zlib
from collections import Counter

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4

MARKER_PAGES = [358, 783]

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8


def entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)

    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def ascii_text(data: bytes) -> str:
    return "".join(
        chr(value) if 32 <= value <= 126 else "."
        for value in data
    )


def decode_utf16le_runs(data: bytes):
    runs = []
    start = None
    chars = []

    for offset in range(0, len(data) - 1, 2):
        low = data[offset]
        high = data[offset + 1]

        valid = (
            high == 0
            and (
                48 <= low <= 57
                or 65 <= low <= 90
                or 97 <= low <= 122
                or low in b"-_{}()[]"
            )
        )

        if valid:
            if start is None:
                start = offset

            chars.append(chr(low))
        else:
            if start is not None and len(chars) >= 4:
                runs.append((start, offset - 1, "".join(chars)))

            start = None
            chars = []

    if start is not None and len(chars) >= 4:
        runs.append((start, len(data) - 1, "".join(chars)))

    return runs


def read_payload(raw: bytes, page_index: int) -> bytes:
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


raw = SRC.read_bytes()

payloads = {
    page_index: read_payload(raw, page_index)
    for page_index in MARKER_PAGES
}

records_by_page = {}

print("=" * 128)
print("T156 FULL 0D RECORD DECODER")
print("=" * 128)

for page_index in MARKER_PAGES:
    payload = payloads[page_index]
    records = []

    print()
    print("=" * 128)
    print(f"PAGE {page_index}")
    print("=" * 128)

    for record_index in range(RECORD_COUNT):
        start = RECORD_START + record_index * RECORD_SIZE
        end = start + RECORD_SIZE
        record = payload[start:end]

        records.append(record)

        print()
        print("-" * 128)
        print(
            f"RECORD {record_index:02d} "
            f"payload_range=0x{start:03x}-0x{end - 1:03x}"
        )
        print("-" * 128)

        print(f"entropy={entropy(record):.4f}")
        print(f"crc32=0x{zlib.crc32(record) & 0xffffffff:08x}")
        print(f"md5={hashlib.md5(record).hexdigest()}")
        print(f"sha1={hashlib.sha1(record).hexdigest()}")
        print()

        print("HEX + ASCII")

        for row_start in range(0, RECORD_SIZE, 16):
            row = record[row_start:row_start + 16]

            print(
                f"+0x{row_start:02x}  "
                + " ".join(f"{value:02x}" for value in row).ljust(47)
                + f"  |{ascii_text(row)}|"
            )

        print()
        print("UTF-16LE TEXT RUNS")

        runs = decode_utf16le_runs(record)

        if not runs:
            print("  none")
        else:
            for run_start, run_end, text in runs:
                print(
                    f"  +0x{run_start:02x}-0x{run_end:02x}: "
                    f"{text!r}"
                )

        print()
        print("ALIGNED U16 FIELDS")

        for offset in range(0, RECORD_SIZE - 1, 2):
            be = struct.unpack_from(">H", record, offset)[0]
            le = struct.unpack_from("<H", record, offset)[0]

            print(
                f"  +0x{offset:02x} "
                f"BE=0x{be:04x} {be:5d} "
                f"LE=0x{le:04x} {le:5d}"
            )

        print()
        print("ALIGNED U32 FIELDS")

        for offset in range(0, RECORD_SIZE - 3, 4):
            be = struct.unpack_from(">I", record, offset)[0]
            le = struct.unpack_from("<I", record, offset)[0]

            print(
                f"  +0x{offset:02x} "
                f"BE=0x{be:08x} {be:10d} "
                f"LE=0x{le:08x} {le:10d}"
            )

        field_04_u8 = record[0x04]
        field_04_le16 = struct.unpack_from("<H", record, 0x04)[0]

        field_57_u8 = record[0x57]
        field_56_be16 = struct.unpack_from(">H", record, 0x56)[0]

        field_6e_be16 = struct.unpack_from(">H", record, 0x6E)[0]
        field_6c_be32 = struct.unpack_from(">I", record, 0x6C)[0]

        print()
        print("TARGET FIELD SUMMARY")
        print(
            f"  field_04_u8       =0x{field_04_u8:02x} "
            f"({field_04_u8})"
        )
        print(
            f"  field_04_le16     =0x{field_04_le16:04x} "
            f"({field_04_le16})"
        )
        print(
            f"  field_57_u8       =0x{field_57_u8:02x} "
            f"({field_57_u8})"
        )
        print(
            f"  field_56_be16     =0x{field_56_be16:04x} "
            f"({field_56_be16})"
        )
        print(
            f"  field_6e_be16     =0x{field_6e_be16:04x} "
            f"({field_6e_be16})"
        )
        print(
            f"  field_6c_be32     =0x{field_6c_be32:08x} "
            f"({field_6c_be32})"
        )

        print()
        print("POSSIBLE OFFSET TRANSFORMS")

        candidates = {
            "field04_u8": field_04_u8,
            "field04_le16": field_04_le16,
            "field57_u8": field_57_u8,
            "field56_be16": field_56_be16,
            "field6e_be16": field_6e_be16,
            "field6c_be32": field_6c_be32,
        }

        multipliers = [
            1,
            4,
            16,
            112,
            1020,
            1024,
            4092,
            4096,
            53040,
        ]

        for name, value in candidates.items():
            print(f"  {name}={value}")

            for multiplier in multipliers:
                result = value * multiplier

                print(
                    f"    x{multiplier:5d} "
                    f"= {result:12d} "
                    f"0x{result:08x}"
                )

    records_by_page[page_index] = records


print()
print("=" * 128)
print("CROSS-RECORD STRUCTURED TABLE")
print("=" * 128)

for page_index in MARKER_PAGES:
    print()
    print(f"PAGE {page_index}")
    print(
        "rec  "
        "f04  f04_le16  "
        "f57  f56_be16  "
        "f6e_be16  f6c_be32  "
        "delta04  delta57  delta6e"
    )

    previous = None

    for record_index, record in enumerate(records_by_page[page_index]):
        f04 = record[0x04]
        f04_le16 = struct.unpack_from("<H", record, 0x04)[0]
        f57 = record[0x57]
        f56_be16 = struct.unpack_from(">H", record, 0x56)[0]
        f6e = struct.unpack_from(">H", record, 0x6E)[0]
        f6c = struct.unpack_from(">I", record, 0x6C)[0]

        if previous is None:
            delta04 = delta57 = delta6e = "-"
        else:
            delta04 = f"{f04 - previous[0]:+d}"
            delta57 = f"{f57 - previous[1]:+d}"
            delta6e = f"{f6e - previous[2]:+d}"

        print(
            f"{record_index:02d}   "
            f"{f04:3d}  {f04_le16:8d}  "
            f"{f57:3d}  {f56_be16:8d}  "
            f"{f6e:8d}  {f6c:9d}  "
            f"{delta04:>7s}  "
            f"{delta57:>7s}  "
            f"{delta6e:>7s}"
        )

        previous = (f04, f57, f6e)


print()
print("=" * 128)
print("PAGE A VS PAGE B")
print("=" * 128)

records_a = records_by_page[MARKER_PAGES[0]]
records_b = records_by_page[MARKER_PAGES[1]]

print(
    "rec  "
    "A_f04 B_f04 diff04  "
    "A_f57 B_f57 diff57  "
    "A_f6e B_f6e diff6e"
)

for record_index, (record_a, record_b) in enumerate(
    zip(records_a, records_b)
):
    a04 = record_a[0x04]
    b04 = record_b[0x04]

    a57 = record_a[0x57]
    b57 = record_b[0x57]

    a6e = struct.unpack_from(">H", record_a, 0x6E)[0]
    b6e = struct.unpack_from(">H", record_b, 0x6E)[0]

    print(
        f"{record_index:02d}   "
        f"{a04:5d} {b04:5d} {b04-a04:+6d}  "
        f"{a57:5d} {b57:5d} {b57-a57:+6d}  "
        f"{a6e:5d} {b6e:5d} {b6e-a6e:+6d}"
    )
