# PLAN-026 — Up to five product images and thumbnail gallery

Status: IMPLEMENTED — approved 2026-11-07; completed 2026-11-07

Date: 2026-11-07 (Asia/Shanghai)

Approved specification: MM-026, explicitly approved by the user on 2026-11-07.

## 1. Outcome

Implement a backward-compatible product gallery containing zero through five
ordered JPEG/PNG uploads. Sellers will receive multi-file drag/drop previews on
Sell and a safe full-gallery replacement workflow on Edit. Buyers will receive
a small accessible thumbnail strip that changes the main image and the existing
lightbox without reloading the page.

The first photo is position 0 and remains the cover used by existing cards.
Only that cover is sent to the optional AI Vision provider.

## 2. Architecture

```text
Sell/Edit multiple file input
        │
        ├─ browser hints: 1–5, type, per-file/combined size
        ├─ local ordered thumbnail previews
        └─ AI Vision receives cover only (Sell page, when enabled)
                    │
                    ▼ Save Listing
Server validates every byte stream independently
        │
        ├─ count ≤ 5
        ├─ each ≤ 5 MiB, group ≤ 25 MiB
        ├─ Pillow format/frame/pixel verification
        └─ metadata-free normalized JPEG per file
                    │
                    ▼ one business transaction
products.image_filename ── cached/compatible cover filename
product_images
    ├─ position 0 ───────── authoritative cover row
    ├─ position 1
    ├─ position 2
    ├─ position 3
    └─ position 4
                    │
                    ▼
Product detail presentation
    ├─ large selected image + existing zoom/lightbox
    └─ 2–5 thumbnail links, JavaScript-enhanced switching
```

The database transaction can roll back rows, but it cannot automatically undo
ordinary filesystem writes. Therefore the image service tracks every newly
stored file and explicitly removes it when any later validation/database step
fails. Old Edit images are deleted only after the replacement transaction
commits.

## 3. Planned file changes

| File | Planned responsibility |
| --- | --- |
| `app/models/product.py` | Add `Product.gallery_images` ordered relationship without removing the cover column. |
| `app/models/product_image.py` | Add `ProductImage`, filename/position constraints, validators and UTC time. |
| `app/models/__init__.py` | Export `ProductImage` for SQLAlchemy, migrations, tests and shell use. |
| `migrations/versions/<revision>_mm026_product_images.py` | Create the gallery table, indexes/constraints and backfill existing covers from migration head `a25c0de02501`. |
| `config.py` | Raise the bounded request maximum from 6 MiB to 26 MiB so five 5-MiB files plus form overhead can reach server validation. |
| `app/forms.py` | Replace the single `FileField` with the compatible-name `MultipleFileField`; update label only. |
| `app/images.py` | Add group selection/normalization/storage/cleanup helpers and ordered usable-gallery presentation. Keep single-image functions as compatible wrappers. |
| `app/marketplace.py` | Integrate multi-image Create, atomic Edit replacement, eager gallery loading, presentation, and gallery-aware media authorization. |
| `app/operations.py` | Include all ProductImage filenames in reference reconciliation and report cover drift. |
| `app/__init__.py` | Expose ProductImage in the shell and add a helpful bounded 413 upload response if the generic response is insufficient. |
| `app/templates/_image_dropzone.html` | Render multi-file limits, ordered preview container, cover explanation and optional current Edit gallery. |
| `app/templates/form.html` | Pass the new dropzone context without duplicating the image field. |
| `app/templates/product.html` | Render the usable ordered main image, thumbnail links, status region and existing lightbox. |
| `app/static/js/market.js` | Upgrade MM-022 previews to 1–5 files; send only cover to AI; add guarded thumbnail/main/lightbox synchronization. |
| `app/static/css/style.css` | Add bounded upload-preview and product-gallery layouts, focus/current states and narrow-screen behavior. |
| `tests/test_multi_image_gallery.py` | Model, create/edit, compensation, media, rendering, AI integration, maintenance and static-contract tests. |
| `tests/test_multi_image_migration.py` | Fresh/current migration, backfill, constraints, preservation and isolated downgrade/re-upgrade tests. |
| Existing image/AI tests | Update only contracts intentionally changed from one image to an ordered group; retain security behavior. |
| `tests/026-browser-checklist.md` | Define isolated picker/drop, switching, lightbox, keyboard and mobile checks. |
| `tests/026-red-verification.md` | Record collection and missing-feature failures before implementation. |
| `tests/026-green-verification.md` | Record focused, regression, full-suite, schema, local migration and browser results. |
| `tests/preview_multi_image_gallery.py` | Provide loopback-only fictional users/products/files under `.pytest-tmp`. |
| `docs/026-multi-image-gallery-guide.md` | Explain one-to-many images, cover caching, transactions/file compensation and progressive enhancement. |
| `README.md` | Link the guide and summarize the five-image limit. |

