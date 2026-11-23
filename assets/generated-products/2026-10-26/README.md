# Market Mirror: matching generated product pictures

Created on 2026-10-26 using the built-in image_gen tool, with one generation per
product. The complete exact prompt set and generation provenance are saved in
[manifest.json](manifest.json). These are AI-generated fictional demo pictures,
not photographs of actual goods or evidence of their condition.

## Saved assets

- [Study desk lamp](study-desk-lamp.png)
- [Python learning book](python-learning-book.png)
- [Wireless keyboard](wireless-keyboard.png)
- [Canvas tote bag](canvas-tote-bag.png)
- [Basketball](basketball.png)
- [Board game collection](board-game-collection.png)
- [Portable speaker](portable-speaker.png)
- [Ceramic plant pot](ceramic-plant-pot.png)
- [Winter jacket](winter-jacket.png)
- [Adventure novel set](adventure-novel-set.png)
- [Camping lantern](camping-lantern.png)
- [Craft supply box](craft-supply-box.png)

The original wireless mouse photo (listing 13) is outside this replacement set.
No laptop listing exists, so no laptop listing or invented product was added.

## How attachment works

The database stores the image filename, while the JPEG file lives in the private
uploads directory. The existing app image helper validates each generated PNG and
makes a web-ready JPEG with a new random filename. Only the original fictional
seed listings with exactly matching old photo references may be updated.

The importer keeps the original files, makes a SQLite database backup, and copies
the old images into a separate recovery folder. All twelve references are updated
in one transaction; prices, descriptions, ownership and availability are unchanged.
Version numbers advance to protect against stale edit forms. A failed import rolls
back its database updates and removes only its own newly stored JPEGs.

This is a one-time asset update, not automatic generation for future listings.
No server code, schema, login behaviour, visibility rule or historical context is
replaced. The originals and earlier Pillow illustration script remain available.

## Verification plan

Before touching live data, pytest checks: successful attachment and unchanged
unrelated fields; rejection of changed photo references; whole-batch rollback on
a bad image; preservation and separate backup of old photos; production refusal.
After import, compare every product against the database backup, check all media
routes including archived-image privacy, and refresh the browser to verify the
visible pictures.

## Completed verification

- Initial Red: 5 tests failed because the importer did not yet exist.
- Windows long-path failures were corrected before touching the live database.
- Final pytest run: **5 passed in 43.28s** using
  `tests/test_generated_product_assets.py` and a disposable test database.
- Live import completed: **12 generated images attached**.
- Database backup and copies of all 12 original drawings:
  `instance/backups/ai-15ce38f22713/` (database.sqlite,
  original-uploads/, and replacement-map.json). Do not blindly restore the whole
  database later: that would also revert unrelated changes made since this backup.
- Compared all 13 live product rows to the backup: only image_filename, version,
  and updated_at changed for the intended 12 rows. The mouse row and all users
  were unchanged; every original image remained and matched its backup copy.
- SQLite integrity check returned `ok`.
- All 13 live media endpoints were checked: active/sold images returned JPEGs
  with HTTP 200; both archived images returned HTTP 404 anonymously, as required.
- Verified the updated catalogue in the in-app browser. Screenshot:
  `docs/evidence/generated-product-photos.jpg`.
- The local server had stopped during verification; it was started again on
  127.0.0.1:5000. Nothing was published to an external host.

This verification covers this asset update, not a rerun of the entire historical
project test suite. The original prompts are preserved verbatim in manifest.json.
