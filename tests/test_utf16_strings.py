from pathlib import Path
import re

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F08/T157.ithmb",
]

def extract_utf16le_strings(data, min_chars=4):
    text = data.decode("utf-16le", errors="ignore")
    matches = re.findall(r"[ -~]{%d,}" % min_chars, text)
    return matches

for path in FILES:
    p = Path(path)
    data = p.read_bytes()

    print("=" * 80)
    print(p)
    print("Size:", len(data))

    strings = extract_utf16le_strings(data)

    for s in strings[:80]:
        print(repr(s))

    print("Total strings:", len(strings))
