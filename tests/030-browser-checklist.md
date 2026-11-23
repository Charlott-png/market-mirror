# MM-030 Browser Verification Checklist

Date: 2026-11-08 (Asia/Shanghai)

Target: actual local Market Mirror server at `http://127.0.0.1:5000`.

## Completed checks

- [x] Desktop Home uses the midnight background, gold brand/actions and a
  large Cinzel hero heading.
- [x] Desktop Explore shows a sticky dark header, raised filter panel, four
  comfortably spaced card columns, product photography and gold price accents.
- [x] Scrolling Explore keeps the header visible and reveals the deep-black
  gold-text footer.
- [x] Product detail uses a premium two-column panel with gold category, price
  and action treatment.
- [x] Product image click opens the near-black full-screen lightbox with a gold
  close button; closing returns focus to the image trigger.
- [x] You might also like reuses the shared glass-card treatment.
- [x] The AI Shop Assistant launcher is gold and its expanded panel uses a
  midnight surface, gold edge, readable fallback/sign-in action and disclosure.
- [x] The default narrow view hides desktop links and shows only the five-item
  fixed bottom navigation.
- [x] At an explicit 320×700 viewport, Explore has one card column, one filter
  column and no horizontal page overflow.
- [x] Measured 320-pixel state: viewport width 320, document scroll width 305,
  desktop navigation `none`, mobile navigation `grid`, header `sticky`.
- [x] Browser console error count was zero after Home, Explore, product,
  lightbox and Assistant checks.
- [x] The temporary explicit browser viewport was reset after verification.

## Browser-found correction

The first narrow screenshot displayed both desktop and mobile navigation. The
new later `.desktop-navigation { display: flex; }` rule had overridden the old
mobile rule through CSS source order. A final scoped
`@media (max-width: 42rem)` rule now restores `display: none`. The browser was
reloaded and visibly confirmed the correction; the final mobile/focused test
set then passed 46 tests.

## Honest limits

This session did not emulate a real screen reader, Windows forced-colors mode,
print output on paper, offline Google Fonts blocking, or a browser-level 200%
zoom control. Static contracts cover those fallbacks, but they remain useful
student-led presentation checks rather than falsely claimed browser evidence.
