# MM-022 — Drag-and-drop product image upload with thumbnail preview

Status: APPROVED — user explicitly approved MM-022 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

## 1. Purpose

Improve the image field on the authenticated **Sell a product** page so a seller
can either choose a picture normally or drag one onto a clearly marked upload
zone. While an acceptable file is dragged over the zone, the zone is visibly
highlighted. After one image is chosen or dropped, the page shows a small local
thumbnail before the seller selects **Save listing**.

The preview is only a browser preview. It does not upload, store, modify, analyze
or publish the image before the existing listing form is submitted.

MM-022 extends MM-001 through MM-021. It must not remove or weaken existing
authentication, listing ownership, CSRF protection, image normalization, AI
suggestions, mobile navigation, lightbox behavior, database integrity or tests.

## 2. Current behavior and authoritative validation

The Sell page currently renders `ListingForm.image` as an ordinary file input.
The form already uses `multipart/form-data`. On submission, `store_image()`:

- accepts one nonempty JPEG or PNG;
- reads no more than 5 MiB plus one detection byte;
- rejects animated/multiple-frame files;
- rejects images above 12 million source pixels;
- verifies that the bytes form a readable image;
- applies EXIF orientation, limits output to 1600×1600;
- removes original metadata; and
- stores a new UUID-named JPEG outside user-controlled paths.

Those server rules remain the source of truth. Browser checks improve feedback
but are not security checks and never replace Pillow validation.

## 3. Scope

MM-022 applies to the new-listing page at `/listings/new`, whose visible heading
is **Sell a product**.

The Edit listing page keeps its current ordinary image input in this feature.
Adding replacement-image preview/edit behavior later requires a separate
specification because it must define how the existing stored image and a newly
selected replacement are presented together.

No catalogue card, product-detail image, seller profile, generated demo image or
database record changes until an ordinary valid listing submission succeeds.

## 4. Upload-zone structure

Replace the plain visual presentation of the Sell page's image input with one
labelled upload zone containing:

- a short instruction such as **“Drag a product photo here”**;
- an equally clear file-picker action such as **“or choose a JPEG or PNG”**;
- the existing single file input connected to its visible label;
- a concise limit note: **“Maximum 5 MiB”**; and
- a status/feedback element for selection and error messages.

The real `<input type="file" name="image">` remains part of the form. The drop
zone must place the dropped file into that exact input so normal form submission,
CSRF handling and server validation continue unchanged.

The input declares `accept="image/jpeg,image/png"` as a file-picker hint. This
attribute is not treated as validation because operating systems and browsers
can still supply misleading types.

The zone accepts exactly one file. It must not add a second upload field, upload
queue, gallery, camera capture requirement or external file service.

## 5. Drag behavior

### 5.1 Entering and hovering

- When a drag containing files enters the upload zone, add a dedicated active
  state such as `.is-drag-over`.
- The active state uses a clear border/background change and does not depend on
  color alone. It must remain readable in light and dark themes.
- `dragover` prevents the browser's default handling only for the zone so the
  file can be dropped there.
- Moving between child elements inside the zone must not make the highlight
  flicker. Nested `dragenter`/`dragleave` events need balanced handling or an
  equivalent containment check.

### 5.2 Leaving, dropping and cancellation

- Leaving the complete zone removes the highlight.
- Dropping removes the highlight immediately, whether the file is valid or not.
- `dragend` and browser cancellation also restore the normal appearance.
- Dropping a file on the zone must not navigate the browser to that local file.
- Drag events outside this particular zone are not converted into uploads and
  must not accidentally submit the form.

### 5.3 Invalid drag payloads

- A drag containing no files does not activate selection behavior.
- Dropping multiple files is rejected as a group with a clear message such as
  **“Choose one product photo.”** It must not silently select the first file.
- A directory or unsupported item is rejected and cannot produce a misleading
  thumbnail.

## 6. File selection rules and feedback

The same client-side handling runs after a file-picker selection and a drop.

Preliminary browser checks:

- exactly one file;
- nonzero byte size;
- no larger than 5 MiB; and
- JPEG or PNG according to `File.type`, with `.jpg`, `.jpeg` or `.png` filename
  fallback only when the browser supplies an empty MIME type.

If a file fails a preliminary check:

- clear the real file input;
- remove any old thumbnail and revoke its temporary object URL;
- show a concise, non-technical message in the feedback element; and
- keep the rest of the form editable and unsubmitted.

Messages must not claim that a file is secure or server-approved. A successful
client preview may say **“Photo selected”**, not **“Valid image uploaded.”** The
server may still reject corrupt, spoofed, animated, oversized-pixel or otherwise
unreadable image bytes after submission.

## 7. Thumbnail preview

After one preliminarily acceptable file is selected or dropped:

