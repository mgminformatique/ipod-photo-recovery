from __future__ import annotations

import bz2
import gzip
import lzma
import math
import zlib
from collections import Counter
from pathlib import Path

CACHE_ROOT = Path('/home/murph/Desktop/iPod Photo Cache')
OUTPUT_ROOT = Path('output/photo_database_transform_probe')

KNOWN_SIGNATURES = {
    b'bplist00': 'Apple binary plist',
    b'<?xml': 'XML',
    b'SQLite format 3\x00': 'SQLite',
    b'PK\x03\x04': 'ZIP',
    b'\x1f\x8b': 'GZIP',
    b'BZh': 'BZIP2',
    b'\xfd7zXZ\x00': 'XZ/LZMA',
    b'\x78\x01': 'ZLIB',
    b'\x78\x5e': 'ZLIB',
    b'\x78\x9c': 'ZLIB',
    b'\x78\xda': 'ZLIB',
    b'mhbd': 'iTunesDB mhbd',
    b'mhsd': 'iTunesDB mhsd',
    b'mhlt': 'iTunesDB mhlt',
    b'mhit': 'iTunesDB mhit',
    b'mhyp': 'iTunesDB mhyp',
    b'mhla': 'iTunesDB mhla',
    b'mhii': 'iPod Photo mhii',
    b'mhfd': 'iPod Photo mhfd',
    b'mhli': 'iPod Photo mhli',
    b'mhia': 'iPod Photo mhia',
    b'mhni': 'iPod Photo mhni',
    b'mhif': 'iPod Photo mhif',
    b'ithm': 'ITHMB marker',
    b'dbhm': 'reversed mhbd',
    b'dfhm': 'reversed mhfd',
    b'iihm': 'reversed mhii',
}

PRINTABLE = set(range(32, 127)) | {9, 10, 13}


def find_database() -> Path:
    matches = sorted(CACHE_ROOT.rglob('Photo Database'))
    if not matches:
        raise FileNotFoundError(f'Photo Database introuvable sous {CACHE_ROOT}')
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
    return sum(1 for b in data if b in PRINTABLE) / len(data)


def zero_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return data.count(0) / len(data)


def scan_signatures(data: bytes):
    hits = []
    for sig, label in KNOWN_SIGNATURES.items():
        start = 0
        while True:
            pos = data.find(sig, start)
            if pos < 0:
                break
            hits.append((pos, label, sig))
            start = pos + 1
    return sorted(hits)


def score_candidate(data: bytes) -> float:
    if not data:
        return -999.0
    sample = data[: min(len(data), 65536)]
    score = printable_ratio(sample) * 10.0
    score += zero_ratio(sample) * 8.0
    score += max(0.0, 7.5 - entropy(sample)) * 4.0
    for sig in KNOWN_SIGNATURES:
        if sample.startswith(sig):
            score += 100.0
        elif sig in sample:
            score += 25.0
    return score


def bit_reverse_byte(value: int) -> int:
    return int(f'{value:08b}'[::-1], 2)


BIT_REVERSE_TABLE = bytes(bit_reverse_byte(i) for i in range(256))


def transform_variants(data: bytes):
    yield 'identity', data
    yield 'reverse_all', data[::-1]
    yield 'bitwise_not', bytes((~b) & 0xFF for b in data)
    yield 'bit_reverse_each_byte', data.translate(BIT_REVERSE_TABLE)

    for size in (2, 4, 8, 16):
        swapped = bytearray()
        for i in range(0, len(data), size):
            swapped.extend(data[i:i + size][::-1])
        yield f'reverse_each_{size}_bytes', bytes(swapped)

    for shift in range(1, 8):
        left = bytes(((b << shift) | (b >> (8 - shift))) & 0xFF for b in data)
        right = bytes(((b >> shift) | (b << (8 - shift))) & 0xFF for b in data)
        yield f'rotate_left_{shift}', left
        yield f'rotate_right_{shift}', right

    for key in range(256):
        yield f'xor_byte_{key:02x}', bytes(b ^ key for b in data)

    for delta in range(1, 256):
        yield f'add_byte_{delta:02x}', bytes((b + delta) & 0xFF for b in data)
        yield f'sub_byte_{delta:02x}', bytes((b - delta) & 0xFF for b in data)


