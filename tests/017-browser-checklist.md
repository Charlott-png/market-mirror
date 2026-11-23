# MM-017 browser acceptance checklist

Defined before implementation, 2026-10-29. Results belong in 017-green-verification.md.

Use synthetic fixtures on an isolated local server for failure cases and stateful checks. Never change real listings or images to create a test failure.

1. Hover main image: scale approximately 1.05, frame/text unchanged; pointer exit restores original scale.
2. Ordinary click or Tab then Enter opens exactly one viewport-covering dialog with the correct image. Modified clicks preserve ordinary link behaviour.
3. Close button, Escape and empty-area click each close it. Image click and image-to-background drag do not.
4. Focus starts at close button; Tab and Shift+Tab stay inside. Closing returns focus to trigger.
5. Open while scrolled; background cannot scroll; closing restores original styles and scroll position. Repeat at least five times using different close paths.
6. Test landscape and portrait image fixtures at desktop, 320px width and short landscape size; resize while open. Close stays visible and no horizontal overflow.
7. Test actual 200% browser zoom separately from resizing if supported.
8. Test reduced-motion preference: no zoom/transition; lightbox still works.
9. Test genuine touch/emulated touch if supported; do not count mouse clicks as touch-device testing.
10. Missing filename and missing file show only a placeholder. A late failing image request shows readable modal error and usable close control, including cached failure on reopening.
11. JavaScript-disabled and unsupported-dialog fixtures retain working image link and hidden dialog.
12. HTML-like title is literal; focus/close control are legible in light/dark colour schemes.
13. Unrelated pages have no new JavaScript errors; catalogue links, recommendations, view tracking and AI suggestions retain their existing behaviour. Opening/closing adds no writes or tracking requests.
14. Save actual desktop and narrow-screen screenshots. Record unsupported checks as unverified, never as passes.
