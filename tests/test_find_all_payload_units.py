from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import csv
import math


PAGE_SIZE = 4096
UNIT_PAGES = 52

# Emplacement réel de tes fichiers .ithmb
ROOT = Path("/home/murph/Desktop/iPod Photo Cache")

OUT = Path("output/all_payload_units_inventory")
OUT.mkdir(parents=True, exist_ok=True)


@dataclass
class PageInfo:
    index: int
    dominant_byte: int
    dominant_ratio: float
    entropy: float
    is_separator: bool


@dataclass
class UnitInfo:
    source: Path
    separator_start: int
    separator_pages: int
    data_start: int
    data_end: int
    cluster_type: str
    normal_pages: int


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0

    counts = Counter(data)
    total = len(data)
    entropy = 0.0

    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)

    return entropy


def classify_page(index: int, page: bytes) -> PageInfo:
    if not page:
        return PageInfo(
            index=index,
            dominant_byte=0,
            dominant_ratio=1.0,
            entropy=0.0,
            is_separator=True,
        )

    counts = Counter(page)
    dominant_byte, dominant_count = counts.most_common(1)[0]

    dominant_ratio = dominant_count / len(page)
    entropy = shannon_entropy(page)

    # Une page séparatrice est généralement presque entièrement
    # remplie d'une même valeur, souvent 0x00 ou 0x01.
    is_separator = (
        dominant_ratio >= 0.97
        or entropy <= 0.40
    )

    return PageInfo(
        index=index,
        dominant_byte=dominant_byte,
        dominant_ratio=dominant_ratio,
        entropy=entropy,
        is_separator=is_separator,
    )


def find_ithmb_files() -> list[Path]:
    if not ROOT.exists():
        raise FileNotFoundError(
            f"Le dossier n'existe pas : {ROOT}"
        )

    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".ithmb"
    )


def read_pages(path: Path) -> list[bytes]:
    data = path.read_bytes()

    pages = []

    for offset in range(0, len(data), PAGE_SIZE):
        page = data[offset:offset + PAGE_SIZE]

        if len(page) == PAGE_SIZE:
            pages.append(page)

    return pages


def count_normal_pages(
    page_infos: list[PageInfo],
    start: int,
    count: int,
) -> int:
    end = min(
        start + count,
        len(page_infos),
    )

    return sum(
        not page_infos[index].is_separator
        for index in range(start, end)
    )


def find_units(
    path: Path,
) -> tuple[list[PageInfo], list[UnitInfo]]:
    pages = read_pages(path)

    page_infos = [
        classify_page(index, page)
        for index, page in enumerate(pages)
    ]

    units: list[UnitInfo] = []

    index = 0

    while index < len(page_infos):
        current = page_infos[index]

        if not current.is_separator:
            index += 1
            continue

        cluster_start = index

        cluster_length = 1

        while (
            cluster_start + cluster_length
            < len(page_infos)
            and page_infos[
                cluster_start + cluster_length
            ].is_separator
            and cluster_length < 4
        ):
            cluster_length += 1

        possibilities = []

        # Les structures déjà observées :
        #
        # Z  + 52 pages
        # ZD + 52 pages
        #
        # On teste donc une séparation de 1 ou 2 pages.
        for separator_length in (1, 2):
            data_start = (
                cluster_start
                + separator_length
            )

            data_end = (
                data_start
                + UNIT_PAGES
                - 1
            )

            if data_end >= len(page_infos):
                continue

            normal_count = count_normal_pages(
                page_infos,
                data_start,
                UNIT_PAGES,
            )

            # Il peut y avoir du padding à l'intérieur,
            # mais la majorité des pages doivent être actives.
            if normal_count >= 35:
                possibilities.append(
                    (
                        normal_count,
                        separator_length,
                        data_start,
                        data_end,
                    )
                )

        if possibilities:
            possibilities.sort(
                key=lambda item: (
                    item[0],
                    -item[1],
                ),
                reverse=True,
            )

            (
                normal_count,
                separator_length,
                data_start,
                data_end,
            ) = possibilities[0]

            cluster_type = (
                "Z"
                if separator_length == 1
                else "ZD"
            )

            units.append(
                UnitInfo(
                    source=path,
                    separator_start=cluster_start,
                    separator_pages=separator_length,
                    data_start=data_start,
                    data_end=data_end,
                    cluster_type=cluster_type,
                    normal_pages=normal_count,
                )
            )

            index = data_end + 1
            continue

        index = (
            cluster_start
            + max(cluster_length, 1)
        )

    return page_infos, units


def main() -> None:
    print("=" * 130)
    print("FIND ALL PAYLOAD UNITS")
    print("=" * 130)
    print(f"Source: {ROOT}")
    print()

    ithmb_files = find_ithmb_files()

    print(
        f"ITHMB files found: "
        f"{len(ithmb_files)}"
    )
    print()

    all_units: list[UnitInfo] = []
    file_rows = []

    for path in ithmb_files:
        try:
            page_infos, units = find_units(path)

        except (OSError, ValueError) as error:
            print(
                f"ERROR {path}: {error}"
            )
            continue

        separator_pages = sum(
            page.is_separator
            for page in page_infos
        )

        z_count = sum(
            unit.cluster_type == "Z"
            for unit in units
        )

        zd_count = sum(
            unit.cluster_type == "ZD"
            for unit in units
        )

        file_rows.append({
            "file": str(path),
            "size_bytes": path.stat().st_size,
            "pages": len(page_infos),
            "separator_pages": separator_pages,
            "units": len(units),
            "z_units": z_count,
            "zd_units": zd_count,
        })

        all_units.extend(units)

        if units:
            print(
                f"{path} | "
                f"pages={len(page_infos):5d} "
                f"separators={separator_pages:4d} "
                f"units={len(units):3d} "
                f"Z={z_count:3d} "
                f"ZD={zd_count:3d}"
            )

    inventory_path = OUT / "units.csv"

    with inventory_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)

        writer.writerow([
            "global_unit",
            "source",
            "cluster_type",
            "separator_start",
            "separator_pages",
            "data_start",
            "data_end",
            "normal_pages",
        ])

        for global_unit, unit in enumerate(all_units):
            writer.writerow([
                global_unit,
                str(unit.source),
                unit.cluster_type,
                unit.separator_start,
                unit.separator_pages,
                unit.data_start,
                unit.data_end,
                unit.normal_pages,
            ])

    files_path = OUT / "files.csv"

    with files_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        fieldnames = [
            "file",
            "size_bytes",
            "pages",
            "separator_pages",
            "units",
            "z_units",
            "zd_units",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        if file_rows:
            writer.writerows(file_rows)

    z_total = sum(
        unit.cluster_type == "Z"
        for unit in all_units
    )

    zd_total = sum(
        unit.cluster_type == "ZD"
        for unit in all_units
    )

    files_with_units = len({
        unit.source
        for unit in all_units
    })

    summary = (
        f"Source: {ROOT}\n"
        f"ITHMB files scanned: {len(ithmb_files)}\n"
        f"Files containing units: {files_with_units}\n"
        f"Total units: {len(all_units)}\n"
        f"Z units: {z_total}\n"
        f"ZD units: {zd_total}\n"
    )

    summary_path = OUT / "summary.txt"

    summary_path.write_text(
        summary,
        encoding="utf-8",
    )

    print()
    print("=" * 130)
    print("SUMMARY")
    print("=" * 130)
    print(summary, end="")
    print()
    print(f"Inventory:   {inventory_path}")
    print(f"File report: {files_path}")
    print(f"Summary:     {summary_path}")


if __name__ == "__main__":
    main()
