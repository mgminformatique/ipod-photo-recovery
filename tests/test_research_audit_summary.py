from pathlib import Path

OUT = Path("output")

FILES = [
    "ithmb_record_vs_payload_classifier.txt",
    "t149_region_type_map.txt",
    "t149_sequence_match_payloads.txt",
    "photo_db_map.txt",
    "photo_db_cross_refs.txt",
    "photo_db_mod2304_context.txt",
    "photo_db_slot_targets.txt",
]

print("=" * 100)
print("RESEARCH AUDIT SUMMARY")
print("=" * 100)

for name in FILES:
    path = OUT / name
    print()
    print("-" * 100)
    print(name)

    if not path.exists():
        print("MISSING")
        continue

    text = path.read_text(errors="replace")
    lines = text.splitlines()

    print(f"lines={len(lines)} size={path.stat().st_size}")

    keywords = [
        "24-BYTE RECORD/TABLE",
        "POSSIBLE PAYLOAD",
        "total exact hits",
        "T149",
        "entropy",
        "mod2304 hits",
        "targets:",
        "PTR_PAGE",
        "U16_ZERO_INTERLEAVED",
    ]

    for k in keywords:
        hits = [l for l in lines if k in l]
        if hits:
            print(f"\n{k}:")
            for l in hits[:12]:
                print("  " + l[:180])
