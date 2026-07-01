from pathlib import Path
from collections import Counter
import struct
import math


class BinaryFile:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        self.size = len(self.data)

    def read_bytes(self, offset, length):
        return self.data[offset:offset + length]

    def read_u8(self, offset):
        return self.data[offset]

    def read_u16le(self, offset):
        return struct.unpack_from("<H", self.data, offset)[0]

    def read_u32le(self, offset):
        return struct.unpack_from("<I", self.data, offset)[0]

    def entropy(self, offset=0, length=None):
        chunk = self.data[offset:] if length is None else self.data[offset:offset + length]
        if not chunk:
            return 0.0

        counts = Counter(chunk)
        total = len(chunk)
        return -sum((n / total) * math.log2(n / total) for n in counts.values())

    def hexdump(self, offset=0, length=256):
        chunk = self.read_bytes(offset, length)
        lines = []

        for i in range(0, len(chunk), 16):
            part = chunk[i:i + 16]
            hex_part = " ".join(f"{b:02x}" for b in part)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in part)
            lines.append(f"{offset + i:08x}  {hex_part:<48}  {ascii_part}")

        return "\n".join(lines)
