from pathlib import Path

DB = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database")
data = DB.read_bytes()

TAGS = [
    b"mhfd",
    b"mhsd",
    b"mhli",
    b"mhii",
    b"mhod",
    b"mhni",
    b"mhba",
    b"mhia",
    b"mhlf",
    b"mhif",
]

print("=" * 80)
print("APPLE PHOTO DATABASE TAG SCAN")
print("=" * 80)
print(f"File: {DB}")
print(f"Size: {len(data)} bytes")
print()

print("First 64 bytes:")
print(data[:64].hex(" "))
print()

found = 0

for tag in TAGS:
    variants = [
        ("normal", tag),
        ("reversed", tag[::-1]),
        ("upper", tag.upper()),
    ]

    for kind, pattern in variants:
        start = 0
        offsets = []

        while True:
            offset = data.find(pattern, start)

            if offset == -1:
                break

            offsets.append(offset)
            start = offset + 1

        if offsets:
            found += len(offsets)

            print(
                f"{tag.decode()} {kind:<8}: "
                + ", ".join(
                    f"0x{offset:08x}"
                    for offset in offsets[:20]
                )
            )

print()

if found == 0:
    print("No standard Apple Photo Database tags found.")
else:
    print(f"Total tag occurrences: {found}")

print()
print("Possible single-byte XOR keys for an mhfd header:")

target = b"mhfd"
header = data[:4]

candidates = []

for key in range(256):
    decoded = bytes(
        value ^ key
        for value in header
    )

    if decoded == target or decoded == target[::-1]:
        candidates.append(key)

if candidates:
    for key in candidates:
        decoded = bytes(
            value ^ key
            for value in data[:64]
        )

        print(f"key=0x{key:02x}")
        print(decoded.hex(" "))
else:
    print("none")

print()
print("Done.")