No new Python or JavaScript dependency is planned. Pillow, Flask-WTF,
SQLAlchemy and the existing browser APIs already provide the needed behavior.

## 4. ProductImage model

Create `app/models/product_image.py`:

```text
product_images
├─ id          INTEGER primary key
├─ product_id  INTEGER NOT NULL → products.id ON DELETE CASCADE
├─ filename    VARCHAR(255) NOT NULL UNIQUE
├─ position    INTEGER NOT NULL CHECK 0..4
└─ created_at  UTCDateTime NOT NULL

UNIQUE(product_id, position)
INDEX(product_id, position)
```

The composite unique index supports both ordered product retrieval and the
one-row-per-slot rule. A separate product-only index is unnecessary because the
composite begins with `product_id`.

Python filename validation will require the existing safe normalized pattern:
32 lowercase hexadecimal characters followed by `.jpg`. The portable database
check will enforce nonblank/bounded length; migration tests will verify model
and database behavior on SQLite. PostgreSQL uses the same column/relational
constraints.

The relationship will be:

```text
Product.gallery_images
    order_by ProductImage.position
    cascade all, delete-orphan
    passive_deletes true
```

The ProductImage-to-Product relationship uses `back_populates`. The name
`gallery_images` avoids ambiguity with filesystem/Pillow helpers.

## 5. Migration design

Generate one revision after `a25c0de02501`, then inspect/simplify it. It will:

1. create `product_images` with named keys/checks/indexes;
2. query for duplicate non-null legacy cover filenames before backfill;
3. abort safely if one stored filename ambiguously belongs to multiple products;
4. insert position 0 for every non-null `products.image_filename`, using the
   product's `created_at` as the historical row timestamp; and
5. leave every source product/file unchanged.

Tests will create a real MM-025 schema/database with users, products, carts,
orders and cover filenames, upgrade to MM-026, and compare every old row. The
backfill requires no image files to exist because schema migration describes
references, while maintenance describes filesystem health.

Downgrade drops only the gallery table/indexes. Legacy cover filenames remain,
so cards and one-image detail fallback still work.

## 6. Request and form limits

Change `Config.MAX_CONTENT_LENGTH` to `26 * 1024 * 1024`.

This global bound is necessary because Flask rejects the request before route
code can count five files. It is not permission for one 26-MiB photo: the image
service still reads at most `5 MiB + 1 byte` from each file and rejects an
aggregate over 25 MiB.

`ListingForm.image` becomes `MultipleFileField` but retains:

- HTML `id="image"`;
- submitted name `image`;
- optional behavior; and
- normal Flask-WTF CSRF/form validation.

One older single-file multipart test remains a valid one-element group.

The input template supplies `multiple=True` plus the existing JPEG/PNG accept
hint. A dedicated 413 handler may render **Upload too large** with a concise
message; it must perform no business write and reveal no server detail.

## 7. Image service refactor

### 7.1 Preserve the proven single-image validator

Refactor without weakening existing checks:

- internal `read_and_normalize_image(upload, ...)` returns clean JPEG bytes plus
  the exact raw byte count;
- existing `normalized_image_bytes()` remains a compatibility wrapper returning
  only bytes for AI Vision;
- existing `store_image()` remains a one-file wrapper for older callers/tests;
- new `store_images(uploads)` returns ordered safe filenames; and
- new `discard_images(filenames)` safely calls existing containment-aware
  cleanup once per unique filename.

### 7.2 Group algorithm

`store_images()` will:

1. remove only empty browser placeholders (`filename == ""`) from the optional
   field;
2. reject more than five real uploads before reading them;
3. normalize one file at a time using the existing limits;
4. maintain an exact raw-size running total and reject above 25 MiB;
5. store each normalized output through UUID `.pending` → atomic rename;
6. return filenames in upload order; and
7. on any exception, delete every new filename already created and re-raise a
   safe validation/storage error.

Sequential normalization bounds memory better than opening five large decoded
images simultaneously. Each Pillow context is closed before the next file.

