# MM-020 Green verification — 2026-11-02

MM-020 and PLAN-020 were approved before test authoring. The 24-test collection
and 22-failure Red checkpoint are recorded in `tests/020-red-verification.md`.

## Focused automated result

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_live_search.py -q --basetemp=.pytest-tmp\mm020-green
# 24 passed in 28.15s
```

The focused suite covers the JSON endpoint, shared full/AJAX query parity,
literal/Unicode/length cases, validation, canonical queries, active-only privacy,
escaping, empty results, pagination links, viewer-specific cart controls,
read-only behavior, safe database failure, fallback hooks, JavaScript contract,
spinner CSS and existing seller-pagination behavior.

## Complete regression result

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm020-regression
# 322 passed in 336.20s (0:05:36)
```

This includes all MM-001 through MM-019 tests. No database migration or local
data rewrite was required by MM-020.

## Browser acceptance result

Browser mutations used an isolated loopback server on port 5020 with a temporary
SQLite database and temporary uploads. The fixture was stopped afterward. The
real local database received only a final read-only Explore request.

| Check | Result |
| --- | --- |
| Initial/fallback state | PASS — 25 server-rendered products, 20 first-page cards, spinner hidden, busy false, normal pagination and anonymous sign-in controls. |
| 300 ms debounce | PASS — at 180 ms the old 25-card state remained and no loading state appeared. |
| Visible loading | PASS — after the debounce, old cards remained while spinner, `Searching…` and busy true appeared. |
| Successful update | PASS — slow query finished with one correct card, canonical `?q=slow`, busy false, spinner hidden and `1 product found`. |
| Focus/caret | PASS — Search retained focus with caret at position 4 after the four-character query. |
| Stale/race protection | PASS — delayed `slow` followed by `camera` remained on the camera result after the older request could finish. |
| Failure recovery | PASS — controlled HTTP and malformed-JSON failures preserved the camera card and URL, showed the fallback status, then recovered to laptop. |
| Filter retention | PASS — category Electronics and Highest price were not automatic by themselves but remained in the next live request; results were correctly ordered. |
| Empty result | PASS — zero cards, `0 products`, No products found panel, empty pagination and retained Search focus. |
| Page reset | PASS — typing from ordinary page 2 updated to canonical page 1, 20 visible cards and Page 1 of 2 pagination. |
| Ordinary form fallback | PASS — Enter caused a normal full-page GET with complete results and an empty live status. |
| History | PASS — one Back action after multiple live queries returned to the preceding seller page, not one step per typed letter. |
| Viewer controls | PASS — anonymous sign-in links, buyer CSRF Add form and owner Your listing state all survived live replacement. |
| No JavaScript | PASS — controlled response had zero scripts and still showed the camera result, GET form and product count. |
| Narrow viewport | PASS — actual 320 CSS-pixel viewport had `scrollWidth 305`, no horizontal overflow, retained focus and wrapped the long title. |
| MM-017/MM-018 smoke | PASS — image lightbox opened with Close image focused and seller link opened the correct 20-card profile. |
| Browser console | PASS — no warnings or errors. |
| Real local startup | PASS — restarted server returned Explore with 19 products, 19 cards, hidden spinner, busy false and `/products/search` hook. |

Evidence:

- `docs/evidence/020-live-search-desktop.png`
- `docs/evidence/020-live-search-narrow.png`

## Explicit limitations

The available browser controls did not expose actual 200% zoom, media-preference
emulation for reduced motion or a real IME composition keyboard. Those checks are
not claimed as manually passed. Pytest verifies the reduced-motion CSS and
composition-event wiring; the browser checks verify real narrow reflow, keyboard
focus and ordinary typing. A 320-pixel viewport is not described as a substitute
for zoom.

## Cleanup and running state

- The disposable port-5020 server was stopped.
- Temporary viewport overrides were reset.
- The real local server was restarted with the tested implementation and is
  serving `http://127.0.0.1:5000/products`.
- No migration, backup, reseed or real product/cart mutation occurred.
