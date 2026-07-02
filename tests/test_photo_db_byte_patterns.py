from pathlib import Path
from collections import Counter

data = Path("/home/murph/Desktop/iPod Photo Cache/Photo Database").read_bytes()

print("Photo Database byte pattern scan")
print("Size:", len(data))
print("=" * 80)

print("Top bytes:")
for byte, count in Counter(data).most_common(20):
    print(f"0x{byte:02x} {count}")

print()
print("Top 2-byte aligned words:")
words = [data[i:i+2] for i in range(0, len(data)-1, 2)]
for word, count in Counter(words).most_common(20):
    print(f"{word.hex(' ')} {count}")

print()
print("Top 4-byte aligned dwords:")
dwords = [data[i:i+4] for i in range(0, len(data)-3, 4)]
for dword, count in Counter(dwords).most_common(20):
    print(f"{dword.hex(' ')} {count}")