### 7.3 Gallery presentation helper

Add a helper that returns ordered usable filenames for one loaded product:

- gallery rows in ascending position when present;
- legacy `image_filename` as a single fallback when there are no rows;
- duplicates removed defensively; and
- missing/invalid filesystem references omitted.

This helper is for presentation only and never repairs rows during GET.

## 8. Create Listing transaction

Keep the existing request-token/replay structure. After ordinary form
validation:

1. call `store_images(form.image.data)`;
2. construct Product text/price/status fields;
3. set `product.image_filename = filenames[0] if filenames else None`;
4. add/flush Product;
5. append ProductImage rows for `enumerate(filenames)`;
6. add ListingSubmission;
7. commit once; and
8. redirect to owner preview.

All error paths call `db.session.rollback()` and `discard_images(new_names)`.
The IntegrityError replay path checks the existing ListingSubmission only after
cleanup/rollback and redirects without creating more files.

The service ignores any browser-submitted product ID, seller ID, position,
cover filename or storage path.

## 9. Edit Listing full replacement

### 9.1 Rendering

Edit receives the same multi-file dropzone but with:

- current gallery thumbnails rendered read-only from authorized media URLs;
- text saying `Leave this empty to keep the current gallery`;
- text saying a new selection replaces all current photos;
- no AI checkbox/provider disclosure; and
- the same first-photo-is-cover explanation.

### 9.2 POST behavior

Capture the current referenced filenames, including the legacy fallback. If the
submitted field has no real files, run the existing text edit only.

If it has one through five files:

1. normalize/store the complete new group;
2. recheck the submitted optimistic Product version;
3. replace the `gallery_images` relationship with new ordered rows;
4. set `image_filename` to new position 0;
5. commit text + gallery together;
6. discard old filenames not present in the new committed group; and
7. redirect to preview.

On form validation, storage, database or `StaleDataError`, rollback and discard
only new names. Never delete old files before commit. `discard_images` remains
best-effort after success; maintenance reports a locked undeleted orphan later.

No Remove All action is added.

## 10. Route loading and media authorization

Product detail and owner preview queries will eager-load
`Product.gallery_images` to avoid one query per thumbnail. Catalogue/card
queries need no gallery loading because they still use the cover pointer only.

The media route will:

1. reject invalid filename shape through existing safe path rules;
2. find a Product whose cover pointer matches; otherwise join ProductImage to
   its Product by filename;
3. apply the current active/sold public and archived-owner policy to that
   product;
4. ensure the safe file exists; and
5. send the normalized JPEG with current headers.

An additional image of an archived product therefore cannot be fetched merely
by guessing its UUID.

## 11. Upload template and browser logic

### 11.1 HTML

Replace the single `<figure>` preview with an empty list/container that
JavaScript populates. The server still renders all instructions and the native
multiple input without JavaScript.

The partial receives explicit flags:

- `vision_ai_available` and provider label;
- `show_vision_ai` (new-listing only);
- `replace_existing_gallery` (Edit only); and
- `current_gallery` (authorized filenames for read-only Edit display).

Do not infer privacy behavior from a missing key; Edit hides the AI section by
scope, while Sell shows enabled/disabled disclosure normally.

### 11.2 MM-022 JavaScript upgrade

The guarded block will maintain:

- one current array of files;
- one array of current object URLs;
- one preview-generation sequence;
- balanced drag depth; and
- safe functions to clear/revoke/render/attach the entire group.

Picker and drop both call one `useFiles()` path. `attachDroppedFiles()` uses one
DataTransfer and verifies the resulting `input.files` count/order. All preview
nodes are created with DOM APIs; filenames use `textContent`.

The code waits until every preview image loads before announcing
`market-mirror:image-ready` with:

```text
detail.file  = first/cover File (AI compatibility)
detail.files = complete ordered File array
```

Any decode error clears the group and emits `image-cleared` once.

### 11.3 AI block

The existing AI listener already consumes `detail.file`; tests will lock this
contract. Update text to say `AI is looking at the cover photo`. A new
selection increments the sequence and aborts the previous request exactly as
before.

`new FormData(listingForm)` followed by `data.delete('image')` removes every
file with that repeated field name from non-vision text suggestion requests.

## 12. Product thumbnail gallery and lightbox integration

The route passes `gallery` as a short ordered list of safe `{filename, url,
position}` presentation objects.

The template renders:

