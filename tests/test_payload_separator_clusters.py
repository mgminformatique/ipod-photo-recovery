from pathlib import Path
import struct
from collections import Counter, defaultdict

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT = Path("output/payload_separator_clusters.txt")

PAGE_SIZE = 0x400

# Famille possédant les headers séquentiels +1 et les tables 0D.
TARGET_T_NUMBERS = (
    {130}
    | set(range(154, 175))
)

EXCLUDED = {
    157,
    168,
}


def get_t_number(path: Path):
    name = path.stem

    if not name.startswith("T"):
        return None

    try:
        return int(name[1:])
    except ValueError:
        return None


def marker_type(header: int):
    if header == 0x00000000:
        return "Z"

    if header == 0x0D000000:
        return "D"

    return None


def build_clusters(markers):
    """
    Fusionne tous les marqueurs physiquement consécutifs.

    Exemple :
        page 357 Z
        page 358 D

    devient un seul cluster :
        start=357, end=358, pattern=ZD
    """
    if not markers:
        return []

    clusters = []

    current = {
        "start": markers[0][0],
        "end": markers[0][0],
        "types": [markers[0][1]],
    }

    for page_index, kind in markers[1:]:
        if page_index == current["end"] + 1:
            current["end"] = page_index
            current["types"].append(kind)
            continue

        clusters.append(current)

        current = {
            "start": page_index,
            "end": page_index,
            "types": [kind],
        }

    clusters.append(current)

    for cluster in clusters:
        cluster["length"] = (
            cluster["end"] - cluster["start"] + 1
        )
        cluster["pattern"] = "".join(cluster["types"])

    return clusters


files = []

for path in CACHE.rglob("T*.ithmb"):
    t_number = get_t_number(path)

    if (
        t_number in TARGET_T_NUMBERS
        and t_number not in EXCLUDED
    ):
        files.append(path)

files.sort(
    key=lambda path: (
        get_t_number(path),
        str(path.relative_to(CACHE)),
    )
)


report = []

global_cluster_patterns = Counter()
global_start_gaps = Counter()
global_end_to_start_gaps = Counter()
global_data_lengths = Counter()
global_phase_transitions = Counter()

report.append("=" * 150)
report.append("PAYLOAD SEPARATOR CLUSTERS")
report.append("=" * 150)
report.append(f"files={len(files)}")
report.append("")

for path in files:
    raw = path.read_bytes()
    page_count = len(raw) // PAGE_SIZE

    headers = []

    for page_index in range(page_count):
        page = raw[
            page_index * PAGE_SIZE:
            (page_index + 1) * PAGE_SIZE
        ]

        if len(page) != PAGE_SIZE:
            continue

        headers.append(
            struct.unpack_from(">I", page, 0)[0]
        )

    markers = []

    for page_index, header in enumerate(headers):
        kind = marker_type(header)

        if kind is not None:
            markers.append((page_index, kind))

    clusters = build_clusters(markers)

    pattern_counts = Counter(
        cluster["pattern"]
        for cluster in clusters
    )

    global_cluster_patterns.update(pattern_counts)

    start_gaps = []
    end_to_start_gaps = []
    data_lengths = []

    for left, right in zip(clusters, clusters[1:]):
        start_gap = right["start"] - left["start"]

        # Nombre de pages strictement normales entre les clusters.
        data_length = (
            right["start"] - left["end"] - 1
        )

        # Distance entre la dernière page du cluster gauche et
        # la première page du cluster droit.
        end_to_start = right["start"] - left["end"]

        start_gaps.append(start_gap)
        end_to_start_gaps.append(end_to_start)
        data_lengths.append(data_length)

        global_start_gaps[start_gap] += 1
        global_end_to_start_gaps[end_to_start] += 1
        global_data_lengths[data_length] += 1

        left_phase = left["start"] % 53
        right_phase = right["start"] % 53

        global_phase_transitions[
            (
                left_phase,
                right_phase,
                right_phase - left_phase,
            )
        ] += 1

    report.append("=" * 150)
    report.append(str(path.relative_to(CACHE)))
    report.append("=" * 150)

    report.append(
        f"pages={page_count} "
        f"raw_markers={len(markers)} "
        f"clusters={len(clusters)}"
    )

    report.append(
        "patterns: "
        + " ".join(
            f"{pattern}={count}"
            for pattern, count in pattern_counts.most_common()
        )
    )

    report.append("")
    report.append("CLUSTERS")
    report.append("-" * 150)

    for index, cluster in enumerate(clusters):
        previous = (
            clusters[index - 1]
            if index > 0
            else None
        )

        if previous is None:
            start_gap_text = "-"
            data_length_text = "-"
        else:
            start_gap_text = str(
                cluster["start"] - previous["start"]
            )

            data_length_text = str(
                cluster["start"] - previous["end"] - 1
            )

        report.append(
            f"cluster={index:02d} "
            f"pages={cluster['start']:04d}-{cluster['end']:04d} "
            f"length={cluster['length']} "
            f"pattern={cluster['pattern']:4s} "
            f"phase_start={cluster['start'] % 53:02d} "
            f"phase_end={cluster['end'] % 53:02d} "
            f"start_gap={start_gap_text:>4s} "
            f"data_before={data_length_text:>4s}"
        )

    report.append("")
    report.append("START-GAP DISTRIBUTION")
    report.append("-" * 150)

    for gap, count in Counter(start_gaps).most_common():
        report.append(
            f"gap={gap:4d} "
            f"count={count:3d} "
            f"mod53={gap % 53:02d}"
        )

    report.append("")
    report.append("DATA-LENGTH DISTRIBUTION")
    report.append("-" * 150)

    for length, count in Counter(data_lengths).most_common():
        report.append(
            f"normal_pages={length:4d} "
            f"count={count:3d}"
        )

    report.append("")


