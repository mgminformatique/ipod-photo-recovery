from pathlib import Path

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
]

guid = "00262001-0002-0010-FBB3-AB02A8125552"
needle = guid.encode("utf-16le")

for path in FILES:
    p = Path(path)
    data = p.read_bytes()

    print("=" * 80)
    print(p)
    print("Size:", len(data))

    pos = 0
    hits = []

    while True:
        idx = data.find(needle, pos)
        if idx == -1:
            break
        hits.append(idx)
        pos = idx + 2

    print("GUID hits:", len(hits))
    for h in hits:
        print("offset:", h, "hex:", hex(h))

    print("Distances:")
    for a, b in zip(hits, hits[1:]):
        print(b - a)
