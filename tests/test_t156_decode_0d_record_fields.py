from pathlib import Path
import struct

SRC = Path("/home/murph/Desktop/iPod Photo Cache/F07/T156.ithmb")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
MARKER_PAGES = [358, 783]

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8

raw = SRC.read_bytes()

print("=" * 110)
print("T156 0D RECORD FIELD DECODER")
print("=" * 110)

for page_index in MARKER_PAGES:
    page = raw[
        page_index * PAGE_SIZE:
        (page_index + 1) * PAGE_SIZE
    ]

    payload = page[HEADER_SIZE:]

    print()
    print("-" * 110)
    print(f"PAGE {page_index}")
    print("-" * 110)

    for record_index in range(RECORD_COUNT):
        start = RECORD_START + record_index * RECORD_SIZE
        record = payload[start:start + RECORD_SIZE]

        print()
        print(
            f"record={record_index:02d} "
            f"range=0x{start:03x}-0x{start + RECORD_SIZE - 1:03x}"
        )

        print(
            f"  byte_04=0x{record[0x04]:02x} "
            f"byte_57=0x{record[0x57]:02x}"
        )

        for offset in [
            0x00, 0x02, 0x04, 0x06,
            0x0C, 0x10, 0x20, 0x30,
            0x40, 0x50, 0x56, 0x57,
            0x58, 0x5A, 0x60, 0x68,
            0x6C, 0x6E
        ]:
            if offset + 2 <= len(record):
                be = struct.unpack_from(">H", record, offset)[0]
                le = struct.unpack_from("<H", record, offset)[0]

                print(
                    f"  off=0x{offset:02x} "
                    f"BE=0x{be:04x} ({be:5d}) "
                    f"LE=0x{le:04x} ({le:5d})"
                )

        print("  last16:")
        print(
            "   "
            + " ".join(f"{b:02x}" for b in record[-16:])
        )
