# Ten additional demo listings — 2026-10-26

## Result

Added ten active, fictional listings (IDs 14–23) to the local Market Mirror database, each with its own AI-generated product picture. The catalogue now has 19 active listings; the database has 23 total including two sold and two archived listings.

| Listing | Source image | Fictional USD price |
| --- | --- | ---: |
| Silver laptop | silver-laptop.png | 450.00 |
| Unlocked smartphone | unlocked-smartphone.png | 180.00 |
| Wireless over-ear headphones | wireless-headphones.png | 55.00 |
| 24-inch monitor | desktop-monitor.png | 110.00 |
| Digital camera | digital-camera.png | 220.00 |
| City bicycle | city-bicycle.png | 140.00 |
| Everyday backpack | everyday-backpack.png | 25.00 |
| Drip coffee maker | drip-coffee-maker.png | 45.00 |
| Ergonomic office chair | office-chair.png | 75.00 |
| Acoustic guitar | acoustic-guitar.png | 85.00 |

These are practice listings, not real goods or market valuations. Each description discloses that its picture and price are fictional demo content. Pictures include a small AI-generated demo label.

## How it works, in plain language

The built-in image-generation tool created one new raster picture per item. The exact prompts are in `manifest.json` and `generation-provenance.json` in this folder. The original PNGs are kept here so they can be inspected or reused.

The import script, `scripts/add_additional_demo_items.py`, uses the existing application's image-storage helper to validate each picture and save a JPEG under `instance/uploads`. The database stores the JPEG's filename alongside the product title, description, seller and price. Think of that filename as the address the website follows to find the correct picture.

The script uses the existing three demo sellers, creates no accounts, and does not edit existing products. It stores money as integer cents, so $25.00 is stored as 2500 rather than an approximate decimal number.

A database transaction groups all ten inserts together. If a file or database operation fails before the commit, the transaction rolls back and the newly created image files are removed. An unchanged repeat of this batch is skipped, preventing duplicate listings. This property is called idempotency.

No application routes, templates or database schema were changed. Previous specifications, plans, assets and context were retained.

## Backup and preservation

The pre-import database snapshot is:

`instance/backups/before-demo-images-20261026T022241Z-531e03624a9b4844b942c03f8437bf6b.sqlite`

The adjacent `.json` receipt records each inserted ID, title and stored image filename. Comparing the snapshot with the updated database confirmed that all original 13 product rows (including Wireless Mouse) and all user rows were unchanged. Original images were not overwritten.

## Tests and verification

Tests were defined before implementing the importer in `tests/test_additional_demo_items.py`.

- Initial red run: six tests failed because the importer module did not yet exist.
- Green run after implementation: **6 passed in 56.40 seconds**.
- Covered exact ten-item insertion, preservation of existing data, repeat-run duplicate prevention, public detail/media routes, corrupt-image rollback, database-error rollback, changed seller identity, title collisions, production refusal and invalid inputs.
- Live database: 23 total products, 19 active, 2 sold, 2 archived; SQLite integrity check returned `ok`.
- All ten new stored images were opened and verified with Pillow.
- Read-only HTTP checks: catalogue, all ten new detail pages and all ten new media URLs returned HTTP 200.
- Browser showed all ten new titles and the 19-product count; the screenshot confirms the generated pictures render on the catalogue.
- Evidence: `docs/evidence/additional-demo-items.jpg`.

Only the focused six-test suite was run for this addition; this document does not claim a full application regression run.

## Try it yourself

Open http://127.0.0.1:5000/products while the local server is running. Search for `laptop`, open Silver laptop, and check its picture and demo description. Clear the search to return to the complete catalogue. No installation or manual file copying is required.
