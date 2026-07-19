from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Modules requis : numpy et matplotlib")
    print("Installation : sudo apt install python3-numpy python3-matplotlib")
    sys.exit(1)


CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/stream_periodicity")

TARGETS = [
    "T154.ithmb",
    "T155.ithmb",
    "T170.ithmb",
    "T173.ithmb",
]

# Analyse complète jusqu'à ce décalage.
MAX_LAG = 16384

# On limite la zone analysée pour garder une exécution rapide
# et comparable entre les fichiers.
MAX_ANALYSIS_BYTES = 900_000

# Les très petits décalages ressortent souvent seulement parce que
# les octets voisins appartiennent au même pixel ou à la même structure.
MIN_RANKED_LAG = 8

TOP_COUNT = 100

# Pas que nous voulons vérifier explicitement.
BASE_CANDIDATES = [
    2,
    3,
    4,
    6,
    8,
    12,
    16,
    18,
    24,
    32,
    36,
    48,
    64,
    72,
    96,
    128,
    144,
    180,
    192,
    256,
    288,
    384,
    480,
    512,
    576,
    640,
    720,
    768,
    960,
    1024,
    1152,
    1280,
    1440,
    1536,
    1728,
    1920,
    2048,
    2304,
    2560,
    2880,
    3072,
    3456,
    3840,
    4096,
    4608,
    5120,
    6144,
    6912,
    8192,
    9216,
    12288,
    13824,
]

# Ajoute les équivalents possibles lorsque l'unité est exprimée
# en pixels RGB888 plutôt qu'en octets.
CANDIDATE_LAGS = sorted(
    {
        value
        for base in BASE_CANDIDATES
        for value in (base, base * 2, base * 3, base * 4)
        if 0 < value <= MAX_LAG
    }
)


@dataclass
class LagMetrics:
    lag: int
    autocorr_raw: float
    autocorr_delta: float
    mad: float
    rmse: float
    exact_percent: float
    near_percent: float


def locate_file(filename: str) -> Path | None:
    matches = sorted(CACHE_ROOT.rglob(filename))

    if not matches:
        return None

    return matches[0]


def next_power_of_two(value: int) -> int:
    return 1 << (value - 1).bit_length()


def normalized_autocorrelation(
    signal: np.ndarray,
    max_lag: int,
) -> np.ndarray:
    """
    Calcule l'autocorrélation avec FFT.

    Le résultat à l'index D indique à quel point le flux ressemble
    à lui-même lorsqu'il est décalé de D positions.
    """
    signal = signal.astype(np.float64, copy=False)

    if len(signal) < 2:
        return np.zeros(max_lag + 1, dtype=np.float64)

    signal = signal - np.mean(signal)

    standard_deviation = float(np.std(signal))

    if standard_deviation <= 1e-12:
        return np.zeros(max_lag + 1, dtype=np.float64)

    signal /= standard_deviation

    fft_size = next_power_of_two(len(signal) * 2)

    spectrum = np.fft.rfft(signal, fft_size)
    autocorrelation = np.fft.irfft(
        spectrum * np.conjugate(spectrum),
        fft_size,
    )[: max_lag + 1]

    overlap = len(signal) - np.arange(max_lag + 1)
    overlap = np.maximum(overlap, 1)

    autocorrelation /= overlap

    if autocorrelation[0] != 0:
        autocorrelation /= autocorrelation[0]

    return autocorrelation


def build_delta_signal(raw: np.ndarray) -> np.ndarray:
    """
    Mesure la force des transitions entre octets voisins.

    Cela peut révéler une structure répétée même lorsque la valeur
    absolue des couleurs varie.
    """
    signed = raw.astype(np.int16)
    delta = np.abs(np.diff(signed))

    return delta.astype(np.float64)


def detailed_metrics(
    raw: np.ndarray,
    lag: int,
    autocorr_raw: np.ndarray,
    autocorr_delta: np.ndarray,
) -> LagMetrics | None:
    if lag <= 0 or lag >= len(raw):
        return None

    left = raw[:-lag].astype(np.int16)
    right = raw[lag:].astype(np.int16)

    if len(left) == 0:
        return None

    difference = left - right
    absolute = np.abs(difference)

    mad = float(np.mean(absolute))
    rmse = float(
        np.sqrt(
            np.mean(
                difference.astype(np.float64) ** 2
            )
        )
    )

    exact_percent = float(np.mean(absolute == 0) * 100.0)
    near_percent = float(np.mean(absolute <= 4) * 100.0)

    raw_score = (
        float(autocorr_raw[lag])
        if lag < len(autocorr_raw)
        else 0.0
    )

    delta_score = (
        float(autocorr_delta[lag])
        if lag < len(autocorr_delta)
        else 0.0
    )

    return LagMetrics(
        lag=lag,
        autocorr_raw=raw_score,
        autocorr_delta=delta_score,
        mad=mad,
        rmse=rmse,
        exact_percent=exact_percent,
        near_percent=near_percent,
    )


