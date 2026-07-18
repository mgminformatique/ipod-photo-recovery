from __future__ import annotations

from pathlib import Path
import csv
import io
import struct
import zlib


ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUT = Path("output/validated_embedded_formats")

JPEG_OUT = OUT / "jpeg"
ZLIB_OUT = OUT / "zlib"

JPEG_OUT.mkdir(parents=True, exist_ok=True)
ZLIB_OUT.mkdir(parents=True, exist_ok=True)

MAX_ZLIB_OUTPUT = 64 * 1024 * 1024
MAX_JPEG_SEARCH_BACK = 64 * 1024
MAX_JPEG_SIZE = 32 * 1024 * 1024

ZLIB_HEADERS = (
    b"\x78\x01",
    b"\x78\x5e",
    b"\x78\x9c",
    b"\x78\xda",
)


def safe_name(path: Path) -> str:
    relative = path.relative_to(ROOT)

    return "__".join(relative.parts).replace("/", "_")


def find_all(data: bytes, needle: bytes):
    start = 0

    while True:
        offset = data.find(needle, start)

        if offset < 0:
            break

        yield offset
        start = offset + 1


def validate_zlib_stream(
    data: bytes,
    offset: int,
) -> tuple[bool, bytes, int, str]:
    try:
        decompressor = zlib.decompressobj()

        compressed = data[offset:]
        output = decompressor.decompress(
            compressed,
            MAX_ZLIB_OUTPUT,
        )

        if len(output) >= MAX_ZLIB_OUTPUT:
            return (
                False,
                b"",
                0,
                "output_limit_reached",
            )

        output += decompressor.flush()

        if not decompressor.eof:
            return (
                False,
                b"",
                0,
                "stream_not_complete",
            )

        consumed = (
            len(compressed)
            - len(decompressor.unused_data)
        )

        if consumed <= 2:
            return (
                False,
                b"",
                0,
                "too_short",
            )

        if not output:
            return (
                False,
                b"",
                consumed,
                "empty_output",
            )

        return (
            True,
            output,
            consumed,
            "valid",
        )

    except zlib.error as exc:
        return (
            False,
            b"",
            0,
            f"zlib_error:{exc}",
        )


def locate_jpeg_start(
    data: bytes,
    jfif_offset: int,
) -> int | None:
    search_start = max(
        0,
        jfif_offset - MAX_JPEG_SEARCH_BACK,
    )

    candidate = data.rfind(
        b"\xff\xd8\xff",
        search_start,
        jfif_offset + 1,
    )

    if candidate < 0:
        return None

    return candidate


def parse_jpeg_end(
    data: bytes,
    start: int,
) -> tuple[int | None, str]:
    if data[start:start + 2] != b"\xff\xd8":
        return None, "missing_soi"

    position = start + 2
    data_length = len(data)

    try:
        while position < data_length:
            if data[position] != 0xFF:
                position += 1
                continue

            while (
                position < data_length
                and data[position] == 0xFF
            ):
                position += 1

            if position >= data_length:
                return None, "unexpected_eof_after_ff"

            marker = data[position]
            position += 1

            if marker == 0xD9:
                return position, "valid"

            if marker == 0xDA:
                while position < data_length - 1:
                    if (
                        data[position] == 0xFF
                        and data[position + 1] == 0xD9
                    ):
                        return position + 2, "valid"

                    if (
                        data[position] == 0xFF
                        and data[position + 1] == 0x00
                    ):
                        position += 2
                        continue

                    position += 1

                return None, "missing_eoi_after_sos"

            if marker in {
                0x01,
                0xD0,
                0xD1,
                0xD2,
                0xD3,
                0xD4,
                0xD5,
                0xD6,
                0xD7,
            }:
                continue

            if position + 2 > data_length:
                return None, "truncated_segment_length"

            segment_length = struct.unpack(
                ">H",
                data[position:position + 2],
            )[0]

            if segment_length < 2:
                return None, "invalid_segment_length"

            position += segment_length

            if position - start > MAX_JPEG_SIZE:
                return None, "jpeg_too_large"

        return None, "unexpected_eof"

    except Exception as exc:
        return None, f"parse_error:{exc}"