report.append("=" * 150)
report.append("GLOBAL CLUSTER PATTERNS")
report.append("=" * 150)

for pattern, count in global_cluster_patterns.most_common():
    report.append(
        f"pattern={pattern:8s} "
        f"count={count:4d}"
    )


report.append("")
report.append("=" * 150)
report.append("GLOBAL CLUSTER START GAPS")
report.append("=" * 150)

for gap, count in global_start_gaps.most_common():
    report.append(
        f"gap={gap:4d} "
        f"count={count:4d} "
        f"mod53={gap % 53:02d}"
    )


report.append("")
report.append("=" * 150)
report.append("GLOBAL END-TO-START GAPS")
report.append("=" * 150)

for gap, count in global_end_to_start_gaps.most_common():
    report.append(
        f"gap={gap:4d} "
        f"count={count:4d}"
    )


report.append("")
report.append("=" * 150)
report.append("GLOBAL NORMAL-PAGE LENGTHS BETWEEN CLUSTERS")
report.append("=" * 150)

for length, count in global_data_lengths.most_common():
    report.append(
        f"normal_pages={length:4d} "
        f"count={count:4d}"
    )


report.append("")
report.append("=" * 150)
report.append("GLOBAL PHASE TRANSITIONS")
report.append("=" * 150)

for (
    left_phase,
    right_phase,
    raw_delta,
), count in global_phase_transitions.most_common():
    report.append(
        f"{left_phase:02d}->{right_phase:02d} "
        f"raw_delta={raw_delta:+3d} "
        f"mod_delta={(right_phase-left_phase) % 53:02d} "
        f"count={count:4d}"
    )


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(report) + "\n")

print("=" * 110)
print("PAYLOAD SEPARATOR CLUSTERS")
print("=" * 110)
print(f"files: {len(files)}")
print(f"saved: {OUTPUT}")
print()

print("Global cluster patterns:")
for pattern, count in global_cluster_patterns.most_common():
    print(
        f"  pattern={pattern:8s} "
        f"count={count}"
    )

print()
print("Global normal-page lengths:")
for length, count in global_data_lengths.most_common(20):
    print(
        f"  normal_pages={length:4d} "
        f"count={count}"
    )

print()
print("Global cluster start gaps:")
for gap, count in global_start_gaps.most_common(20):
    print(
        f"  gap={gap:4d} "
        f"count={count} "
        f"mod53={gap % 53:02d}"
    )
