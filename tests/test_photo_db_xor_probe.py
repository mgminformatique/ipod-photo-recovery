from pathlib import Path

data = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database").read_bytes()

signatures = [
    b"mhbd",
    b"mhsd",
    b"mhii",
    b"mhod",
    b"SQLite",
    b"bplist",
    b"Photo",
    b"Album",
    b"F00",
    b"T154",
]

for key in range(256):
    decoded = bytes(b ^ key for b in data[:4096])

    hits = []
    for sig in signatures:
        if sig in decoded:
            hits.append(sig.decode(errors="ignore"))

    if hits:
        print("XOR key:", key, "hits:", hits)
