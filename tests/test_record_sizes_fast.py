from pathlib import Path
import struct

ROOT = Path("/home/murph/Desktop/iPod Photo Cache")
DB = ROOT / "Photo Database"

SIZES = [
    8,12,16,20,24,28,32,36,40,
    48,56,64,72,80,96,112,128,
    160,192,224,256
]

data = DB.read_bytes()

print("="*80)
print("FAST RECORD SIZE TEST")
print("="*80)
print(f"Database size : {len(data)} bytes")
print()

for record_size in SIZES:

    print(f"Testing record size {record_size}...")

    records = len(data)//record_size
    remainder = len(data)%record_size

    best=None

    for field in range(0,min(record_size-4,32)+1,4):

        values=[]

        pos=field

        while pos+4<=len(data):
            values.append(
                struct.unpack_from("<I",data,pos)[0]
            )
            pos+=record_size

        if len(values)<8:
            continue

        increasing=0

        for a,b in zip(values,values[1:]):
            if b>=a:
                increasing+=1

        ratio=increasing/(len(values)-1)

        if best is None or ratio>best[0]:
            best=(ratio,field,min(values),max(values))

    if best:
        print(
            f"  records={records:5d} "
            f"remainder={remainder:4d} "
            f"best_field={best[1]:2d} "
            f"mono={best[0]:.3f} "
            f"min={best[2]} "
            f"max={best[3]}"
        )

print()
print("Done.")
