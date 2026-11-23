# PLAN-022 — Drag-and-drop image upload and thumbnail preview

Status: APPROVED — user explicitly approved PLAN-022 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

Approved specification: MM-022, explicitly approved by the user on 2026-11-02.

## 1. Outcome and boundaries

Enhance only the new-listing page at `/listings/new` with:

- a clearly labelled single-file drop zone around the real image input;
- a visible nested-drag-safe highlight;
- one browser-local thumbnail and safe filename after picker or drop selection;
- early, helpful feedback for obvious client-side problems; and
- progressive fallback to the ordinary file input.

The existing server submission remains unchanged in meaning. `store_image()` is
still the only authority for image bytes, limits, metadata removal and storage.
There is no pre-upload endpoint, database migration, package, external service,
AI image processing, multiple-image support or public deployment.

## 2. Planned files and responsibilities

| File | Planned change |
| --- | --- |
| `app/marketplace.py` | Add an explicit `image_dropzone` render flag to new-listing responses only; Edit listing remains false/default. |
| `app/templates/form.html` | Special-case only the flagged `image` field and include a dedicated partial; retain the ordinary loop for every other field/form. |
| `app/templates/_image_dropzone.html` | Render the real file input, instructions, 5 MiB note, accessible status, hidden preview, safe filename target and existing server-error area. |
| `app/static/css/style.css` | Style idle/drag-over/focus/preview/error states with theme variables and responsive overflow protection. |
| `app/static/js/market.js` | Add one guarded MM-022 IIFE for file/picker/drop handling, validation, object-URL lifecycle and preview decode failure. |
| `tests/test_image_dropzone.py` | Define HTML scope, accessibility, static JS/CSS, no-mutation and server-preservation contracts before implementation. |
| `tests/022-browser-checklist.md` | Define real-browser drag, picker-equivalent, preview, replacement, invalid cases, mobile and no-script checks before implementation. |
| `tests/preview_image_dropzone.py` | Supply a temporary app/database and test-only draggable file sources so real drag events can be exercised without the user's files/data. |
| `tests/022-red-verification.md` | Record collection and expected missing-feature failures. |
| `tests/022-green-verification.md` | Record focused, image-security, full-suite and browser results honestly. |
| `docs/022-image-dropzone-guide.md` | Explain drag events, `DataTransfer`, object URLs, progressive enhancement and why the server must revalidate. |
| `docs/evidence/022-*` | Store screenshots if the available browser interface supports local export. |

No model, migration, requirements/lock, media route or AI route changes are
planned.

## 3. Route and rendering design

Change the existing listing helper conceptually to:

```python
def render_listing(form, title, code=200, image_dropzone=False):
    return render_template(
        "form.html",
        title=title,
        form=form,
        submit="Save listing",
        listing=True,
        image_dropzone=image_dropzone,
    ), code
```

Call it with `image_dropzone=True` for both:

- GET `/listings/new`; and
- invalid POST `/listings/new` returning 400.

Edit listing uses the default `False` on its GET and invalid POST. Successful
creation still redirects to the existing owner preview and never renders the
drop zone itself.

This explicit flag is preferred over checking the title text or request path in
Jinja. Presentation scope is decided by the route, not fragile user-visible text.

## 4. Template design

### 4.1 Form loop

In `form.html`, preserve the current generic field loop. Only when all are true:

```text
listing is true
image_dropzone is true
field.name == "image"
```

include `_image_dropzone.html`. Otherwise render the existing field markup
unchanged. This guarantees Login, Register, Profile, Edit listing and all text/
choice listing fields retain their current structure.

### 4.2 Partial structure

The partial will render stable, unique elements equivalent to:

```text
div.field.image-upload-field
  label[for=image]
  div#product-image-dropzone.image-dropzone[data-max-bytes=5242880]
    p#product-image-drop-instruction
    input#image[type=file][name=image][accept=image/jpeg,image/png]
    p#product-image-help
    figure#product-image-preview.image-upload-preview[hidden]
      img#product-image-preview-thumbnail
      figcaption#product-image-preview-name
  p#product-image-upload-status[aria-live=polite]
  div#image-errors[role=alert]
```

The exact label remains the WTForms field label: “Optional product photo (JPEG
or PNG, up to 5 MiB)”. The drop instruction says “Drag a product photo here” and
the help identifies the normal chooser plus maximum size.

The file input receives an `aria-describedby` value containing instruction,
help, status and error IDs. The native file input stays visible and focusable; it
is not replaced by a fake keyboard control. The figure begins with the `hidden`
attribute and no `src`, preventing an empty image request.

