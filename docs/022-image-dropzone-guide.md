# MM-022 — Image drag-and-drop learning guide

## What we built

The Sell a product page still has a normal file input, but it now sits inside a
drag-and-drop zone. A seller can use the file chooser or drag one JPEG/PNG onto
the zone. The border highlights during a file drag, and a small preview appears
after selection.

Nothing is uploaded at that moment. The seller must still select **Save listing**.

## How the browser pieces work

A browser fires several **events** during dragging:

1. `dragenter` — the file enters the zone;
2. `dragover` — the file moves within it;
3. `dragleave` — it leaves a part of the zone; and
4. `drop` — the user releases it.

The script counts nested enter/leave events so the highlight does not flicker as
the pointer crosses the instruction, input and help text inside the same zone.

`DataTransfer` is the browser object carrying dragged files. After checking that
there is exactly one file, JavaScript connects it to the real file input. If the
browser cannot do that safely, Market Mirror asks the seller to use the ordinary
chooser instead of showing a misleading preview.

## What an object URL means

`URL.createObjectURL(file)` creates a temporary browser-only address for the
selected file. The thumbnail uses that address. It is not a web URL, database
record or upload.

The script calls `URL.revokeObjectURL()` when the picture is replaced, rejected,
cannot be decoded, or the page is left. This is memory cleanup—similar to putting
away a tool after using it.

## Why the server checks the image again

Browser checks give quick feedback, but filenames and MIME types can lie. A text
file can be renamed `photo.png`. Therefore the existing Python/Pillow code still:

- limits bytes and pixels;
- reads the actual image format;
- rejects corrupt or animated input;
- removes metadata; and
- writes a clean JPEG with a generated filename.

The browser is the convenience layer. The server is the trust boundary.

## Progressive enhancement

**Progressive enhancement** means starting with something dependable and adding
convenience when supported. Here, the dependable part is the native file input
and normal multipart form. JavaScript adds drag highlighting and preview. If the
script is unavailable, the seller can still choose and submit a picture.

## Files to explain during a demonstration

1. `app/templates/_image_dropzone.html` — real input and preview structure.
2. `app/marketplace.py` — enables the zone only on new listings.
3. `app/static/js/market.js` — drag events, validation and object URLs.
4. `app/static/css/style.css` — idle, drag-over, focus and mobile layout.
5. `app/images.py` — authoritative byte validation and normalization.
6. `tests/test_image_dropzone.py` — feature and preservation contracts.

## A good classroom explanation

“The browser gives the seller an immediate preview, but it does not trust or
store the file. Save listing sends the real input through the existing secure
Flask route. Pillow then verifies the bytes and creates a clean image. This keeps
the interface friendly without weakening the server.”
