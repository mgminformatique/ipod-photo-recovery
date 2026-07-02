from parser.ithmb_records import ITHMBRecordParser

FILES = [
    "/home/murph/Desktop/iPod Photo Cache/F12/T161.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F06/T155.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F08/T157.ithmb",
    "/home/murph/Desktop/iPod Photo Cache/F15/T113.ithmb",
]

for path in FILES:
    parser = ITHMBRecordParser(path)
    records = parser.find_records()

    print("=" * 80)
    print(path)
    print("records:", len(records))

    for r in records:
        f = r.fields()
        print(
            f"start={f['record_start']} "
            f"field_88={f['field_88']} "
            f"field_92={f['field_92']} "
            f"field_96={f['field_96']} "
            f"field_100={f['field_100']} "
            f"field_104={f['field_104']} "
            f"field_108={f['field_108']}"
        )
