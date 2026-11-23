# MM-017 verification — 2026-10-29

Specification and plan were explicitly approved. Tests and the browser checklist were defined before application changes; the observed Red checkpoint is recorded in `017-red-verification.md`.

## Pytest results

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm017-green
# 8 passed in 17.92s

.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm017-regression
# 235 passed in 283.56s (0:04:43)

.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm017-final
# Final focused recheck: 8 passed in 24.32s
```

Tests use temporary SQLite databases and upload folders. The new tests assert rendering contracts, not pretend execution of browser code. No new dependencies were installed.

## Browser evidence

Used the controlled in-app browser with an isolated loopback fixture server on port 5017 (`python -m tests.preview_image_interactions`). It creates an in-memory database and synthetic landscape/portrait photos under `.pytest-tmp/mm017-browser-*`, not the real instance database. Final visual check used the existing Silver laptop listing on port 5000, as an anonymous visitor.

Verified:

- Click and link Enter activation open exactly one native modal with the correct image and accessible name; initial focus goes to Close.
- Close button, Escape and empty-area click close the modal. Clicking the image does not close it. Dragging from image to background also leaves it open.
- Tab and Shift+Tab keep focus on Close. Closing returns focus to the image link.
- From scroll Y=288, opening fixed the body at top=-288px; attempted background scrolling did not move the background. Closing restored Y=288 and cleared the temporary body/root styles.
- Five additional keyboard open/close cycles ended with one closed dialog, released body styles and trigger focus.
- Browser inspection exposed the asynchronous native close-event timing. Cleanup was hardened to release the scroll lock synchronously and ignore delayed close events when already reopened; repeated-cycle and scroll checks were then performed on that updated script.
- Actual laptop hover computed transform was `matrix(1.05, 0, 0, 1.05, 0, 0)`; pointer exit restored `none`. The wrapper remained at the same position and dimensions (approximately 504.94 by 378.70 CSS pixels), confirming no frame layout shift.
- Landscape image fitted the desktop overlay. Portrait image fitted at 320x640 and 640x320. At 320x640 its displayed bounds were approximately x=43.43, y=76, width=233.14, height=544. At 640x320 it was 96x224. No horizontal overflow; Close remained 44 pixels high and inside the viewport.
- Resized the viewport while the dialog was already open; controls stayed visible. Reset the viewport override afterwards.
- A test-only invalid modal image URL produced the readable unavailable-image message and usable close control. Reopening retained safe error handling.
- The no-script fixture (script tag omitted) and unsupported-dialog fixture (test-only support shim) both navigated to the authorized image normally, with no dead control or exposed closed dialog. These are controlled fallback simulations, not changes to the user's browser preferences or an older-browser compatibility certification.
- Catalogue and product recommendations rendered in the isolated app without a lightbox on the catalogue. Real laptop recommendations also rendered. Browser warning/error logs were empty on the inspected catalogue and real laptop page. Deliberate missing-image requests in failure fixtures are expected failures, not regressions.
- Server-side tests verified absent/missing images, archived image permissions, escaped HTML-like titles, existing forms and unchanged test product/user rows.

Screenshots:

- `docs/evidence/017-laptop-lightbox.jpg`: actual demo laptop in the completed overlay.
- `docs/evidence/017-narrow.jpg`: isolated portrait fixture at 320 pixels wide.

The browser returned JPEG screenshot bytes, so the evidence uses `.jpg` rather than the initially planned `.png`. The disposable port-5017 test server was stopped after verification; its test files remain available for inspection.

## Limits — not claimed as verified

The available browser control surface did not expose motion/colour-scheme emulation or genuine touch configuration. Reduced-motion and dark-mode rules were reviewed in code, but not exercised with those actual preferences. Real touch-device use, actual 200% browser zoom, modified-link actions, and an older browser were not tested. Narrow viewport testing is not equivalent to browser zoom or a touch-device test.

AI suggestion form actions and personalization tracking were covered by the existing Python regression suite, but not re-exercised end-to-end in an authenticated browser during this feature check. No claim is made that HTTP request counts were measured. Opening/closing handlers contain no write or analytics requests; existing tracking code was left unchanged.

No database migration, real listing modification, image replacement, external publication or package installation was performed. The actual marketplace server remains local on port 5000.