def local_peak_indices(
    scores: np.ndarray,
    minimum_lag: int,
    maximum_lag: int,
) -> list[int]:
    peaks = []

    upper = min(maximum_lag, len(scores) - 2)

    for lag in range(max(1, minimum_lag), upper + 1):
        value = scores[lag]

        if value >= scores[lag - 1] and value >= scores[lag + 1]:
            peaks.append(lag)

    return peaks


def suppress_near_duplicates(
    ranked_lags: list[int],
    minimum_distance: int = 3,
) -> list[int]:
    selected = []

    for lag in ranked_lags:
        if all(
            abs(lag - existing) > minimum_distance
            for existing in selected
        ):
            selected.append(lag)

    return selected


def rank_lags(
    autocorr_raw: np.ndarray,
    autocorr_delta: np.ndarray,
) -> list[tuple[int, float]]:
    raw_peaks = local_peak_indices(
        autocorr_raw,
        MIN_RANKED_LAG,
        MAX_LAG,
    )

    delta_peaks = local_peak_indices(
        autocorr_delta,
        MIN_RANKED_LAG,
        MAX_LAG,
    )

    candidates = set(raw_peaks) | set(delta_peaks)

    ranked = []

    for lag in candidates:
        raw_score = float(autocorr_raw[lag])
        delta_score = float(autocorr_delta[lag])

        # Le score combiné privilégie un décalage visible dans les
        # octets et/ou dans la structure des transitions.
        combined = (
            max(raw_score, 0.0) * 0.55
            + max(delta_score, 0.0) * 0.45
        )

        ranked.append((lag, combined))

    ranked.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    ordered_lags = [lag for lag, _ in ranked]

    ordered_lags = suppress_near_duplicates(
        ordered_lags,
        minimum_distance=3,
    )

    score_by_lag = dict(ranked)

    return [
        (lag, score_by_lag[lag])
        for lag in ordered_lags[:TOP_COUNT]
    ]


def write_top_lags(
    output_path: Path,
    ranked: list[tuple[int, float]],
    autocorr_raw: np.ndarray,
    autocorr_delta: np.ndarray,
) -> None:
    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)

        writer.writerow(
            [
                "rank",
                "lag_bytes",
                "lag_rgb888_pixels",
                "combined_score",
                "autocorr_raw",
                "autocorr_delta",
                "divisible_by_3",
                "divisible_by_24",
                "divisible_by_48",
                "divisible_by_128",
                "divisible_by_512",
                "divisible_by_2304",
            ]
        )

        for rank, (lag, combined) in enumerate(
            ranked,
            start=1,
        ):
            writer.writerow(
                [
                    rank,
                    lag,
                    (
                        f"{lag / 3:.3f}"
                        if lag % 3
                        else lag // 3
                    ),
                    f"{combined:.9f}",
                    f"{autocorr_raw[lag]:.9f}",
                    f"{autocorr_delta[lag]:.9f}",
                    int(lag % 3 == 0),
                    int(lag % 24 == 0),
                    int(lag % 48 == 0),
                    int(lag % 128 == 0),
                    int(lag % 512 == 0),
                    int(lag % 2304 == 0),
                ]
            )


def write_candidate_metrics(
    output_path: Path,
    metrics: list[LagMetrics],
) -> None:
    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)

        writer.writerow(
            [
                "lag_bytes",
                "lag_rgb888_pixels",
                "autocorr_raw",
                "autocorr_delta",
                "mad",
                "rmse",
                "exact_percent",
                "near_percent_abs_le_4",
            ]
        )

        for metric in metrics:
            writer.writerow(
                [
                    metric.lag,
                    (
                        f"{metric.lag / 3:.3f}"
                        if metric.lag % 3
                        else metric.lag // 3
                    ),
                    f"{metric.autocorr_raw:.9f}",
                    f"{metric.autocorr_delta:.9f}",
                    f"{metric.mad:.6f}",
                    f"{metric.rmse:.6f}",
                    f"{metric.exact_percent:.6f}",
                    f"{metric.near_percent:.6f}",
                ]
            )


