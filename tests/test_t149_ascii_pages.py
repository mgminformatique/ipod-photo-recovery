from pathlib import Path
import struct

FILE = Path("/home/murph/Desktop/iPod Photo Cache/F00/T149.ithmb")

def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]

def decode_val(v):
    hi = v >> 8
    lo = v & 0xff

    if 32 <= hi <= 126 and lo == 0:
        return chr(hi)
    if 32 <= lo <= 126 and hi == 0:
        return chr(lo)
    return "."

def main():
    data = FILE.read_bytes()

    print("=" * 100)
    print("T149 ASCII-LIKE PAGES")
    print("=" * 100)

    for page in range(0, len(data) & ~0xff, 0x100):
        chars = []
        raw_vals = []

        for i in range(128):
            v = u16(data, page + i * 2)
            raw_vals.append(v)
            chars.append(decode_val(v))

        text = "".join(chars)

        score = sum(1 for c in text if c != ".")
        if score >= 8:
            print()
            print("-" * 100)
            print(f"page=0x{page:04x} ascii_score={score}")
            print(text)

            runs = []
            cur = ""
            start = None
            for i, c in enumerate(text):
                if c != ".":
                    if start is None:
                        start = i
                    cur += c
                else:
                    if len(cur) >= 4:
                        runs.append((start, cur))
                    cur = ""
                    start = None
            if len(cur) >= 4:
                runs.append((start, cur))

            for idx, s in runs:
                print(f"  run idx={idx:03d}: {s}")

if __name__ == "__main__":
    main()
