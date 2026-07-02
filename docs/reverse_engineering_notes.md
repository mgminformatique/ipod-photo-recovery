# iPod Photo Cache Reverse Engineering Notes

## Confirmed findings

### Cache contents

The cache contains:

- `Photo Database`
- `.ithmb` files inside `Fxx/` folders

### ITHMB record GUID

Some `.ithmb` files contain UTF-16LE records with this GUID:

`00262001-0002-0010-FBB3-AB02A8125552`

The GUID records are 112 bytes long.

### Record families

Files with records include mainly `T154` to `T174`, plus `T130`.

Most contain 16 records.

Known exceptions:

- `T166` contains 8 records
- `T172` contains 24 records

### Record structure

Records contain mostly constant data.

Only a few bytes change between records:

- offset `0`
- offset `1`
- offset `6`
- offset `88`
- offset `89`

### Slot byte

Byte offset `6` appears to be a slot index.

Slots cover values from `0` to `127`, grouped in blocks of 8.

Example:

`T161` contains:

- `112 111 110 109 108 107 106 105`
- `120 119 118 117 116 115 114 113`

### field_88

`field_88` is a 32-bit little-endian value.

It has this shape:

`0x0028XXXX`

The high 16 bits are always `0x0028`.

The low 8 bits appear related to file/group identity.

The middle bits vary in regular steps, often by `2304`.

### Photo Database

Current observations:

- high entropy
- no readable UTF-16LE GUID
- no obvious references to `Txxx.ithmb`
- no simple fixed-size table found
- no simple XOR 1-byte obfuscation found
- zlib/gzip/raw-deflate hits appear to be false positives

## Working hypothesis

The `.ithmb` files include structured format/slot records, but the actual photo-to-frame mapping is likely stored in `Photo Database` or in another hidden structure.

The records appear to describe cache slots or render formats rather than individual photos.