def create_plot(
    output_path: Path,
    autocorr_raw: np.ndarray,
    autocorr_delta: np.ndarray,
    title: str,
) -> None:
    maximum = min(
        MAX_LAG,
        len(autocorr_raw) - 1,
        len(autocorr_delta) - 1,
    )

    x = np.arange(1, maximum + 1)

    figure = plt.figure(figsize=(16, 8))
    axis = figure.add_subplot(111)

    axis.plot(
        x,
        autocorr_raw[1 : maximum + 1],
        label="Octets bruts",
        linewidth=0.8,
    )

    axis.plot(
        x,
        autocorr_delta[1 : maximum + 1],
        label="Transitions",
        linewidth=0.8,
        alpha=0.8,
    )

    for lag in [
        48,
        128,
        512,
        1024,
        2304,
        4096,
        6912,
        9216,
        13824,
    ]:
        if lag <= maximum:
            axis.axvline(
                lag,
                linestyle="--",
                linewidth=0.7,
                alpha=0.5,
            )

            axis.text(
                lag,
                axis.get_ylim()[1] * 0.94,
                str(lag),
                rotation=90,
                verticalalignment="top",
                fontsize=8,
            )

    axis.set_title(title)
    axis.set_xlabel("Décalage en octets")
    axis.set_ylabel("Autocorrélation normalisée")
    axis.grid(True, alpha=0.2)
    axis.legend()

    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def process_file(
    filename: str,
) -> tuple[
    list[tuple[int, float]],
    np.ndarray,
    np.ndarray,
] | None:
    path = locate_file(filename)

    if path is None:
        print(f"[ABSENT] {filename}")
        return None

    data = path.read_bytes()

    raw = np.frombuffer(
        data[:MAX_ANALYSIS_BYTES],
        dtype=np.uint8,
    ).copy()

    usable_max_lag = min(
        MAX_LAG,
        len(raw) // 3,
    )

    if usable_max_lag < MIN_RANKED_LAG:
        print(f"[TROP PETIT] {path}")
        return None

    print("=" * 80)
    print(f"Fichier       : {path}")
    print(f"Taille totale : {len(data):,} octets")
    print(f"Zone analysée : {len(raw):,} octets")
    print(f"Lag maximal   : {usable_max_lag:,}")
    print()

    raw_autocorrelation = normalized_autocorrelation(
        raw,
        usable_max_lag,
    )

    delta_signal = build_delta_signal(raw)

    delta_autocorrelation = normalized_autocorrelation(
        delta_signal,
        usable_max_lag,
    )

    ranked = rank_lags(
        raw_autocorrelation,
        delta_autocorrelation,
    )

    file_output = OUTPUT_ROOT / path.stem
    file_output.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_top_lags(
        file_output / "top_lags.csv",
        ranked,
        raw_autocorrelation,
        delta_autocorrelation,
    )

    metrics = []

    for lag in CANDIDATE_LAGS:
        if lag > usable_max_lag:
            continue

        result = detailed_metrics(
            raw,
            lag,
            raw_autocorrelation,
            delta_autocorrelation,
        )

        if result is not None:
            metrics.append(result)

    metrics.sort(
        key=lambda item: (
            -max(item.autocorr_raw, item.autocorr_delta),
            item.mad,
        )
    )

    write_candidate_metrics(
        file_output / "candidate_lags.csv",
        metrics,
    )

    create_plot(
        file_output / "periodicity.png",
        raw_autocorrelation,
        delta_autocorrelation,
        f"{path.stem} — périodicité du flux",
    )

    print("Meilleurs décalages détectés :")
    print()

    print(
        f"{'rang':>4} "
        f"{'lag':>8} "
        f"{'pixels/3':>10} "
        f"{'combiné':>12} "
        f"{'brut':>12} "
        f"{'delta':>12}"
    )

    for rank, (lag, combined) in enumerate(
        ranked[:25],
        start=1,
    ):
        pixel_value = (
            str(lag // 3)
            if lag % 3 == 0
            else f"{lag / 3:.2f}"
        )

        print(
            f"{rank:4d} "
            f"{lag:8d} "
            f"{pixel_value:>10} "
            f"{combined:12.6f} "
            f"{raw_autocorrelation[lag]:12.6f} "
            f"{delta_autocorrelation[lag]:12.6f}"
        )

    print()
    print(f"Résultats : {file_output}")

    return (
        ranked,
        raw_autocorrelation,
        delta_autocorrelation,
    )


def create_consensus(
    results: dict[
        str,
        tuple[
            list[tuple[int, float]],
            np.ndarray,
            np.ndarray,
        ],
    ],
) -> None:
    if not results:
        return

    maximum_common_lag = min(
        len(raw_scores) - 1
        for _, raw_scores, _ in results.values()
    )

    consensus_rows = []

    for lag in range(
        MIN_RANKED_LAG,
        maximum_common_lag + 1,
    ):
        raw_values = []
        delta_values = []

        for _, raw_scores, delta_scores in results.values():
            raw_values.append(float(raw_scores[lag]))
            delta_values.append(float(delta_scores[lag]))

        mean_raw = float(np.mean(raw_values))
        mean_delta = float(np.mean(delta_values))

        positive_raw = max(mean_raw, 0.0)
        positive_delta = max(mean_delta, 0.0)

        consensus_score = (
            positive_raw * 0.55
            + positive_delta * 0.45
        )

        # Récompense un lag qui ressort dans tous les fichiers,
        # plutôt qu'un pic isolé dans un seul.
        consistency = float(
            min(
                np.mean(np.array(raw_values) > 0),
                np.mean(np.array(delta_values) > 0),
            )
        )

        consensus_score *= 0.5 + consistency * 0.5

        consensus_rows.append(
            (
                lag,
                consensus_score,
                mean_raw,
                mean_delta,
                float(np.std(raw_values)),
                float(np.std(delta_values)),
            )
        )

    consensus_rows.sort(
        key=lambda row: row[1],
        reverse=True,
    )

    selected = []
    used_lags = []

    for row in consensus_rows:
        lag = row[0]

        if any(abs(lag - used) <= 3 for used in used_lags):
            continue

        selected.append(row)
        used_lags.append(lag)

        if len(selected) >= 200:
            break

    output_path = OUTPUT_ROOT / "consensus.csv"

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)

        writer.writerow(
            [
                "rank",
                "lag_bytes",
                "lag_rgb888_pixels",
                "consensus_score",
                "mean_autocorr_raw",
                "mean_autocorr_delta",
                "std_autocorr_raw",
                "std_autocorr_delta",
            ]
        )

        for rank, row in enumerate(selected, start=1):
            (
                lag,
                score,
                mean_raw,
                mean_delta,
                std_raw,
                std_delta,
            ) = row

            writer.writerow(
                [
                    rank,
                    lag,
                    (
                        lag // 3
                        if lag % 3 == 0
                        else f"{lag / 3:.3f}"
                    ),
                    f"{score:.9f}",
                    f"{mean_raw:.9f}",
                    f"{mean_delta:.9f}",
                    f"{std_raw:.9f}",
                    f"{std_delta:.9f}",
                ]
            )

    print()
    print("=" * 80)
    print("CONSENSUS ENTRE LES FICHIERS")
    print("=" * 80)

    print(
        f"{'rang':>4} "
        f"{'lag':>8} "
        f"{'pixels/3':>10} "
        f"{'score':>12} "
        f"{'brut':>12} "
        f"{'delta':>12}"
    )

    for rank, row in enumerate(selected[:40], start=1):
        lag, score, mean_raw, mean_delta, _, _ = row

        pixel_value = (
            str(lag // 3)
            if lag % 3 == 0
            else f"{lag / 3:.2f}"
        )

        print(
            f"{rank:4d} "
            f"{lag:8d} "
            f"{pixel_value:>10} "
            f"{score:12.6f} "
            f"{mean_raw:12.6f} "
            f"{mean_delta:12.6f}"
        )

    print()
    print(f"Consensus complet : {output_path}")


def main() -> None:
    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 80)
    print("ITHMB STREAM PERIODICITY ANALYZER")
    print("=" * 80)
    print(f"Cache      : {CACHE_ROOT}")
    print(f"Fichiers   : {', '.join(TARGETS)}")
    print(f"Lag maximal: {MAX_LAG:,} octets")
    print()

    results = {}

    for filename in TARGETS:
        result = process_file(filename)

        if result is not None:
            results[filename] = result

        print()

    create_consensus(results)

    print()
    print("=" * 80)
    print("TERMINÉ")
    print("=" * 80)
    print(f"Dossier : {OUTPUT_ROOT}")
    print()
    print("Fichiers importants :")
    print(f"  {OUTPUT_ROOT}/consensus.csv")
    print(f"  {OUTPUT_ROOT}/T154/top_lags.csv")
    print(f"  {OUTPUT_ROOT}/T154/candidate_lags.csv")
    print(f"  {OUTPUT_ROOT}/T154/periodicity.png")


if __name__ == "__main__":
    main()