- create a browser-local object URL using `URL.createObjectURL(file)`;
- show one small thumbnail below or inside the zone;
- preserve the image aspect ratio using `object-fit: cover` or `contain` without
  stretching;
- keep the thumbnail within the form at 320 CSS pixels without horizontal
  overflow;
- show the safely inserted filename as text, truncated/wrapped when long; and
- use useful alternative text such as **“Selected product photo preview”**.

The preview is not read from or written to Market Mirror's media route. It is
not inserted with `innerHTML`, and the filename is assigned with `textContent`
so HTML-like filenames cannot execute markup.

If the browser cannot decode the selected file into the preview image, remove
the broken thumbnail, clear the input, revoke the temporary URL, and tell the
seller to choose a readable JPEG or PNG.

Selecting/dropping another valid file replaces the prior thumbnail rather than
adding another. Revoke the previous object URL when replacing or rejecting a
file and on page unload to avoid retaining unnecessary browser memory.

## 8. File-picker and keyboard behavior

Drag-and-drop is an optional convenience, never the only way to choose a photo.

- Clicking the zone's picker label/control opens the normal file chooser.
- The file input remains keyboard reachable or has an equivalent correctly
  labelled native control; Enter/Space behavior must remain native.
- Keyboard-only users receive the same thumbnail and status after file-picker
  selection.
- The zone must have an understandable accessible label/instructions.
- The feedback element uses `aria-live="polite"`; invalid-file feedback may also
  use an appropriate alert association without repeatedly announcing drag hover.
- Focus is not moved automatically after selection or drop.
- A visible focus style is provided for the file input/picker control.
- The zone itself must not pretend to be a button if it does not implement full
  button keyboard behavior.

## 9. Progressive enhancement and compatibility

Without JavaScript, the page continues to show and submit the ordinary labelled
file input. The user can choose a file and the existing server validation gives
the final result; drag highlighting and preview are unavailable.

If required browser APIs such as `DataTransfer`, `URL.createObjectURL`, or
assigning `input.files` are unavailable:

- the normal file chooser remains usable;
- do not show a thumbnail for a dropped file unless that exact file has been
  successfully attached to the real input; and
- provide a short instruction to use the file chooser when a drop cannot be
  connected safely.

The shared script initializes only when all MM-022 elements exist. On Home,
Explore, product detail, Profile, Edit listing and all other pages it returns
without changing behavior or creating console errors.

## 10. Form submission and error behavior

- Choosing or dropping a file never automatically submits the form.
- **Save listing** remains the only ordinary submission control.
- The listing form continues to submit once with the existing request token and
  CSRF token.
- AI category/price requests continue to delete the `image` field from their
  `FormData`; selecting a preview must never send image bytes to the AI routes.
- If another field fails server validation and the page reloads, browsers do not
  repopulate file inputs for security reasons. The preview may therefore reset,
  and the user must choose the image again. The page must not claim it retained
  the file.
- If server image validation fails, use the existing form error area and leave
  the database and upload folder in their existing compensated/rolled-back
  state.
- Double-clicking Save, replayed request tokens, storage failures and database
  failures retain their existing server behavior.

## 11. Visual and responsive design

- Reuse the existing theme variables (`--surface`, `--background`, `--text`,
  `--muted`, `--brand`, `--brand-dark`, `--line`).
- The idle zone has a clear dashed or otherwise recognizable boundary.
- Drag-over has both a stronger border and a background/outline change.
- The preview is intentionally small (approximately 6–10rem on its longest
  displayed dimension) and never replaces the full product image experience.
- Filename and messages wrap without widening the page.
- The zone, file control and preview work at desktop, 320px portrait, short
  landscape, 200% zoom when available, light mode and dark mode.
- No animation is required. If a short color/border transition is added, it must
  be disabled under `prefers-reduced-motion: reduce`.

## 12. Security and privacy

- The browser preview is local and must not make a fetch/XHR request.
- Do not send the file to an AI model, analytics service, CDN or third party.
- Do not expose local filesystem paths. Browsers may supply a protected fake path;
  only the safe display filename may be shown.
- Do not trust MIME type, extension, filename, object URL or thumbnail success as
  proof of safety. The existing server byte validation remains authoritative.
- Do not use `innerHTML`, inline event-handler attributes or executable content
  from the filename.
- Keep CSRF, login requirements, seller identity derivation, ownership rules,
  image limits and normalized storage unchanged.
- Dropping/selecting/previewing alone performs no database mutation and creates
  no server-side file.

## 13. Acceptance criteria

