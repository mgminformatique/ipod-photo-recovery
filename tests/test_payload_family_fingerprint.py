from pathlib import Path
import struct
import math
from collections import defaultdict, Counter

CACHE = Path("/home/murph/Desktop/iPod Photo Cache")

PAGE_SIZE = 0x400
HEADER_SIZE = 4
PAYLOAD_SIZE = PAGE_SIZE - HEADER_SIZE

T_NUMBERS = set(range(154,175)) | {130}
EXCLUDED = {157,168}

RECORD_START = 0x7C
RECORD_SIZE = 0x70
RECORD_COUNT = 8


def get_t_number(path):
    try:
        return int(path.stem[1:])
    except:
        return None


family_pages = defaultdict(list)

for path in sorted(CACHE.rglob("T*.ithmb")):

    t = get_t_number(path)

    if t not in T_NUMBERS or t in EXCLUDED:
        continue

    raw = path.read_bytes()
    page_count = len(raw)//PAGE_SIZE

    for table_page in range(page_count):

        page = raw[
            table_page*PAGE_SIZE:
            (table_page+1)*PAGE_SIZE
        ]

        if struct.unpack_from(">I",page,0)[0] != 0x0D000000:
            continue

        payload = page[4:]

        for rec in range(RECORD_COUNT):

            r = payload[
                RECORD_START+rec*RECORD_SIZE:
                RECORD_START+(rec+1)*RECORD_SIZE
            ]

            tile = struct.unpack_from("<H",r,0x04)[0]
            f56  = struct.unpack_from(">H",r,0x56)[0]

            if f56 % 9:
                continue

            page_index = f56//9

            if page_index >= page_count:
                continue

            base = tile-page_index

            data = raw[
                page_index*PAGE_SIZE+4:
                (page_index+1)*PAGE_SIZE
            ]

            family_pages[base].append(data)

print("="*120)
print("FAMILY FINGERPRINT")
print("="*120)

for base in sorted(family_pages):

    blobs = family_pages[base]

    total = len(blobs)

    ent = []
    unique=[]
    avg=[]
    variance=[]
    low=[]
    high=[]
    ones=[]
    zeros=[]

    diff_counter=Counter()

    for blob in blobs:

        counts=Counter(blob)

        p=len(blob)

        entropy=0

        for c in counts.values():
            f=c/p
            entropy-=f*math.log2(f)

        ent.append(entropy)

        unique.append(len(counts))

        mean=sum(blob)/p
        avg.append(mean)

        var=sum((x-mean)*(x-mean) for x in blob)/p
        variance.append(var)

        low.append(sum(x<16 for x in blob))
        high.append(sum(x>240 for x in blob))
        ones.append(blob.count(1))
        zeros.append(blob.count(0))

        for a,b in zip(blob,blob[1:]):
            diff_counter[(b-a)&0xff]+=1

    print()
    print("-"*120)
    print(f"BASE {base}")
    print("-"*120)

    print(f"pages              : {total}")
    print(f"entropy avg        : {sum(ent)/len(ent):8.3f}")
    print(f"unique bytes avg   : {sum(unique)/len(unique):8.2f}")
    print(f"mean byte avg      : {sum(avg)/len(avg):8.2f}")
    print(f"variance avg       : {sum(variance)/len(variance):10.2f}")
    print(f"bytes <16 avg      : {sum(low)/len(low):8.2f}")
    print(f"bytes >240 avg     : {sum(high)/len(high):8.2f}")
    print(f"zeros avg          : {sum(zeros)/len(zeros):8.2f}")
    print(f"ones avg           : {sum(ones)/len(ones):8.2f}")

    print()

    print("top byte deltas")

    for delta,count in diff_counter.most_common(20):
        print(
            f"  delta={delta:3d} count={count}"
        )