- main link/image from `gallery[0]`;
- existing placeholder when empty;
- thumbnail `<a>` links only when `gallery|length > 1`;
- `data-gallery-index`, media URL and escaped alt/accessibility values;
- position-aware main alt text;
- `aria-current="true"` only on the initial thumbnail; and
- a polite selection status.

Add a separate guarded MM-026 JavaScript block before/alongside MM-017. On an
unmodified primary click/keyboard activation of a thumbnail it:

1. prevents media-link navigation;
2. updates main `src`, `alt`, trigger `href`/label;
3. updates lightbox `data-src`/alt and removes an old loaded `src` so opening
   loads the selected file through existing error handlers;
4. moves `aria-current` to the activated link;
5. updates polite status with `Showing photo N of M`; and
6. leaves focus on the thumbnail.

Modified clicks retain normal open-in-new-tab/window behavior. If the selected
main image fails, retain a usable page/thumbnail controls and let a later
selection recover. The existing lightbox block continues handling zoom/open/
close/focus/scroll; it reads the updated data at open time.

## 13. CSS plan

Add scoped styles:

- `.image-upload-preview-list` — responsive grid of up to five previews;
- `.image-upload-preview-item` and `.is-cover` — bounded item and textual cover
  badge;
- `.product-gallery-thumbnails` — wrapping or locally scrolling row;
- `.product-gallery-thumbnail` — at least 44 × 44, fixed visual box;
- `[aria-current="true"]` — strong border plus an additional selected marker;
- `.product-gallery-status` — screen-reader/visible polite helper as chosen by
  the plan tests; and
- stable main image aspect box using `object-fit: contain`.

Reuse theme variables and current focus rules. At ≤30rem, previews use a small
two-column/auto-fit grid and thumbnail strip stays within its parent. Reduced
motion keeps existing no-transform behavior.

## 14. Maintenance changes

`maintenance images` will build the reference set as the union of:

- non-null Product.image_filename values; and
- all ProductImage.filename values.

Cover drift count is computed for products that have gallery rows when:

- no position-0 row exists; or
- position-0 filename differs from Product.image_filename.

Products with no gallery rows retain legacy compatibility and are not silently
repaired by the read-only command. Output remains aggregate counts without
private filenames. Explicit orphan deletion uses the union, so an additional
gallery photo is never mistaken for an orphan.

## 15. Test-first sequence

After PLAN-026 approval, follow this order strictly:

1. Add `tests/test_multi_image_gallery.py`,
   `tests/test_multi_image_migration.py` and browser checklist only.
2. Update existing MM-017/MM-022/MM-023/MM-024 tests only where the approved
   single-file presentation contract intentionally becomes multi-file.
3. Keep existing byte-validation, AI privacy, card-cover, ownership and
   lightbox tests as regressions rather than deleting them.
4. Run `--collect-only`; repair test syntax/fixtures until collection is clean.
5. Run focused tests against unchanged application code.
6. Record failures for missing ProductImage/table/multiple input/gallery
   rendering/JavaScript behavior in `tests/026-red-verification.md`.
7. Implement models/migration first.
8. Implement image group helpers and Create/Edit transactions.
9. Implement media/maintenance integration.
10. Implement upload/product templates, JavaScript and CSS.
11. Run focused tests until Green.
12. Run existing image, AI, marketplace, hardening, cart/order and mobile
    regression groups.
13. Run the complete pytest suite and schema consistency check.
14. Back up and migrate the stopped real local database only after isolated
    migration tests pass.
15. Run an isolated real-browser check using generated product pictures only.
16. Write the student guide and actual Green evidence.

No application/model/migration file changes during steps 1–6.

## 16. Planned automated test coverage

### 16.1 Model and migration

- valid 0–4 positions, deterministic relationship order and UTC timestamp;
- invalid negative/5+ positions, missing parents/nulls, duplicate slot and
  duplicate filename;
- unsafe/short/long filename validation;
- fresh migration to one head;
- MM-025 database upgrade with 0/1/many legacy covers;
- exact backfill position 0 without modifying Product rows/files;
- duplicate legacy cover preflight failure without partial schema/data;
- preservation of users/products/carts/orders/messages/events;
- isolated downgrade leaves cover pointer and older tables; and
- re-upgrade succeeds.

### 16.2 Image group service

