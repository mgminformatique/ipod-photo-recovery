from parser.photo_database import PhotoDatabase

db = PhotoDatabase("/home/murph/Desktop/iPod Photo Cache/Photo Database")

print("Photo Database")
print("Size:", db.size)
print("")

print("First 256 bytes:")
print(db.hexdump(0, 256))
print("")

print("Low entropy blocks:")
for b in db.find_low_entropy_blocks(512, 7.0)[:30]:
    print(
        f"offset=0x{b['offset']:08x} "
        f"entropy={b['entropy']} "
        f"zeros={b['zeros']} "
        f"ff={b['ff']} "
        f"first16={b['first16']}"
    )
