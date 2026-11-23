# PLAN-017 — Product image interactions: implementation and test plan

Status: APPROVED — user explicitly approved PLAN-017 on 2026-10-29 (Asia/Shanghai)

Date: 2026-10-29 (Asia/Shanghai)

Approved specification: MM-017, explicitly approved by the user on 2026-10-29.

## 1. Outcome and boundaries

Add a gentle hover zoom and accessible image lightbox to the existing product detail template. Preserve the existing product data, media permissions, catalogue cards, forms, recommendations and shared JavaScript behaviour. No new pictures, database changes, runtime dependencies or hosting changes are needed.

The specification defines **what** should happen. This plan defines **how** we intend to build and check it. Only documentation has changed at this stage. After plan approval, define and validate tests before modifying application code.

## 2. Files and responsibilities

| File | Planned work | Why it belongs here |
| --- | --- | --- |
| `app/templates/product.html` | Wrap an existing picture in a fallback image link; add one initially closed native dialog with image, accessible name, error message and close button. | HTML supplies the structure and meaningful controls. |
| `app/static/css/style.css` | Add narrowly scoped image-frame, hover, focus, dialog, backdrop and reduced-motion styles. | CSS controls appearance without changing data. |
| `app/static/js/market.js` | Add a guarded lightbox initializer and open/close/error handlers independent of current features. | JavaScript reacts to user actions. |
| `tests/test_product_image_interactions.py` | New isolated pytest integration tests. | Verify server-rendered markup, fallbacks, escaping and permissions before implementation. |
| `tests/017-browser-checklist.md` | Define browser scenarios and expected results before implementation. | Real browser behaviour cannot be proved by HTML assertions alone. |
| `tests/017-red-verification.md` | Record collection and initial test failures, with commands and reasons. | Demonstrate that new tests detect the missing feature. |
| `tests/017-green-verification.md` | Record focused, regression and browser results, including limitations. | Provide evidence, not just a claim of completion. |
| `docs/017-product-image-interactions-guide.md` | Explain the code and provide a small exercise. | Help the student confidently explain the finished feature. |
| `docs/evidence/017-*.png` | Screenshots of the actual implemented lightbox. | Show desktop and narrow-screen results. |

Existing files and historical documents will remain intact. Tests will reuse `tests/conftest.py` fixtures where practical; any browser-test helpers must stay separate from the application runtime.

## 3. Planned technical design

### 3.1 HTML: a useful page before JavaScript runs

Keep the existing check for both an image filename and an image file. If either is absent, render the current non-interactive “No photo yet” placeholder, without a lightbox trigger or dialog.

For an available image, render a link containing the image. Its `href` points to the existing `market.media` URL. Without JavaScript, clicking it opens the authorized image normally; there is no dead button. Keep native link semantics: Tab focuses it and Enter activates it. Do not add a button role or pretend that a link supports Space.

Render a native `<dialog>` only in the available-image branch. Give it a safely escaped accessible name using the product title, a close button with `type="button"`, an image with meaningful alternative text, and a hidden error message. The dialog must not have an `open` attribute initially. Avoid putting it inside seller/contact forms.

The modal picture uses the same media URL, with no new endpoint or high-resolution source. Jinja's normal escaping remains enabled for titles and attributes. Do not use `safe` filters or inline event handlers.

### 3.2 CSS: zoom without moving the page

Use a block-level rounded frame with `overflow: hidden` and a visible outer keyboard focus outline. Scale only its image to `1.05`, not the frame. A transform changes how the image is drawn without changing the space it occupies in the page layout.

Enable the approximately 200 ms transform transition only inside `(hover: hover) and (pointer: fine)` conditions. Under `prefers-reduced-motion: reduce`, remove both the scaling and transition. Touch users still tap to enlarge.

Style only the open dialog as a viewport-sized overlay. A closed dialog must remain hidden; avoid unconditional `display: flex` or `display: grid` that could override its closed state. Add an explicit closed-state guard if needed for older browsers that do not understand dialog defaults.

Use a dark backdrop, constrained image area, and `object-fit: contain`. Reserve space for a high-contrast close button at least 44 by 44 CSS pixels. Use viewport-height fallbacks and dynamic viewport units where available, so phone browser controls do not hide the close button. Keep titles/error text wrapping safely and prevent horizontal overflow. Do not inherit the page's general button margins or colours in a way that makes the close control disappear in dark mode.

### 3.3 JavaScript: small, self-contained event handlers

Initialize only when the trigger, dialog and required child elements exist and native `showModal`/`close` functions are available. Unsupported browsers retain the image link. Keep the initializer locally scoped and do not interfere with current recommendation, view-tracking or suggestion handlers.