- empty optional placeholder → no images;
- one and exactly five valid mixed JPEG/PNG inputs;
- six images rejected before storage;
- per-file exact/over 5 MiB and aggregate exact/over 25 MiB;
- one invalid image after stored valid predecessors removes all new files;
- Pillow format/frame/pixel/orientation/transparency/metadata rules retained;
- all stored names unique, pattern-safe and ordered;
- simulated filesystem failure cleans earlier files;
- `discard_images` deduplicates and never escapes upload root; and
- single-image/AI wrappers retain behavior.

### 16.3 Create/Edit routes

- authentication, real CSRF and owner-only edit;
- zero/one/five create rows with cover synchronization;
- forged positions/filenames/seller/product fields ignored;
- request-token replay creates one product/gallery;
- invalid form/image/database commit leaves no partial rows/orphans;
- Edit empty input keeps exact gallery/files;
- Edit valid set replaces all rows and deletes old after commit;
- Edit invalid/storage/commit/stale-version keeps every old row/file and removes
  every new file;
- title/price/status behavior remains; and
- safe 413 performs no mutation.

### 16.4 Presentation/media/maintenance

- zero image placeholder, one image no thumbnail strip, 2–5 ordered thumbnails;
- legacy cover fallback when no rows;
- missing one image omitted; all missing placeholder;
- escaped titles/attributes and position-aware accessible labels;
- card/search/seller/cart uses cover only;
- active/sold public media, archived owner allowed, strangers/anonymous denied;
- additional images authorized through ProductImage;
- invalid/unreferenced/missing/path filenames return 404;
- reference union prevents gallery orphan deletion;
- missing/orphan/drift aggregate reporting; and
- read-only views/maintenance do not mutate.

### 16.5 JavaScript/CSS contracts

- `multiple`, limit instructions and guarded required nodes;
- one common picker/drop group path;
- count, per-file and total-size checks;
- DataTransfer attaches every file and verifies order/count;
- one object URL per file and complete cleanup on replace/reject/pagehide;
- no fetch/submit from preview block;
- filenames assigned through textContent, no innerHTML;
- ready event exposes first `file` plus all `files`;
- AI request receives only first, text requests delete all images;
- thumbnail click updates main/link/lightbox/current/status;
- modified click/no-JS fallback preserved;
- initialization safely returns on unrelated pages;
- 44px controls, focus/current, bounded grids/strip and reduced motion; and
- prior AJAX search/recommendations/lightbox scripts remain intact.

### 16.6 Concurrency and regression

- two replays of one create token produce one gallery;
- overlapping Edit submissions use Product.version so one wins and loser keeps
  no new files;
- maintenance does not race in destructive mode during tests;
- MM-017 lightbox, MM-022 drag/drop, MM-023/024 AI, MM-025 checkout, generated
  demo images and full project suite pass.

## 17. Verification commands

