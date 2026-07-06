from pathlib import Path
import struct

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

TARGETS = [
    CACHE / "F05" / "T154.ithmb",
    CACHE / "F06" / "T155.ithmb",
    CACHE / "F07" / "T156.ithmb",
    CACHE / "F09" / "T158.ithmb",
    CACHE / "F23" / "T172.ithmb",
]

print("OFFSET TABLE SCAN")

for path in TARGETS:
    data = path.read_bytes()
    size = len(data)

    print("=" * 100)
    print(path.relative_to(CACHE), "size", size)

    for endian_name, fmt in [("LE", "<I"), ("BE", ">I")]:
        candidates = []

        for start in range(0, min(size - 4 * 8, 65536), 4):
            vals = []

            for i in range(32):
                off = start + i * 4
                if off + 4 > size:
                    break
                v = struct.unpack_from(fmt, data, off)[0]
                vals.append(v)

            # Garde seulement les valeurs plausibles comme offsets
            good = [v for v in vals if 0 <= v < size]

            if len(good) < 8:
                continue

            # Cherche progression croissante
            ordered = []
            last = -1

            for v in vals:
                if 0 <= v < size and v >= last:
                    ordered.append(v)
                    last = v
                else:
                    break

            if len(ordered) >= 8:
                diffs = [ordered[i+1] - ordered[i] for i in range(len(ordered)-1)]
                nonzero = [d for d in diffs if d > 0]

                if nonzero:
                    avg = sum(nonzero) / len(nonzero)
                    candidates.append((len(ordered), start, endian_name, ordered[:16], diffs[:15], avg))

        candidates.sort(reverse=True)

        for count, start, endian, vals, diffs, avg in candidates[:20]:
            print(
                f"{endian} start=0x{start:06x} "
                f"count={count} avg_diff={avg:.1f}"
            )
            print("  vals:", [hex(v) for v in vals])
            print("  diffs:", diffs)

print("done")