For an ordinary click/keyboard activation, open the dialog using `showModal()`. Preserve modified link actions such as Ctrl-click and middle-click. Prevent ordinary link navigation only once the enhanced opening succeeds. Guard against opening an already-open dialog.

On successful opening:

1. Save the previously focused trigger, scroll coordinates and any inline scroll-lock styles that will be changed.
2. Lock background scrolling without losing the current scroll position, using a contained fixed-body strategy if required for touch browsers. Preserve existing style values and restore them exactly, rather than clearing unrelated styles.
3. Focus the close button. Native modal behaviour makes the rest of the page inert. Explicitly handle Tab/Shift+Tab if needed to keep keyboard focus inside the dialog; avoid an unnecessary competing focus-trap implementation.

The close button closes the dialog. Escape uses the dialog's cancel/close lifecycle. A click on the empty overlay area closes it; a click on the image, caption/error message or close control must not be misclassified as a backdrop click. Use the full-screen dialog's empty-area target rather than closing on every bubbled click. Avoid accidental closure when a drag starts on the image and ends outside it.

Use one cleanup path on the dialog's `close` event for all ways of closing. Restore saved scroll-lock styles and scroll position, then return focus to the trigger without scrolling it into a different position. Ensure opening exceptions also release any partially applied lock. Register handlers once.

Attach image load/error handlers before assigning the modal source if setting it dynamically. Also check `complete` and `naturalWidth` to catch cached load failures. A failed image shows readable status text inside the dialog while keeping the close button usable. Reopening may retry the same authorized source; no unsafe URL construction, `innerHTML` or third-party fetches are needed.

## 4. Test-first sequence

1. Obtain approval of this plan.
2. Write the pytest integration tests and browser acceptance checklist. Use temporary databases and upload directories only.
3. Run pytest collection to confirm tests are discoverable, then run the focused suite against the unchanged application.
4. Record the expected Red results. New lightbox-markup assertions should fail because the feature is absent; preservation/permission tests may already pass. Dependency/import/setup failures do not count as a validated feature failure.
5. Implement the HTML, CSS and JavaScript only after those tests are defined and validated.
6. Run the focused suite, fix actual failures, and run the full existing pytest suite.
7. Exercise the browser checklist against an isolated test server with synthetic fixtures, then make a read-only visual check on an existing local product if useful. Do not change real listings or user data to manufacture error cases.
8. Save evidence and the beginner guide, with results clearly separated into passed, failed and not verified.

