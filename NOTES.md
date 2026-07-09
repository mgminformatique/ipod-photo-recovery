# iPod Photo Recovery — Research Notes

## Confirmed
- T102/T103/T104/etc = tables / records 24 bytes.
- T154/T155/T156/T157/T158/etc = probable payloads.
- Photo Database: high entropy, not simple SQLite/bplist/zlib.
- T149 contains internal tables/LUT-like regions.
- Raw YUV tests on table files created false diagonal patterns.
- Raw YUV/RGB565/RGB555/grayscale tests on payloads did not produce readable photos.

## Ruled out
- Direct RGB565/RGB555 pixels.
- Simple YUYV/UYVY/VYUY/YVYU decode.
- Simple stride-only fix.
- Simple zlib/gzip/JPEG/PNG embedded streams.
- Photo Database as direct parser target.

## Next direction
- Stop brute-force rendering.
- Map relationships between 24-byte table records and payload offsets.
- Use table files to locate exact payload chunks.
- Compare table values against payload active blocks.
