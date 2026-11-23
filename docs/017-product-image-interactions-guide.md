# How the product image zoom and lightbox work

Implemented under approved MM-017 and PLAN-017, 2026-10-29.

## Try the result

Start Market Mirror normally, then open http://127.0.0.1:5000/products/14 (the demo laptop). Hover over its picture: it grows slightly inside its frame. Click to see a larger version. Close with the Close button, Escape, or a click in the empty dark area. Clicking or dragging the picture itself does not close it.

No packages need installing. The feature uses HTML, CSS and JavaScript already supported by modern browsers. No products, prices, accounts or uploaded photos were changed.

## Three files, three jobs

| File | Job | Simple explanation |
| --- | --- | --- |
| `app/templates/product.html` | Structure | Defines the image link, dialog, close button and error message. |
| `app/static/css/style.css` | Appearance | Controls zoom, spacing, colours and fitting the picture on screen. |
| `app/static/js/market.js` | Behaviour | Responds to clicks and keyboard actions, opens/closes the dialog and restores the page. |

### 1. HTML gives the browser meaningful building blocks

The main picture sits inside an `<a>` link. The link points to the same protected media URL that already serves the product picture. Without JavaScript, it still opens the picture. This is **progressive enhancement**: start with something useful, then add the richer experience when the browser supports it.

The `<dialog>` element represents a temporary window above the page. It starts closed. Its accessible name includes the product title, so assistive technology can explain what it contains. The close button has `type="button"`, which prevents it from acting like a form submission.

The template keeps the old missing-image check. If no usable local photo exists, the visitor sees “No photo yet” instead of a misleading enlarge control.

Jinja escapes product titles. For example, a title containing `<img>` must appear as text, not create a new HTML element. We did not add `innerHTML` or inline JavaScript handlers.

### 2. CSS zooms the picture without rearranging the page

`transform: scale(1.05)` means “draw this image at 105% of its ordinary size.” It does not enlarge the layout space around it. The wrapper uses `overflow: hidden`, which clips the small excess at its rounded edges. This prevents the picture from growing over the product description.

The transition takes 200 milliseconds (one fifth of a second). It applies only when the device has a fine pointer and supports hover. A reduced-motion media query removes the scaling and animation for visitors who have requested less motion.

The open dialog covers the viewport—the currently visible part of the browser. The picture retains its proportions with `object-fit: contain` and limits on both its width and height. The close button has reserved space above it. Closed dialogs and explicitly hidden elements remain hidden, rather than accidentally being displayed by the layout rules.

### 3. JavaScript connects actions to responses

An **event listener** is a small function that runs when something happens, such as a click or key press. The lightbox initializer first checks that all required elements and native dialog functions exist. On other pages, it simply exits; it does not try to open a nonexistent picture.

On an ordinary image click:

1. Save the page's current scroll position and the specific styles that must change.
2. Temporarily fix the body in place so the page behind the overlay cannot scroll.
3. Call `showModal()` and put keyboard focus on Close.
4. Load the larger display from the same image URL, after registering load/error handlers.
5. Cancel the link's normal navigation because the modal opened successfully.

Ctrl-click, middle-click and other modified link actions keep their usual browser behaviour. If enhancement fails, normal image-link navigation remains available.

### 4. Closing is more than hiding a box

Every close method uses the same cleanup path. It restores the exact saved style values, restores scrolling to the original position, and puts focus back on the image link. We release the scroll lock immediately rather than waiting for the browser's queued close event. A delayed event from an older opening cannot unlock a newly reopened dialog.

Native modal behaviour makes the background inactive. Since Close is the only keyboard-focusable control inside this dialog, Tab and Shift+Tab keep focus there. Escape uses the dialog cancellation event. For outside clicks, the handler checks that the pointer started in the empty overlay area; dragging from the image to the background does not count as an outside click.

### 5. What happens when a picture fails?

A file can disappear or fail to load after the page was rendered. The modal's image listens for `load` and `error`. On failure, the broken picture is hidden and a readable message appears; Close still works. A check of `complete` and `naturalWidth` also catches already-completed failed loads.

The lightbox does not generate or upscale pictures. It shows more of the existing image by using more screen space. A blurry source image will still be blurry when displayed larger.

## How we tested it

Eight focused pytest checks cover rendered markup, placeholder cases, title escaping, media permissions and preservation of existing data/forms. They first produced five expected failures and three passes, then all eight passed after implementation. The full existing suite passed: **235 tests**.

Real-browser checks covered opening and all close methods, keyboard controls, repeated use, scroll restoration, hover scaling, portrait/landscape fitting, narrow/short screens, image-load failure and fallbacks. See `tests/017-green-verification.md` for the exact results and unverified cases; passing Python tests alone does not prove JavaScript or CSS behaviour.

## Your small practice task

1. Open the laptop picture, then close it using each of the three methods.
2. Use Tab to reach the image link, Enter to open, Tab/Shift+Tab inside, and Escape to close. Notice where focus returns.
3. Open a tall picture on a narrow browser window. Check that Close remains visible.
4. Explain in your own words: why is the image a link, why do we clip its hover zoom, and why do we restore focus?

If you can explain those answers, you understand both the visual feature and the accessibility work behind it.