Suggested PowerShell commands, from the project directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm017-red
.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm017-green
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm017-regression
```

The assistant will run these commands during implementation. They are included so the student can understand and reproduce the process. Pytest owns these specifically named temporary directories and may clear their contents on reruns; never use a directory holding real data as `--basetemp`.

## 5. Pytest integration cases

Use `db_app`, `client`, `user_factory` and `product_factory` with test-owned image files. Parse rendered HTML using the Python standard library where practical, avoiding brittle whitespace/string matching and new packages solely for markup assertions.

| Case | Expected assertion | Specification |
| --- | --- | --- |
| Valid active listing with an existing image | One image link, correct authorized media URL, one closed dialog, meaningful alt/name, close button, initially hidden error message. | AC-02, AC-04 |
| Sold listing | Existing public visibility rules remain unchanged; allowed detail view has image interaction markup. | AC-11 |
| Owner preview, including archived product | Owner can view the image interaction; non-owner preview and public archived access remain forbidden according to current routes. | AC-10, AC-11 |
| No image filename | Placeholder remains; no trigger/dialog. | AC-08 |
| Filename present but file absent | Same safe placeholder behaviour, without broken interactive markup. | AC-08 |
| Title containing quotes, angle brackets and HTML-like text | Parsed alt/name retain literal title text; no injected element or executable attribute is created. | AC-10 |
| Media authorization | Public active/sold images and owner-only archived access retain current authorization behaviour. | AC-10 |
| Other pages | Catalogue cards remain ordinary detail links; no detail dialog leaks into unrelated pages. | AC-09, AC-11 |
| Read-only rendering | Rendering details does not change listing values, image references or user records. | AC-11 |
| Script integration | Existing external script remains deferred; new controls contain no inline JavaScript; existing forms still target the same actions. | AC-09, AC-11 |

A test that only finds `showModal` or a CSS selector in a source file is not proof of runtime behaviour. Do not substitute such checks for the browser cases below.

## 6. Browser acceptance matrix

Define the following scenarios before implementation. Use the available controlled browser and, if already available, browser automation driven by pytest. First inspect supported capabilities rather than assuming media emulation or network interception is available. No browser-test package installation is planned; explain any required addition before making it. If a capability cannot be exercised, record that limitation instead of claiming it passed.

| Scenario | Steps and expected evidence | Spec |
| --- | --- | --- |
| Hover | Move pointer onto/off the picture. Observe slight zoom and return; frame and nearby text stay fixed. | AC-01 |
| Open and image identity | Activate the picture. One dark full-screen dialog appears with the same image, correct accessible name and no navigation. | AC-02 |
| All close paths | Separately close by button, Escape and empty overlay area. Clicking the image leaves it open. | AC-03 |
| Keyboard | Tab to image link, Enter to open, Tab and Shift+Tab while open, then Escape. Focus begins at close, stays in modal, then returns to image link. | AC-04 |
| Scroll state | Open while scrolled partway down; attempt background scrolling; close each way. Page is locked only while open and returns to the same position. | AC-05 |
| Repeated use | Perform at least five open/close cycles; verify one dialog, responsive close controls and no accumulating events/errors. | AC-09 |
| Responsive layout | Check desktop, 320-pixel width, a short landscape viewport, portrait and landscape image fixtures, and resize while open. Close control remains reachable; image stays contained. | AC-06 |
| Browser zoom | Use actual 200% browser zoom when available; record separately from viewport resizing, which is not equivalent. | AC-06 |
| Motion preference | With reduced-motion enabled, no hover scaling or animation; modal still opens and closes. | AC-07 |
| Touch | Tap image and close controls using supported touch testing or a real touch device; do not label a desktop mouse click as a touch-device test. | AC-02, AC-06 |
| Missing image | Test absent and missing-file fixtures; only placeholder appears. | AC-08 |
| Late load failure | Use a test-owned fixture whose image becomes unavailable after rendering. Open modal; readable error and usable close control remain. | AC-08 |
| JavaScript disabled | Image link still reaches the authorized image, no dead control or visible closed dialog. | AC-08 |
| Unsupported dialog | In a controlled browser fixture with capability unavailable, keep working image-link fallback. Do not mutate the live user's browser globals to simulate this. | AC-08 |
| Shared-script regressions | Check catalogue and listing-form pages for new errors; suggestions/recommendations still function with isolated fixtures and view tracking is not retriggered by opening the modal. | AC-09, AC-11 |
| Escaping and appearance | HTML-like title is displayed literally; close button/focus indicator remain legible in supported light/dark modes. | AC-04, AC-10 |

Inspect browser errors and distinguish existing failures from new feature failures. Save screenshots showing an open desktop lightbox and a narrow-screen view; screenshots supplement behaviour checks, not replace them.

## 7. Risks and mitigations

- **Closed dialog accidentally visible:** scope display/layout styles to the open state and verify initial rendering and no-JavaScript mode.
- **Page remains frozen after closing:** route every close mechanism through the same cleanup handler and test repeated cycles.
- **Keyboard focus escapes or gets lost:** use native modal behaviour, verify both Tab directions, and explicitly restore trigger focus.
- **Close button blends into the overlay:** use lightbox-specific colours and focus styles rather than relying on generic button styling.
- **Tiny screens or very tall pictures:** reserve control space, constrain both image dimensions and test resizing/zoom.
- **Cached broken image misses an error event:** combine load/error listeners with a completed-image validity check.
- **JavaScript fails on unrelated pages:** guard absent nodes/support and keep the initializer independent of existing features.
- **Browser checks affect real data:** use isolated fixtures for failure cases and mutations; final real-site preview is read-only.
- **Legacy browser lacks dialog support:** preserve the plain authorized image link instead of adding a large compatibility library.

## 8. Completion and handoff

Complete when focused tests and the regression suite pass, core browser opening/closing/keyboard/scroll checks pass, and the remaining acceptance criteria have documented results or clearly disclosed environment limitations. Do not describe untested cases as verified. Investigate any regressions before delivery; report unresolved blockers and preserve previous work.

Deliver a short explanation, links to changed files and the beginner guide, actual test results, and screenshot evidence. No database rollback should be needed because the feature does not modify stored data. If an implementation rollback is necessary, reverse only this feature's edits while preserving other user changes.

Student exercise: open a laptop picture, close it each of the three ways, then repeat using only Tab, Enter and Escape. Explain the different roles of HTML, CSS and JavaScript, and why CSS zoom does not improve source resolution.

## 9. Approval gate

Reply **“I approve PLAN-017”** to authorize the test-first implementation sequence above. Approval will allow the assistant to write and validate tests, implement the feature after the Red checkpoint, and verify it; it does not claim any tests have already run. No HTML, CSS or JavaScript has been modified at this planning stage.
