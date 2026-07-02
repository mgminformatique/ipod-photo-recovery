from pathlib import Path
from core.binary import BinaryFile

COMMON_SIZES = [
    (120, 120),
    (130, 88),
    (176, 220),
    (220, 176),
    (320, 240),
    (720, 480),
]


class ITHMBAnalyzer:
    def __init__(self, path):
        self.path = Path(path)
        self.binary = BinaryFile(path)

    def candidate_frames(self):
        size = self.binary.size
        results = []

        for w, h in COMMON_SIZES:
            formats = [
                ("RGB888", w * h * 3),
                ("RGB565", w * h * 2),
                ("YCbCr420", int(w * h * 1.5)),
            ]

            for fmt, frame_size in formats:
                frames = size // frame_size
                remainder = size % frame_size

                if frames > 0:
                    results.append({
                        "width": w,
                        "height": h,
                        "format": fmt,
                        "frame_size": frame_size,
                        "frames": frames,
                        "remainder": remainder,
                    })

        return sorted(results, key=lambda r: (r["remainder"], -r["frames"]))
