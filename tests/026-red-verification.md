# MM-026 Red verification

Date: 2026-11-07 (Asia/Shanghai)

Before application implementation, only MM-026 tests/checklists and the
intentionally changed MM-022 test expectations were added.

Collection command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_multi_image_gallery.py tests\test_multi_image_migration.py tests\test_image_dropzone.py tests\test_product_image_interactions.py --collect-only -q
```

Result: **40 tests collected**.

Red command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_multi_image_gallery.py tests\test_multi_image_migration.py tests\test_image_dropzone.py tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm026-red
```

Result: **19 failed, 21 passed in 49.16 seconds**.

Expected failures reported:

- missing ProductImage model/relationship;
- missing product_images migration/backfill/duplicate preflight;
- missing multiple file input, five/25-MiB instructions and preview list;
- Edit still using the old ordinary single-file presentation;
- missing multi-file JavaScript count/total/URL-array behavior;
- missing gallery CSS and product thumbnail/lightbox synchronization; and
- maintenance not yet aware of gallery references/cover drift.

The 21 passing cases prove existing lightbox/media/security and unaffected
dropzone behavior remained stable at the boundary. Collection had no syntax or
fixture errors, and no test touched the real database/uploads. This is a valid
Red checkpoint, so the approved SDD sequence now permits implementation.
