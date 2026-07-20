from __future__ import annotations

import bz2
import gzip
import lzma
import math
import struct
import zlib
from collections import Counter
from pathlib import Path

CACHE_ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
OUTPUT_ROOT = Path("output/photo_database_strict_stream_probe")

MIN_OUTPUT = 32
MAX_OUTPUT = 128 * 1024 * 1024

MAGIC_MARKERS = {
    b"bplist00": "Apple binary plist",
    b"<?xml": "XML",
    b"SQLite format 3\x00": "SQLite",
    b"mhfd": "iPod Photo mhfd",
    b"mhii": "iPod Photo mhii",
    b"mhni": "iPod Photo mhni",
    b"mhif": "iPod Photo mhif",
    b"mhli": "iPod Photo mhli",
    b"mhia": "iPod Photo mhia",
    b"mhla": "iPod Photo mhla",
    b"mhsd": "Apple mhsd",
    b"mhbd": "iTunesDB mhbd",
    b"PK\x03\x04": "ZIP",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"\xff\xd8\xff": "JPEG",
}


def find_database() -> Path:
    matches = sorted(CACHE_ROOT.rglob("Photo Database"))
    if not matches:
        raise FileNotFoundError(f"Photo Database introuvable sous {CACHE_ROOT}")
    return matches[0]


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13)) / len(data)


def zero_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return data.count(0) / len(data)


def marker_hits(data: bytes) -> list[tuple[int, str]]:
    hits = []
    for marker, label in MAGIC_MARKERS.items():
        start = 0
        while True:
            pos = data.find(marker, start)
            if pos < 0:
                break
            hits.append((pos, label))
            start = pos + 1
    return sorted(hits)


def valid_zlib_header(data: bytes, offset: int) -> bool:
    if offset + 2 > len(data):
        return False

    cmf = data[offset]
    flg = data[offset + 1]

    # Compression method must be DEFLATE (8).
    if (cmf & 0x0F) != 8:
        return False

    # CINFO <= 7, meaning a window no larger than 32 KiB.
    if (cmf >> 4) > 7:
        return False

    # RFC 1950 header checksum.
    if ((cmf << 8) | flg) % 31 != 0:
        return False

    return True


def try_zlib(data: bytes, offset: int, wbits: int) -> tuple[bytes, int] | None:
    obj = zlib.decompressobj(wbits)
    try:
        decoded = obj.decompress(data[offset:], MAX_OUTPUT)
        decoded += obj.flush()
    except zlib.error:
        return None

    if not obj.eof:
        return None
    if len(decoded) < MIN_OUTPUT:
        return None

    consumed = len(data[offset:]) - len(obj.unused_data)
    return decoded, consumed


def try_bz2(data: bytes, offset: int) -> tuple[bytes, int] | None:
    obj = bz2.BZ2Decompressor()
    try:
        decoded = obj.decompress(data[offset:], MAX_OUTPUT)
    except (OSError, EOFError, ValueError):
        return None

    if not obj.eof or len(decoded) < MIN_OUTPUT:
        return None

    consumed = len(data[offset:]) - len(obj.unused_data)
    return decoded, consumed


def try_lzma(data: bytes, offset: int) -> tuple[bytes, int] | None:
    obj = lzma.LZMADecompressor()
    try:
        decoded = obj.decompress(data[offset:], MAX_OUTPUT)
    except (lzma.LZMAError, EOFError, ValueError):
        return None

    if not obj.eof or len(decoded) < MIN_OUTPUT:
        return None

    consumed = len(data[offset:]) - len(obj.unused_data)
    return decoded, consumed


