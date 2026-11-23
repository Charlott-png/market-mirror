# MM-022 Green verification

Date: 2026-11-02 (Asia/Shanghai)

## Automated verification

The implementation-first focused run passed before browser validation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm022-green
# 17 passed in 20.87s
```

Targeted marketplace, upload, security, mobile-navigation and form regressions:

```text
101 passed in 133.25s
```

Complete project regression suite:

```text
371 passed in 688.29s
```

## Browser-discovered regression and test-first correction

The first live preview check exposed that the site's Content Security Policy
blocked the temporary local `blob:` image URL. A failing pytest contract was
added first, then `blob:` was allowed only in the `img-src` directive. The
updated focused module now contains 18 passing tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm022-csp-green
# 18 passed in 10.59s
```

This narrow policy change does not allow remote scripts, styles, frames or form
destinations. It permits only a browser-local image preview.

## Isolated live-browser verification

The disposable MM-022 browser fixture used a temporary SQLite database and did
not touch the real Market Mirror catalogue. Verified results:

- the real image picker displayed a bounded preview and the selected filename;
- a 1448×1086 PNG preview rendered at 127×95 pixels inside the drop zone;
- replacing the file revoked the previous temporary object URL;
- selecting `README.md` showed `Choose a JPEG or PNG photo.`, hid the preview,
  and cleared the input;
- previewing and replacement performed zero network fetches;
- at 320 pixels wide, the page had no horizontal overflow and the preview
  stayed inside the drop zone;
- without `market.js`, the real file input and normal Save Listing form remained
  available;
- the production drop-event path accepted a 600×300 JPEG, attached it to the
  real input, and submitted a temporary listing whose product page displayed
  the normalized stored image;
- dropped multiple, over-5-MiB and corrupt-image cases produced their specific
  messages, cleared the preview and left no drag highlight; and
- the Edit Listing page kept its existing ordinary file input and received no
  new drop-zone behavior.

The browser console contained no warnings or errors on the checked edit page.

The in-app browser's physical pointer-drag helper focused the test control but
did not carry its generated `File`. The fixture therefore used a user-clicked,
browser-native `DataTransfer`/`DragEvent` accessibility fallback to exercise the
same production `dragenter`, `dragover` and `drop` listeners. The successful
server submission proves the dropped file was attached to the real form input,
not merely displayed as a thumbnail. A quick human pointer-drag remains in the
manual classroom-demo checklist because automation cannot prove mouse feel.