def differential_variants(data: bytes):
    if not data:
        return
    out = bytearray([data[0]])
    for i in range(1, len(data)):
        out.append(data[i] ^ data[i - 1])
    yield 'xor_with_previous', bytes(out)

    out = bytearray([data[0]])
    for i in range(1, len(data)):
        out.append((data[i] - data[i - 1]) & 0xFF)
    yield 'subtract_previous', bytes(out)

    for width in (2, 4):
        out = bytearray(data[:width])
        for i in range(width, len(data)):
            out.append(data[i] ^ data[i - width])
        yield f'xor_with_previous_{width}', bytes(out)


def repeating_xor_candidates(data: bytes, max_key_len: int = 32):
    results = []
    sample = data[: min(len(data), 32768)]
    for key_len in range(2, max_key_len + 1):
        key = bytearray()
        for pos in range(key_len):
            column = sample[pos::key_len]
            best_key = 0
            best_score = -1.0
            for candidate in range(256):
                decoded = bytes(b ^ candidate for b in column[:4096])
                s = printable_ratio(decoded) * 2.0 + zero_ratio(decoded) * 0.5
                if s > best_score:
                    best_score = s
                    best_key = candidate
            key.append(best_key)
        decoded = bytes(b ^ key[i % key_len] for i, b in enumerate(data))
        results.append((f'xor_repeat_len_{key_len}_key_{key.hex()}', decoded))
    return results


def try_decompress(name: str, data: bytes):
    attempts = [
        ('zlib', lambda x: zlib.decompress(x)),
        ('zlib_raw', lambda x: zlib.decompress(x, -zlib.MAX_WBITS)),
        ('gzip', gzip.decompress),
        ('bz2', bz2.decompress),
        ('lzma', lzma.decompress),
    ]
    outputs = []
    for label, func in attempts:
        try:
            decoded = func(data)
            if decoded:
                outputs.append((f'{name}__decompressed_{label}', decoded))
        except Exception:
            pass
    for offset in range(min(len(data), 8192)):
        chunk = data[offset:]
        for label, func in attempts:
            try:
                decoded = func(chunk)
                if decoded:
                    outputs.append((f'{name}__offset_{offset:04x}__decompressed_{label}', decoded))
            except Exception:
                pass
    return outputs


def detect_repeated_blocks(data: bytes, block_size: int):
    blocks = [data[i:i + block_size] for i in range(0, len(data) - block_size + 1, block_size)]
    if not blocks:
        return 0, 0
    counts = Counter(blocks)
    repeats = sum(c - 1 for c in counts.values() if c > 1)
    return repeats, max(counts.values())


