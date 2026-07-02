from pathlib import Path
from collections import Counter
import math


class PhotoDatabase:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        self.size = len(self.data)

    def entropy(self, data):
        if not data:
            return 0.0
        counts = Counter(data)
        total = len(data)
        return -sum((n / total) * math.log2(n / total) for n in counts.values())

    def scan_blocks(self, block_size=512):
        blocks = []

        for offset in range(0, self.size, block_size):
            chunk = self.data[offset:offset + block_size]

            blocks.append({
                "offset": offset,
                "size": len(chunk),
                "entropy": round(self.entropy(chunk), 3),
                "zeros": chunk.count(0),
                "ff": chunk.count(255),
                "first16": chunk[:16].hex(" "),
            })

        return blocks

    def find_low_entropy_blocks(self, block_size=512, max_entropy=6.5):
        return [
            b for b in self.scan_blocks(block_size)
            if b["entropy"] <= max_entropy
        ]

    def hexdump(self, offset=0, length=256):
        chunk = self.data[offset:offset + length]
        lines = []

        for i in range(0, len(chunk), 16):
            part = chunk[i:i + 16]
            hex_part = " ".join(f"{b:02x}" for b in part)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in part)
            lines.append(f"{offset+i:08x}  {hex_part:<48}  {ascii_part}")

        return "\n".join(lines)
