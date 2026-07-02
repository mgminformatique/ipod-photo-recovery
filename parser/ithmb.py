from pathlib import Path
from core.binary import BinaryFile


class ITHMBFile:
    def __init__(self, path):
        self.path = Path(path)
        self.binary = BinaryFile(path)
        self.size = self.binary.size

    def frame_layouts(self, candidates):
        layouts = []

        for c in candidates:
            frame_size = c["frame_size"]
            if frame_size <= 0:
                continue

            frames = self.size // frame_size
            remainder = self.size % frame_size

            layouts.append({
                "width": c["width"],
                "height": c["height"],
                "format": c["format"],
                "frame_size": frame_size,
                "frames": frames,
                "remainder": remainder,
                "possible_footer": remainder,
                "possible_header": remainder,
            })

        return sorted(layouts, key=lambda x: x["remainder"])
