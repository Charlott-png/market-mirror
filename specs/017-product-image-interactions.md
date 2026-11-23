# MM-017 — Product image hover zoom and lightbox

Status: APPROVED — user explicitly approved MM-017 on 2026-10-29 (Asia/Shanghai)

Date: 2026-10-29 (Asia/Shanghai)

## 1. Purpose

Make a product's main picture easier to inspect without leaving its detail page. Add a small hover zoom and a full-screen lightbox (a dark overlay containing a larger picture). This supplements the existing approved specifications; it does not replace any previous context, requirements or documents.

## 2. Current application and scope

The product page is rendered by `app/templates/product.html`. Its main image uses the existing authorized `market.media` URL and the product title as alternative text. Missing images display “No photo yet”. Styles are in `app/static/css/style.css`; `app/static/js/market.js` is already loaded with `defer` in the base template.

This change applies to the main image on product detail pages, including owner previews that use this template. Catalogue cards, recommendations, image uploads, database records, prices, permissions and existing business actions must remain unchanged. No new framework, external service, image-generation call, database migration or production deployment is required.

## 3. Required behaviour

### H-01 — Hover zoom

- On a device supporting hover and a fine pointer, hovering over the main picture scales it to approximately 1.05 times its normal size with a short, smooth transition (about 200 milliseconds).
- Zoom stays clipped inside the existing rounded image frame. It must not change surrounding layout or overlap product information.
- Moving the pointer away restores the original scale.
- The pointer indicates that the picture can be enlarged. Touch devices do not depend on hover.
- With the operating system's reduced-motion preference enabled, disable the animated zoom. Opening the lightbox still works.

### L-01 — Open the lightbox

- Clicking or tapping an available main product image opens a viewport-covering dark overlay without navigating away or submitting a form.
- Keyboard users can reach the image control with Tab and activate it using the control's native keyboard interaction. A button supports Enter and Space; an image link supports Enter.
- The overlay shows the same product image at a larger available display size. Preserve its aspect ratio and show the entire image without stretching or cropping.
- Use the existing stored image and authorized media URL. Enlarging is not AI upscaling and cannot create additional source detail.
- The overlay begins closed. Opening it repeatedly must not create additional overlays or duplicate handlers.

### L-02 — Close the lightbox

- Provide a clearly visible close button with an accessible name, such as “Close image”.
- Close on Escape and on a click/tap on the empty dark area outside the image and close control.
- Clicking the image itself must not close the overlay.
- Restore normal page scrolling and return keyboard focus to the image control after closing. Preserve the user's page scroll position.
- All close mechanisms must work after repeated open/close cycles.

### A-01 — Accessibility and responsive layout

- Use an accessible modal dialog with an accessible name derived safely from the product title and meaningful image alternative text.
- Move focus into the dialog on opening; keep Tab/Shift+Tab within the open dialog. Background controls must not be keyboard-interactive while it is open.
- Maintain visible focus indicators. Make the close button at least 44 by 44 CSS pixels and keep it reachable independently of image dimensions.
- Prevent background scrolling while open and restore the previous scroll behaviour on close.
- Fit the image and controls within the viewport, including narrow 320-pixel layouts, portrait and landscape pictures, short screens and 200% browser zoom. No horizontal page overflow may be introduced.
- Resizing the viewport while open must keep the close button visible and the picture contained.

### F-01 — Missing images and graceful fallback

- A product with no image or a missing local image continues to display the existing non-interactive “No photo yet” placeholder; no unusable lightbox trigger is offered.
- If an image request fails after page rendering, the page remains usable. An opened overlay must retain its close controls and provide a readable unavailable-image message rather than trapping the user.
- If JavaScript is disabled or required dialog support is unavailable, the ordinary product image remains visible. Do not expose a dead interactive control: retain a working link to the authorized image or enhance the plain image into an interactive control only when supported.
- The shared JavaScript must initialize safely on pages with no product image/lightbox, without breaking recommendations, AI suggestion buttons or view tracking.

### S-01 — Security and preservation

- Use the existing media route; do not expose filesystem paths or bypass product/media access rules.
- Escape product titles in HTML and use safe text/attribute assignment in JavaScript. Never interpret a title as executable HTML.
- Keep JavaScript in the existing external script, with no inline event-handler attributes or new third-party dependencies.
- Lightbox interactions themselves cause no database writes or new analytics requests. Existing page-view behaviour is unchanged.
- Do not alter existing listings, photos, user data, forms or specifications.

## 4. Acceptance criteria

| ID | Observable result |
| --- | --- |
| AC-01 | Hover produces the small contained zoom; pointer exit restores it without layout movement. |
| AC-02 | Clicking/tapping a valid main image opens one full-screen overlay with the correct image. |
| AC-03 | Close button, Escape and outside click each close it; clicking the image does not. |
| AC-04 | Keyboard activation, initial focus, focus containment and focus restoration work. |
| AC-05 | Background scroll is locked only while open; closing preserves the prior scroll position. |
| AC-06 | Portrait/landscape images and small viewports retain aspect ratio and visible close controls. |
| AC-07 | Reduced-motion settings disable animated zoom without disabling image access. |
| AC-08 | Missing images, failed requests, disabled JavaScript and unsupported dialog capability remain usable. |
| AC-09 | Repeated opening/closing and pages without a lightbox produce no new JavaScript errors. |
| AC-10 | Titles containing quotes or HTML-like text remain plain text; existing media authorization is preserved. |
| AC-11 | Existing listing actions, catalogue navigation and shared-script features continue to work; original data is unchanged. |

## 5. Verification requirements

After approval, create a separate implementation and test plan, then define and validate tests before implementing the feature. Use pytest with isolated fixtures for template rendering, image/placeholder branches, escaping and permission regressions. A pytest HTML assertion alone cannot prove that JavaScript or CSS behaves correctly: verify actual opening, closing, focus, scrolling, hover and responsive behaviour in a browser, with automated browser checks where the available environment supports them. Record what was tested and any limitations honestly; do not install new browser-test dependencies without explaining the need.

Preserve evidence of the initial expected failures and passing results after implementation. Include the existing regression suite in the final feature check, plus screenshots of the completed interaction. Tests must not modify the user's real database or uploads.

## 6. Beginner explanation and learning exercise

HTML describes the image control and dialog. CSS controls their appearance, including scaling an image with `transform` without moving surrounding content. JavaScript listens for actions such as clicks and opens or closes the dialog. The server still supplies the same picture; only the browser's presentation changes.

A modal is like temporarily placing a magnifying window above the page. Focus management makes sure keyboard users enter that window and can return to where they started. Reduced-motion support respects people who prefer less animation.

After implementation, try opening a laptop picture, closing it three different ways, and repeating the process with only the keyboard. Explain why a missing picture should not have an enlarge button and why a larger display does not necessarily mean a higher-resolution photo.

## 7. Approval gate

The user replied **“I approve MM-017”** on 2026-10-29. This approves the behaviour defined above. The next stage is PLAN-017, followed by tests and implementation under the existing SDD workflow. The original specification's requirements are unchanged by this approval record.
