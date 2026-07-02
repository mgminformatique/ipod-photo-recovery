from pathlib import Path

db = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database").read_bytes()

guid = "00262001-0002-0010-FBB3-AB02A8125552"

patterns = {
    "utf16le": guid.encode("utf-16le"),
    "ascii": guid.encode("ascii"),
}

for name, pattern in patterns.items():
    hits = []
    pos = 0

    while True:
        idx = db.find(pattern, pos)
        if idx == -1:
            break
        hits.append(idx)
        pos = idx + 1

    print(name, "hits:", len(hits), hits[:20])
