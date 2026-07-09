# Research State

## Scripts principaux à garder
- test_cache_file_inventory.py
- test_ithmb_record_vs_payload_classifier.py
- test_find_tile_ids.py
- test_t149_records_24.py
- test_t149_tile_record_summary.py
- test_t149_expand_blocks.py
- test_t149_resolve_record_ranges.py
- test_t149_deref_expanded_offsets.py
- test_t149_region_type_map.py

## Pistes déjà testées / à ne plus refaire
- render brut RGB565/RGB555/RGB888/BGR
- YUV/YCBCR brut
- tile unswizzle brut
- Keith iPod Photo Reader direct
- zlib/gzip/JPEG/PNG direct
- grayscale payload brut

## État actuel
T149 est une structure logique/table/index, pas une image.
Les gros fichiers T154-T174 sont probablement des payloads, mais pas décodables en pixels bruts.
La prochaine piste doit être Photo Database ↔ T149 ↔ payloads.