def save_stream(rank: int, kind: str, offset: int, decoded: bytes) -> Path:
    folder = OUTPUT_ROOT / "decoded_streams"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{rank:03d}_{kind}_offset_{offset:08x}.bin"
    path.write_bytes(decoded)
    return path


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    db_path = find_database()
    data = db_path.read_bytes()

    print("=" * 100)
    print("PHOTO DATABASE STRICT STREAM PROBE")
    print("=" * 100)
    print(f"Fichier          : {db_path}")
    print(f"Taille           : {len(data):,}")
    print(f"Entropie         : {entropy(data):.6f}")
    print(f"Ratio imprimable : {printable_ratio(data):.6f}")
    print(f"Ratio zéros      : {zero_ratio(data):.6f}")
    print()

    candidates = []

    valid_zlib_offsets = [
        offset for offset in range(len(data) - 1)
        if valid_zlib_header(data, offset)
    ]

    gzip_offsets = [
        offset for offset in range(len(data) - 9)
        if data[offset:offset + 2] == b"\x1f\x8b"
        and data[offset + 2] == 8
        and (data[offset + 3] & 0xE0) == 0
    ]

    bz2_offsets = [
        offset for offset in range(len(data) - 3)
        if data[offset:offset + 3] == b"BZh"
        and data[offset + 3:offset + 4] in b"123456789"
    ]

    xz_offsets = [
        offset for offset in range(len(data) - 5)
        if data[offset:offset + 6] == b"\xfd7zXZ\x00"
    ]

    print(f"En-têtes ZLIB valides mathématiquement : {len(valid_zlib_offsets)}")
    print(f"En-têtes GZIP complets possibles       : {len(gzip_offsets)}")
    print(f"En-têtes BZIP2 complets possibles      : {len(bz2_offsets)}")
    print(f"En-têtes XZ complets possibles         : {len(xz_offsets)}")
    print()

    print("[1/5] Test des flux ZLIB avec en-tête...")
    for offset in valid_zlib_offsets:
        result = try_zlib(data, offset, zlib.MAX_WBITS)
        if result:
            decoded, consumed = result
            candidates.append(("zlib", offset, consumed, decoded))

    print("[2/5] Test de tous les offsets en DEFLATE brut...")
    for offset in range(len(data)):
        result = try_zlib(data, offset, -zlib.MAX_WBITS)
        if result:
            decoded, consumed = result
            candidates.append(("deflate_raw", offset, consumed, decoded))

    print("[3/5] Test des flux GZIP...")
    for offset in gzip_offsets:
        result = try_zlib(data, offset, 16 + zlib.MAX_WBITS)
        if result:
            decoded, consumed = result
            candidates.append(("gzip", offset, consumed, decoded))

    print("[4/5] Test des flux BZIP2...")
    for offset in bz2_offsets:
        result = try_bz2(data, offset)
        if result:
            decoded, consumed = result
            candidates.append(("bz2", offset, consumed, decoded))

    print("[5/5] Test des flux XZ/LZMA...")
    for offset in xz_offsets:
        result = try_lzma(data, offset)
        if result:
            decoded, consumed = result
            candidates.append(("xz", offset, consumed, decoded))

    # Deduplicate exact decoded outputs.
    unique = {}
    for kind, offset, consumed, decoded in candidates:
        fingerprint = (len(decoded), zlib.crc32(decoded), decoded[:32], decoded[-32:])
        if fingerprint not in unique:
            unique[fingerprint] = (kind, offset, consumed, decoded)

    candidates = list(unique.values())
    candidates.sort(
        key=lambda item: (
            -len(item[3]),
            entropy(item[3][:65536]),
            item[1],
        )
    )

    report_path = OUTPUT_ROOT / "strict_stream_report.txt"
    with report_path.open("w", encoding="utf-8") as report:
        report.write("=" * 100 + "\n")
        report.write("STRICT STREAM REPORT\n")
        report.write("=" * 100 + "\n\n")

        if not candidates:
            report.write("Aucun flux compressé valide trouvé.\n")

        for rank, (kind, offset, consumed, decoded) in enumerate(candidates, 1):
            hits = marker_hits(decoded)
            saved = save_stream(rank, kind, offset, decoded)

            report.write(f"FLUX #{rank}\n")
            report.write(f"Type           : {kind}\n")
            report.write(f"Offset         : 0x{offset:08x} ({offset})\n")
            report.write(f"Octets consommés: {consumed}\n")
            report.write(f"Taille sortie  : {len(decoded)}\n")
            report.write(f"Ratio expansion: {len(decoded) / max(consumed, 1):.6f}\n")
            report.write(f"Entropie sortie: {entropy(decoded[:65536]):.6f}\n")
            report.write(f"Imprimable     : {printable_ratio(decoded[:65536]):.6f}\n")
            report.write(f"Zéros          : {zero_ratio(decoded[:65536]):.6f}\n")
            report.write(f"Marqueurs      : {len(hits)}\n")
            report.write(f"Fichier        : {saved}\n")
            report.write(f"Début hex      : {decoded[:128].hex(' ')}\n")

            for pos, label in hits[:50]:
                report.write(f"  0x{pos:08x} {label}\n")

            report.write("-" * 100 + "\n")

    print()
    print("=" * 100)
    print("RÉSULTATS VALIDÉS")
    print("=" * 100)

    if not candidates:
        print("Aucun flux ZLIB/DEFLATE/GZIP/BZIP2/XZ valide n'a été trouvé.")
    else:
        print(
            f"{'rang':>4} {'type':>12} {'offset':>12} "
            f"{'consommé':>10} {'sortie':>10} {'entropie':>10} {'marqueurs':>9}"
        )
        for rank, (kind, offset, consumed, decoded) in enumerate(candidates[:100], 1):
            print(
                f"{rank:4d} {kind:>12} 0x{offset:08x} "
                f"{consumed:10d} {len(decoded):10d} "
                f"{entropy(decoded[:65536]):10.4f} "
                f"{len(marker_hits(decoded)):9d}"
            )

    print()
    print("=" * 100)
    print("TERMINÉ")
    print("=" * 100)
    print(f"Rapport : {report_path}")
    print()
    print("Commande suivante :")
    print(f"  cat {report_path}")


if __name__ == "__main__":
    main()
