# Demo-image utility verification — 2026-10-25

This adds evidence; it does not replace earlier project verification records.

## Red

The initial 23 tests were written before `scripts/generate_demo_images.py` existed.

```text
.venv\Scripts\python.exe -m pytest tests\test_demo_images.py -q --basetemp=.pytest-tmp\demo-images-red
23 failed in 73.15s
```

All failures were the expected missing utility import, not fixture setup errors.

## Green and regression

The first implementation passed those 23 tests in 59.84 seconds. Five further
checks covered seed-contract consistency, backup failure, deferred commit failure,
redirected output paths, and running the actual script from an unrelated folder
with misleading external database/upload environment variables.

```text
.venv\Scripts\python.exe -m pytest tests\test_demo_images.py tests\test_marketplace.py tests\test_seed_command.py -q --basetemp=.pytest-tmp\demo-images-regression
80 passed in 1112.50s (0:18:32)
```

This is the 28-test utility suite plus existing marketplace/seed regression tests,
not a claim that the entire historical project suite was rerun. Python compilation
checks also passed. Pillow 12.3.0 matches the existing lock file.

The contact sheet at `.pytest-tmp/demo-images-preview.jpg` was visually inspected:
all twelve illustrations depict the corresponding product, titles are legible,
and each is explicitly labelled as fictional artwork rather than a photograph.

Tests exercised the real Flask media route: active/sold images were accessible,
while anonymous access to archived images returned 404. Backups retained the
original rows and passed SQLite integrity checks. Injected rendering/update/commit
failures rolled back references and removed newly created files without deleting
pre-existing files. Repeated successful invocations made no further changes.

## Real data was not modified

Read-only inspection found 13 actual listings, including 12 original seed listings
without photos and one other listing with a photo. The real development database
SHA-256 matched before and after the utility work:

`553678E5632CC15F586A1B2C7F4522CF7A628DEC0055E25ADB602C268CE88FFF`

Only disposable test databases received images. The user runs the delivered
PowerShell command to attach images to their real local database. No deployment,
API calls, paid image generation, schema migration, or removal of prior context
was performed.