Expected commands, with actual counts recorded only after execution:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_multi_image_gallery.py tests\test_multi_image_migration.py tests\test_image_dropzone.py tests\test_product_image_interactions.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_multi_image_gallery.py tests\test_multi_image_migration.py tests\test_image_dropzone.py tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm026-red
.\.venv\Scripts\python.exe -m pytest tests\test_multi_image_gallery.py tests\test_multi_image_migration.py tests\test_image_dropzone.py tests\test_product_image_interactions.py tests\test_ai_vision.py tests\test_gemini_vision.py -q --basetemp=.pytest-tmp\mm026-green
.\.venv\Scripts\python.exe -m pytest tests\test_marketplace.py tests\test_hardening.py tests\test_cart.py tests\test_checkout.py tests\test_mobile_navigation.py tests\test_operations.py -q --basetemp=.pytest-tmp\mm026-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm026-full
powershell -ExecutionPolicy Bypass -File .\scripts\local.ps1 check
.\.venv\Scripts\python.exe -m pip check
```

Concurrency tests use separate sessions against a temporary file-backed SQLite
database and bounded worker timeouts. Test temp paths never point to `instance`
or real uploads.

## 18. Isolated browser checklist

The loopback fixture will create one seller, one active product with five
generated colored/labelled angle images, and another legacy one-image product.
It will never read the real database/uploads.

Checks:

1. sign in as fictional seller;
2. Sell page states count/per-file/total/cover rules;
3. file picker selects five generated JPEG/PNG files;
4. five ordered previews appear and first is labelled Cover;
5. selecting six or one invalid file group clears all with useful feedback;
6. Save creates one listing and redirects to owner preview;
7. five product thumbnails appear in order;
8. keyboard activation of photo 3 updates main image, selected semantics and
   status;
9. lightbox opens photo 3 and retains close/focus behavior;
10. narrow mobile view contains preview/thumb rows without page overflow;
11. Edit with empty image input keeps all five;
12. isolated two-image replacement changes cover/gallery together;
13. public card shows only replacement cover;
14. JavaScript-disabled page retains multiple input and ordinary media links;
15. archived additional media remains owner-private; and
16. console has no new errors on pages with/without galleries.

Actual drag/drop will be tested only if the browser tool exposes a safe local
file-drag primitive; otherwise automated JavaScript/static contracts plus real
picker behavior will be reported honestly. Screenshots will capture the
five-preview upload and selected-thumbnail product page.

## 19. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Five files exceed old 6-MiB request limit | Explicit 26-MiB request bound plus 5-MiB each/25-MiB group validation. |
| One bad file leaves partial storage | Track new names; compensate all on any group/transaction failure. |
| Edit deletes old images before success | Commit new rows/cover first; delete old files only afterward. |
| Cover and position 0 disagree | One service writes both; migration backfill; model/route/maintenance drift tests. |
| Old listings break | Retain cover column and legacy fallback; migration only adds/backfills. |
| Cards download five images | Cards retain cover pointer only; gallery eager loading limited to detail/preview. |
| Additional archived photo leaks | Media filename resolves through ProductImage then applies product visibility/owner policy. |
| AI sends all selected photos | Ready event preserves first-file contract; vision FormData created from cover only; explicit tests. |
| Text AI accidentally sends repeated image fields | `FormData.delete('image')` removes all; contract test. |
| Browser preview trusted as validation | Server independently checks bytes/count/sizes/formats. |
| Object URLs leak memory | Track/revoke complete URL array on every transition/pagehide. |
| Filename/title injects markup | Jinja escaping and textContent/DOM properties only. |
| Migration meets corrupt duplicate cover references | Preflight abort; backup and operator resolution rather than ambiguous ownership. |
| Bigger global request increases resource use | Still hard-capped at 26 MiB; per-file sequential reads and pixel/frame limits. |
| PostgreSQL not installed locally | Portable constraints/queries; SQLite tests plus generated SQL/schema review; document live PostgreSQL limit. |

## 20. Local database migration and rollback

Before real migration:

1. confirm the server is stopped;
2. run all isolated migration/focused tests;
3. check duplicate cover references;
4. copy `instance/market-mirror.sqlite` to a timestamped
   `instance/backups/market-mirror-before-mm026-*.sqlite`;
5. record size and SHA-256;
6. run local migration once; and
7. run schema consistency/readiness checks.

This additive migration does not alter files. If migration fails, stop and
inspect; do not delete images or force a revision stamp.

After real MM-026 listings exist, casual downgrade would remove gallery rows
for positions 1–4 while leaving only cover pointers. Restore the coordinated
backup or use an explicit export/reversal procedure instead of downgrading a
valuable database.

## 21. Student documentation

The guide will explain at high-school level:

- one Product to many ProductImage rows;
- why position 0 is the cover;
- why the cover pointer is retained for backward compatibility;
- browser preview versus real upload;
- why every file is re-encoded;
- database rollback versus filesystem compensation;
- how JavaScript progressively enhances thumbnail links; and
- why only the cover is sent to AI.

A small exercise will have the student predict row/file state after a valid
three-photo save, an invalid fifth photo, and a failed Edit commit.

## 22. Definition of done

MM-026 is done only when:

1. every AC-026 criterion maps to passing automated/browser evidence;
2. valid Red evidence predates implementation;
3. model/migration/backfill and schema checks pass;
4. Create/Edit file/row compensation tests pass;
5. media privacy, AI cover-only and maintenance tests pass;
6. previous image/lightbox/AI/card/cart/order/mobile regressions pass;
7. complete pytest suite and dependency check pass;
8. real database is backed up and upgraded with no old row/file changes;
9. isolated browser picker, switching, lightbox, keyboard/mobile checks pass;
10. no test modifies the real catalogue/uploads; and
11. beginner documentation accurately explains behavior and limitations.

## 23. Approval and completion record

The user explicitly approved **PLAN-026** on 2026-11-07. The test-first Red
checkpoint is preserved in `tests/026-red-verification.md`. The focused suite
then passed 32 tests and the full project suite passed 460 tests. The local
database was backed up, migrated to `b26c0de02601`, and checked with 24 legacy
covers backfilled and zero cover drift.