Jinja renders existing field errors as escaped text. JavaScript writes filenames
and feedback only through `textContent`.

## 5. JavaScript design

Add one self-contained IIFE before the existing AI listing code. It queries:

- `#listing-form`;
- `#product-image-dropzone`;
- `#image`;
- preview figure/image/name; and
- status element.

If any element or `URL.createObjectURL`/`URL.revokeObjectURL` is unavailable, it
returns and the native input remains usable. The IIFE stores only:

- the current object URL;
- an integer drag depth; and
- cleanup/listener functions.

It does not use global mutable state or change the existing `listingForm` AI
variable.

### 5.1 Common selection function

One `useFiles(files, source)` function handles both picker and drop inputs:

1. Convert the file list to an array without reading bytes.
2. Reject counts other than one; multiple files are never silently truncated.
3. Reject size zero or greater than `5 * 1024 * 1024`.
4. Accept exact `image/jpeg` or `image/png` MIME. Only when MIME is empty, use a
   case-insensitive `.jpg`, `.jpeg` or `.png` filename fallback.
5. For a drop, create a fresh `DataTransfer`, add the one file, assign its
   `.files` to the real input, then verify that the input actually contains the
   same one file. If construction/assignment fails, clear state and ask the user
   to use the chooser.
6. Revoke the previous object URL before creating a new one.
7. Assign filename with `textContent`, set the thumbnail source to the new object
   URL and keep success wording pending until `load` confirms decoding.

The picker already owns `input.files`; it uses the same checks without rebuilding
the list.

### 5.2 Preview load/error

- On `load`, reveal the figure and set polite status to “Photo selected: <name>”.
- On `error`, revoke the URL, remove `src`, hide the figure, clear filename and
  input, and announce “Choose a readable JPEG or PNG.”
- Listener/state ordering prevents a late event from an older replaced preview
  from clearing the new selection. The current URL/file identity is checked
  before handling completion.

### 5.3 Clearing and URL cleanup

`clearSelection(message, clearInput=true)`:

- revokes the current URL once;
- removes thumbnail `src`;
- hides the preview;
- clears filename text;
- clears `input.value` when requested; and
- uses `textContent` for the provided status.

It runs for every invalid selection. `pagehide` (and optionally `beforeunload` as
a fallback) revokes the remaining URL without changing form state. Replacing a
file revokes the old URL before allocating the new one.

### 5.4 Drag state

Use a `dragDepth` counter only for drags whose `dataTransfer.types` contains
`Files`:

- `dragenter`: prevent default, increment and add `.is-drag-over`;
- `dragover`: prevent default and set `dropEffect="copy"` where writable;
- `dragleave`: decrement to a floor of zero, removing the class only at zero;
- `drop`: prevent default, reset depth/class, reject directory-like entries or
  pass the dropped `files` into the common handler; and
- `dragend`: reset depth/class.

The counter prevents flicker while moving over the input, instruction, help and
preview children. Non-file drag content is ignored rather than highlighted.

Directory detection uses `DataTransferItem.webkitGetAsEntry()` only when
available. A directory result is rejected. Its absence does not weaken the
server; unsupported payloads still fail assignment/preview/server validation.

### 5.5 Request isolation

The code calls no `fetch`, `XMLHttpRequest`, form submission or media route.
Existing AI assistance continues to create `FormData(listingForm)` and delete
`image` before its request. Tests assert that contract remains present.

## 6. CSS design

Add scoped selectors near existing form styles:

- `.image-dropzone`: `min-width:0`, dashed 2px theme border, rounded corners,
  surface/background, padding and grid/flex spacing;
- `.image-dropzone.is-drag-over`: solid/stronger border, background and inset
  outline/box-shadow so the state is not color-only and does not shift layout;
- `.image-dropzone:focus-within`: visible theme outline;
- `.image-upload-help` and status: muted text, wrapping, reserved small height;
- `.image-upload-preview`: small flexible row/grid with safe overflow;
- thumbnail: approximately `8rem × 6rem`, `max-width:100%`, `object-fit:contain`,
  themed border/background;
- filename: `min-width:0` and `overflow-wrap:anywhere`; and
- `[hidden]` preview remains absent.

At the existing mobile breakpoints the preview can stack vertically if needed.
No fixed widths may widen a 320px page.

No animation is necessary. If a transition is used during implementation,
`prefers-reduced-motion: reduce` must disable it and tests must cover that rule.

## 7. Test-first execution sequence

1. Obtain explicit PLAN-022 approval.
2. Write `tests/test_image_dropzone.py` and `tests/022-browser-checklist.md`
   without changing application/template/CSS/JavaScript feature code.