def save_preview(rank: int, name: str, data: bytes) -> Path:
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in name)
    path = OUTPUT_ROOT / 'candidates' / f'{rank:02d}_{safe}.bin'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    db_path = find_database()
    data = db_path.read_bytes()

    print('=' * 100)
    print('PHOTO DATABASE TRANSFORM PROBE')
    print('=' * 100)
    print(f'Fichier          : {db_path}')
    print(f'Taille           : {len(data):,} octets')
    print(f'Entropie         : {entropy(data):.6f}')
    print(f'Ratio imprimable : {printable_ratio(data):.6f}')
    print(f'Ratio zéros      : {zero_ratio(data):.6f}')
    print()

    for size in (8, 16, 32, 64):
        repeats, max_count = detect_repeated_blocks(data, size)
        print(f'Blocs {size:2d} octets : répétitions={repeats}, fréquence maximale={max_count}')

    raw_hits = scan_signatures(data)
    print(f'\nSignatures brutes trouvées : {len(raw_hits)}')
    for pos, label, sig in raw_hits[:100]:
        print(f'  0x{pos:08x}  {label:<24}  {sig!r}')

    candidates = []
    print('\n[1/4] Transformations simples...')
    for name, transformed in transform_variants(data):
        hits = scan_signatures(transformed)
        score = score_candidate(transformed)
        if hits or score >= 8.0:
            candidates.append((score, name, transformed, hits))

    print('[2/4] Transformations différentielles...')
    for name, transformed in differential_variants(data):
        hits = scan_signatures(transformed)
        score = score_candidate(transformed)
        if hits or score >= 8.0:
            candidates.append((score, name, transformed, hits))

    print('[3/4] XOR à clé répétée...')
    for name, transformed in repeating_xor_candidates(data):
        hits = scan_signatures(transformed)
        score = score_candidate(transformed)
        if hits or score >= 8.0:
            candidates.append((score, name, transformed, hits))

    unique = {}
    for item in candidates:
        score, name, transformed, hits = item
        fingerprint = (len(transformed), transformed[:64], transformed[-64:])
        if fingerprint not in unique or score > unique[fingerprint][0]:
            unique[fingerprint] = item
    candidates = sorted(unique.values(), key=lambda x: x[0], reverse=True)

    print('[4/4] Tentatives de décompression...')
    decompressed = []
    for score, name, transformed, hits in candidates[:40]:
        for dname, decoded in try_decompress(name, transformed):
            decompressed.append((score_candidate(decoded) + 20.0, dname, decoded, scan_signatures(decoded)))
    candidates.extend(decompressed)
    candidates.sort(key=lambda x: x[0], reverse=True)

    report_path = OUTPUT_ROOT / 'transform_candidates.txt'
    with report_path.open('w', encoding='utf-8') as report:
        report.write('=' * 100 + '\nTRANSFORM CANDIDATES\n' + '=' * 100 + '\n\n')
        for rank, (score, name, transformed, hits) in enumerate(candidates[:100], 1):
            sample = transformed[:65536]
            report.write(f'RANG #{rank}\n')
            report.write(f'Nom            : {name}\n')
            report.write(f'Score          : {score:.6f}\n')
            report.write(f'Taille         : {len(transformed)}\n')
            report.write(f'Entropie       : {entropy(sample):.6f}\n')
            report.write(f'Ratio imprim.  : {printable_ratio(sample):.6f}\n')
            report.write(f'Ratio zéros    : {zero_ratio(sample):.6f}\n')
            report.write(f'Signatures     : {len(hits)}\n')
            for pos, label, sig in hits[:20]:
                report.write(f'  0x{pos:08x} {label:<24} {sig!r}\n')
            report.write(f'Hex début      : {transformed[:128].hex(" ")}\n')
            report.write('-' * 100 + '\n')
            if rank <= 20:
                save_preview(rank, name, transformed)

    print('\n' + '=' * 100)
    print('MEILLEURS CANDIDATS')
    print('=' * 100)
    if not candidates:
        print('Aucun candidat prometteur détecté.')
    else:
        print(f"{'rang':>4} {'score':>10} {'entropie':>10} {'imprim.':>9} {'zéros':>8} {'sign.':>6}  transformation")
        for rank, (score, name, transformed, hits) in enumerate(candidates[:30], 1):
            sample = transformed[:65536]
            print(f'{rank:4d} {score:10.4f} {entropy(sample):10.4f} {printable_ratio(sample):9.4f} {zero_ratio(sample):8.4f} {len(hits):6d}  {name}')

    print('\n' + '=' * 100)
    print('TERMINÉ')
    print('=' * 100)
    print(f'Rapport : {report_path}')
    print(f'Candidats binaires : {OUTPUT_ROOT / "candidates"}')
    print(f"Commande suivante : sed -n '1,260p' {report_path}")


if __name__ == '__main__':
    main()