def classify_output(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"

    if data.startswith(b"GIF87a"):
        return "GIF87a"

    if data.startswith(b"GIF89a"):
        return "GIF89a"

    if data.startswith(b"BM"):
        return "BMP"

    if data.startswith(b"II\x2a\x00"):
        return "TIFF_LE"

    if data.startswith(b"MM\x00\x2a"):
        return "TIFF_BE"

    if data.startswith(b"PK\x03\x04"):
        return "ZIP"

    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "MP4_FTYP"

    printable = sum(
        32 <= value <= 126
        or value in {9, 10, 13}
        for value in data[:4096]
    )

    if data and printable / min(len(data), 4096) >= 0.85:
        return "TEXT_LIKE"

    return "BINARY"


def main() -> None:
    files = sorted(ROOT.rglob("*.ithmb"))

    if not files:
        raise FileNotFoundError(
            f"Aucun .ithmb trouvé dans {ROOT}"
        )

    zlib_rows = []
    jpeg_rows = []

    total_zlib_candidates = 0
    total_valid_zlib = 0
    total_jfif_candidates = 0
    total_valid_jpeg = 0

    print("=" * 110)
    print("VALIDATION DES FORMATS EMBARQUÉS")
    print("=" * 110)
    print(f"Source: {ROOT}")
    print(f"Fichiers: {len(files)}")
    print()

    for path in files:
        data = path.read_bytes()
        base = safe_name(path)

        valid_zlib_for_file = 0
        valid_jpeg_for_file = 0

        seen_zlib_offsets = set()

        for header in ZLIB_HEADERS:
            for offset in find_all(data, header):
                if offset in seen_zlib_offsets:
                    continue

                seen_zlib_offsets.add(offset)
                total_zlib_candidates += 1

                (
                    valid,
                    output,
                    consumed,
                    status,
                ) = validate_zlib_stream(
                    data,
                    offset,
                )

                output_type = ""
                output_path = ""

                if valid:
                    total_valid_zlib += 1
                    valid_zlib_for_file += 1

                    output_type = classify_output(output)

                    filename = (
                        f"{base}__off_{offset:010d}"
                        f"__compressed_{consumed}"
                        f"__output_{len(output)}"
                        f"__{output_type}.bin"
                    )

                    destination = ZLIB_OUT / filename
                    destination.write_bytes(output)
                    output_path = str(destination)

                zlib_rows.append({
                    "file": str(path),
                    "offset": offset,
                    "header": header.hex(),
                    "valid": valid,
                    "status": status,
                    "compressed_bytes_consumed": consumed,
                    "output_bytes": len(output),
                    "output_type": output_type,
                    "output_path": output_path,
                })

        jfif_offsets = sorted(
            set(find_all(data, b"JFIF"))
        )

        total_jfif_candidates += len(jfif_offsets)

        seen_jpeg_ranges = set()

        for jfif_offset in jfif_offsets:
            start = locate_jpeg_start(
                data,
                jfif_offset,
            )

            if start is None:
                jpeg_rows.append({
                    "file": str(path),
                    "jfif_offset": jfif_offset,
                    "jpeg_start": "",
                    "jpeg_end": "",
                    "jpeg_size": "",
                    "valid": False,
                    "status": "no_soi_before_jfif",
                    "output_path": "",
                })
                continue

            end, status = parse_jpeg_end(
                data,
                start,
            )

            if end is None:
                jpeg_rows.append({
                    "file": str(path),
                    "jfif_offset": jfif_offset,
                    "jpeg_start": start,
                    "jpeg_end": "",
                    "jpeg_size": "",
                    "valid": False,
                    "status": status,
                    "output_path": "",
                })
                continue

            key = (start, end)

            if key in seen_jpeg_ranges:
                continue

            seen_jpeg_ranges.add(key)

            jpeg_data = data[start:end]

            filename = (
                f"{base}"
                f"__start_{start:010d}"
                f"__end_{end:010d}.jpg"
            )

            destination = JPEG_OUT / filename
            destination.write_bytes(jpeg_data)

            total_valid_jpeg += 1
            valid_jpeg_for_file += 1

            jpeg_rows.append({
                "file": str(path),
                "jfif_offset": jfif_offset,
                "jpeg_start": start,
                "jpeg_end": end,
                "jpeg_size": len(jpeg_data),
                "valid": True,
                "status": "valid",
                "output_path": str(destination),
            })

        if valid_zlib_for_file or valid_jpeg_for_file:
            print(
                f"{path.relative_to(ROOT)} | "
                f"valid_zlib={valid_zlib_for_file} | "
                f"valid_jpeg={valid_jpeg_for_file}"
            )

    zlib_csv = OUT / "zlib_validation.csv"

    with zlib_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "offset",
                "header",
                "valid",
                "status",
                "compressed_bytes_consumed",
                "output_bytes",
                "output_type",
                "output_path",
            ],
        )

        writer.writeheader()
        writer.writerows(zlib_rows)

    jpeg_csv = OUT / "jpeg_validation.csv"

    with jpeg_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "jfif_offset",
                "jpeg_start",
                "jpeg_end",
                "jpeg_size",
                "valid",
                "status",
                "output_path",
            ],
        )

        writer.writeheader()
        writer.writerows(jpeg_rows)

    valid_zlib_rows = [
        row
        for row in zlib_rows
        if row["valid"]
    ]

    valid_jpeg_rows = [
        row
        for row in jpeg_rows
        if row["valid"]
    ]

    summary_lines = [
        f"Source: {ROOT}",
        f"Files scanned: {len(files)}",
        "",
        f"Zlib candidates: {total_zlib_candidates}",
        f"Valid zlib streams: {total_valid_zlib}",
        "",
        f"JFIF candidates: {total_jfif_candidates}",
        f"Valid JPEG files: {total_valid_jpeg}",
        "",
        "Valid zlib outputs by type:",
    ]

    type_counts = {}

    for row in valid_zlib_rows:
        output_type = row["output_type"]

        type_counts[output_type] = (
            type_counts.get(output_type, 0)
            + 1
        )

    if type_counts:
        for output_type, count in sorted(
            type_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            summary_lines.append(
                f"  {output_type}: {count}"
            )
    else:
        summary_lines.append("  none")

    summary_lines.extend([
        "",
        "Largest valid zlib outputs:",
    ])

    if valid_zlib_rows:
        for row in sorted(
            valid_zlib_rows,
            key=lambda item: int(item["output_bytes"]),
            reverse=True,
        )[:30]:
            summary_lines.append(
                f"  {int(row['output_bytes']):10d} bytes | "
                f"{row['output_type']:<10} | "
                f"offset={int(row['offset']):10d} | "
                f"{Path(row['file']).parent.name}/"
                f"{Path(row['file']).name}"
            )
    else:
        summary_lines.append("  none")

    summary_lines.extend([
        "",
        "Valid JPEG files:",
    ])

    if valid_jpeg_rows:
        for row in valid_jpeg_rows:
            summary_lines.append(
                f"  {int(row['jpeg_size']):10d} bytes | "
                f"start={int(row['jpeg_start']):10d} | "
                f"{Path(row['file']).parent.name}/"
                f"{Path(row['file']).name}"
            )
    else:
        summary_lines.append("  none")

    summary_path = OUT / "summary.txt"

    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 110)
    print("RÉSULTAT")
    print("=" * 110)
    print("\n".join(summary_lines))
    print()
    print(f"Résumé:    {summary_path}")
    print(f"Zlib CSV:  {zlib_csv}")
    print(f"JPEG CSV:  {jpeg_csv}")
    print(f"Zlib dir:  {ZLIB_OUT}")
    print(f"JPEG dir:  {JPEG_OUT}")


if __name__ == "__main__":
    main()