3. Run test collection. The new suite must collect against the unchanged app.
4. Run focused tests and record the expected Red result. Expected failures are
   the missing route flag, partial/markup, styles and JavaScript handler.
5. Implement route flag and template partial first, then CSS, then guarded JS.
6. Run focused tests until Green without weakening approved contracts.
7. Run existing server image-security tests and listing/AI/shared-script tests.
8. Run the complete suite.
9. Read the local-preview guidance, start the temporary port-5022 fixture and
   execute real-browser drag/drop, preview, replacement, invalid, mobile and
   no-script checks.
10. Stop the fixture, reset browser overrides, restart the real local server,
    perform only a read-only real Sell-page/startup check and record evidence.

Planned commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm022-red
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm022-green
.\.venv\Scripts\python.exe -m pytest tests\test_marketplace.py tests\test_hardening.py tests\test_ai.py tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm022-image-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm022-regression
```

## 8. Pytest coverage matrix

| Group | Required cases | Specification coverage |
| --- | --- | --- |
| Route scope | GET and invalid POST create include flag/zone; Edit GET/invalid POST do not | AC-022-01, 12 |
| Authentication | Anonymous create redirects safely and renders no zone; no rows/files created | security/preservation |
| Markup | One real file input, accept types, max bytes, instructions, help, described-by IDs, polite status and hidden preview | AC-022-01, 07–09 |
| Escaping | HTML-like/Unicode server error and static labels remain escaped; JS filename target is text-only | AC-022-06, security |
| Static JS structure | Guarded IIFE; picker/change and drag events; shared handler; no inline handlers | AC-022-02–06, 09, 12 |
| Drop semantics | Files-only activation, depth counter, prevent default, class reset, multiple/directory rejection and DataTransfer assignment verification | AC-022-02, 03, 06 |
| File checks | Zero, max boundary, over max, MIME choices and empty-MIME extension fallback are explicit | AC-022-04, 06 |
| Object URL lifecycle | Create once per valid file; revoke on replace, reject, decode error and page leave; stale events protected | AC-022-05, 06 |
| Request isolation | New handler contains no fetch/submit; AI handler still deletes image; preview GET/JS causes no DB/file mutation | AC-022-10, 13 |
| CSS | Dashed idle, non-color drag state, focus-within, bounded object-fit preview, wrapping and 320px-safe rules | AC-022-02, 07, 08 |
| No-script fallback | Complete labelled file input is server-rendered, not created by JS | AC-022-09 |
| Server validation | Real valid JPEG/PNG works; corrupt/spoof/empty/large/pixels/animated rejects; no orphan and rollback preserved | AC-022-11 |
| Regression | Edit field, AI, image lightbox, mobile nav and full suite remain green | AC-022-12, 13 |

Static source assertions will check stable behavior/structure, not brittle wording
or JavaScript formatting where a browser behavior check is stronger.

## 9. Browser fixture and acceptance design

Create `tests/preview_image_dropzone.py` on port 5022. It will use a temporary
SQLite database/uploads directory and one temporary seller. It will never import
or change the real local database.

The fixture will generate in `.pytest-tmp`:

- valid landscape JPEG;
- valid portrait and transparent PNG;
- zero-byte file;
- text bytes named `.png`;
- a file exactly 5 MiB and one byte over for client-limit checks; and
- HTML-like/Unicode filenames when supported by the temporary filesystem.

To test genuine production drag handlers without requiring the user's File
Explorer, the fixture may inject test-only draggable source cards on a dedicated
fixture-only page/response. Each source creates a synthetic `File` in its
`dragstart` handler. Browser pointer dragging that card onto the real production
zone therefore generates normal `dragenter`, `dragover`, `dragleave` and `drop`
events. This harness is registered only inside the preview application; no
test-only route, script, bypass or credential enters production code.

Browser checklist:

1. Desktop Sell page: real input/instructions visible, preview hidden, Save
   listing enabled and no request caused by initial page.
2. Drag a valid fixture JPEG over nested zone children; observe stable highlight,
   copy behavior, then drop and confirm highlight clears.
3. Verify one thumbnail, correct aspect ratio, safe filename text, Photo selected
   status, input has one file and form has not submitted.
4. Replace JPEG with PNG and verify one preview plus old object-URL revocation via
   fixture instrumentation where browser APIs permit observation.
5. Drop multiple, zero-byte, unsupported, over-limit and directory-like sources;
   confirm input/preview clear and messages appear without navigation/submission.
6. Trigger corrupt-image preview decode failure and confirm usable cleared state.
7. Use the native picker path with a fixture file only if browser upload controls
   are available and the test-file interaction is authorized; otherwise record
   the limitation and rely on common-handler tests plus drag verification.
8. Fill valid required fields and submit the temporary listing after a drop;
   verify owner preview and normalized authorized media. Repeat an invalid text
   field case and confirm the browser honestly resets the file selection.
9. Select a file, request category/price suggestions and verify no image request
   body/server upload occurred before Save.
10. At 320px and short landscape, verify thumbnail/filename wrap and
    `scrollWidth <= innerWidth`; verify mobile navigation does not cover Save.
11. Keyboard through label/input/status/Save and verify visible focus and logical
    order without automatic focus movement.
12. Controlled no-script response: native file input and Save submission remain
    usable; no dead preview placeholder is exposed.
13. Visit Edit listing and unrelated pages; verify ordinary input/current
    behavior and no console errors.
14. Check available dark/reduced-motion/200% zoom capabilities honestly.
15. Save screenshots if supported and inspect console errors/warnings.

No test clicks Save against the user's real database. The real server receives a
read-only GET only after the disposable fixture is stopped.

## 10. Security and data-preservation checks

- Compare database table snapshots and temporary upload listings before/after
  GET, drag and preview-only activity.
- Use the existing CSRF-protected multipart route for the one fixture submission.
- Confirm seller ID still comes from `current_user`, never JS/form data.
- Confirm a spoofed `.png`, corrupt image, excessive byte/pixel count and
  multi-frame image never create a committed product or leftover upload.
- Confirm filename content cannot become markup and local paths are not rendered.
- Confirm the object URL remains browser-local and no production code sends it
  to the server.
- Confirm AI requests delete the image field.
- Confirm request-token replay behavior remains idempotent.

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Preview looks successful but file is unsafe | Use “Photo selected” wording and retain full server byte validation. |
| Dropped file is not actually submitted | Assign through `DataTransfer`, verify `input.files`, and refuse misleading preview if assignment fails. |
| Moving over child nodes flickers highlight | Balanced file-only drag-depth counter, reset on drop/dragend. |
| Browser navigates to dropped local file | Prevent default for file dragover/drop inside the zone. |
| Multiple files silently lose data | Reject the whole multiple selection. |
| Object URLs leak browser memory | Single tracked URL; revoke on replace, reject, decode error and page leave. |
| Old image load/error changes new state | Compare current URL/file identity before event handling. |
| Filename executes HTML | Jinja escaping plus JS `textContent`; no `innerHTML` or inline handlers. |
| JavaScript failure removes upload ability | Keep the complete native input server-rendered and visible. |
| Edit listing changes unintentionally | Explicit new-route-only render flag and negative tests. |
| Preview sends image to AI | Preserve `data.delete('image')` and verify no preview fetch. |
| Mobile preview widens/gets covered | `max-width:100%`, wrapping/min-width rules and real 320px/end-of-page checks. |
| Client and server size/type rules drift | Reuse constant 5 MiB in explicit data attribute/test contract; server remains authoritative. |

## 12. Rollback and recovery

MM-022 stores no new data before Save and changes no schema. To roll back:

1. remove the create-route render flag;
2. restore the ordinary image-field branch in `form.html` and remove the partial;
3. remove scoped image-dropzone CSS;
4. remove the guarded MM-022 IIFE; and
5. run listing/image/AI tests plus the complete suite.

The original file input behavior remains inside the enhanced partial throughout,
so a CSS/JS problem can also be mitigated by disabling only the enhancement
script while the secure server upload continues to work.

## 13. Beginner concepts to document

The final guide will explain:

- **drag events:** enter, over, leave, drop and why default navigation is stopped;
- **DataTransfer:** the browser container carrying dragged files;
- **progressive enhancement:** a normal input works before JavaScript adds help;
- **object URL:** a temporary local browser address, not an upload;
- **event listener:** code that waits for an interaction;
- **client versus server validation:** fast feedback versus actual trust boundary;
- **memory cleanup:** revoking object URLs when they are no longer needed; and
- **safe text insertion:** `textContent` keeps filenames from becoming HTML.

## 14. Approval gate

This plan commits to:

1. an explicit new-listing-only template flag;
2. a visible native file input inside the drop zone for accessible fallback;
3. one common selection/preview path for picker and drop;
4. a nested-drag-safe depth counter and verified `DataTransfer` assignment;
5. one tracked object URL with complete cleanup;
6. unchanged authoritative Pillow/server validation and AI exclusion; and
7. tests plus an isolated browser fixture before touching real application data.

The user explicitly approved this plan on 2026-11-02. The Testing stage may now
begin; tests and the browser checklist must be written and validated Red before
any feature implementation.
