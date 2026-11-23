# MM-022 Red verification

Date: 2026-11-02 (Asia/Shanghai)

The approved pytest contracts and browser checklist were written before feature
implementation.

## Collection

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py --collect-only -q
# 17 tests collected in 0.98s
```

## Expected failing run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm022-red
# 7 failed, 10 passed in 21.01s
```

Expected missing-feature failures:

- no new-listing drop-zone/preview/status markup;
- no MM-022 guarded JavaScript block or drag/drop/object-URL behavior; and
- no drop-zone, drag-over, focus or bounded-preview CSS.

The ten passing tests confirmed preserved authentication/form scope, read-only
rendering, existing server normalization, and rejection/cleanup of empty,
spoofed and over-5-MiB images. This proves the new tests detect the absent user
experience without falsely claiming the already-secure server pipeline is new.