| ID | Expected outcome |
| --- | --- |
| AC-022-01 | `/listings/new` presents a clearly labelled single-image drag-and-drop zone with ordinary JPEG/PNG file-picker fallback and a 5 MiB note. |
| AC-022-02 | File drag enter/over visibly highlights the full zone without flicker; leave, drop, cancellation and invalid drops always remove the highlight. |
| AC-022-03 | Dropping one preliminary-valid JPEG/PNG attaches it to the real `image` input, prevents file navigation and does not submit the form. |
| AC-022-04 | File-picker selection and drop use the same handler and produce one thumbnail, safe filename text and polite “Photo selected” feedback. |
| AC-022-05 | Replacing a selection replaces the thumbnail and revokes the prior object URL; unload/error cleanup revokes the current URL. |
| AC-022-06 | Empty, over-5-MiB, unsupported, multiple, directory-like and preview-decode-failing choices clear the input/preview and show useful feedback. |
| AC-022-07 | The thumbnail has meaningful alternative text, preserves aspect ratio, stays small and causes no horizontal overflow at 320px. |
| AC-022-08 | Keyboard/file-picker use remains fully available with visible focus; the feedback is accessible and focus is not unexpectedly moved. |
| AC-022-09 | With JavaScript disabled or required drop APIs unavailable, the normal labelled file input and server submission remain usable without misleading preview state. |
| AC-022-10 | Preview activity makes no server request, upload, AI request or database change; only Save listing can begin the existing server workflow. |
| AC-022-11 | Existing server validation still rejects corrupt/spoofed/oversized/animated images and preserves transaction/file compensation. |
| AC-022-12 | Edit listing and unrelated pages retain current behavior; shared JavaScript produces no new errors there. |
| AC-022-13 | AI suggestion requests still exclude image bytes, and MM-001–MM-021 tests continue to pass. |

## 14. Edge cases for the later plan and tests

The Planning and Testing stages must cover at least:

- picker selection versus actual mouse/pointer file drop;
- dragenter/dragleave across nested zone children;
- drag cancellation and repeated entering/leaving;
- one JPEG, one `.jpeg`, one PNG and uppercase filename extensions;
- empty MIME type with supported filename fallback;
- misleading MIME/extension and corrupt bytes;
- zero-byte and exactly/just over 5 MiB files;
- multiple files, directories and non-file drag data;
- landscape, portrait, square, transparent PNG and very long filename;
- HTML-like filename text and filenames containing quotes/Unicode;
- preview image decode error;
- selecting the same file twice and replacing it with another file;
- object URL creation/revocation counts;
- submit after drop proving the real input contains the file;
- no automatic submission/request during preview;
- invalid title/price submission resetting the browser file selection honestly;
- server failure/rollback and no orphan upload;
- AI category/price requests with a selected image;
- JavaScript disabled and missing `DataTransfer`/object-URL support;
- keyboard-only selection, visible focus and polite status;
- desktop, 320px, short landscape, dark mode and 200% zoom when available; and
- initialization on pages without the upload zone.

## 15. Out of scope

MM-022 does not add:

- multiple product images;
- image reordering, cropping, rotation, filters or AI background removal;
- camera-only capture;
- paste-from-clipboard upload;
- remote image URLs or cloud drives;
- an upload progress bar or upload-before-submit endpoint;
- permanent draft storage;
- changes to the Edit listing existing-image/replacement experience;
- changes to Pillow normalization, size/pixel limits or database schema;
- a new JavaScript/CSS package; or
- public deployment.

## 16. Beginner explanation

A drag-and-drop zone is still connected to a normal file input. JavaScript reads
the browser's `drop` event and places the selected file into that input. The
thumbnail comes from a temporary **object URL**, which is like a short-lived
browser address pointing to the local file. It is not a Market Mirror upload.

The server must still inspect the real bytes after Save listing. A filename such
as `photo.png` can lie, just as changing a text file's name does not turn it into
a picture. Client-side checks help the user quickly; server-side checks protect
the application.

## 17. Subsequent SDD stages

After explicit MM-022 approval:

1. Write PLAN-022 with the exact template, CSS, JavaScript, test fixtures,
   browser checks, cleanup and rollback design.
2. Wait for explicit PLAN-022 approval.
3. Write pytest/static contracts and a browser checklist before implementation.
4. Run and record the expected Red result.
5. Implement only the approved behavior.
6. Run focused tests, server image-security regressions, the full suite and an
   isolated real-browser drag/drop check.
7. Record Green evidence and a high-school-level learning guide.

No HTML, CSS, JavaScript, route or test implementation is authorized by this
specification alone.

## 18. Approval gate

Please review these main decisions:

1. MM-022 applies only to **Sell a product**, while Edit listing stays unchanged;
2. one file only, JPEG/PNG, maximum 5 MiB, with the server still authoritative;
3. picker and drag/drop both show the same local thumbnail preview;
4. invalid/multiple files clear the preview and show a useful message; and
5. choosing/dropping never uploads automatically—Save listing remains required.

The user explicitly approved this specification on 2026-11-02. The Planning
stage may begin, but feature tests and implementation still require separate
PLAN-022 approval.
