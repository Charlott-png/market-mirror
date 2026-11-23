# MM-021 Green verification — 2026-11-02

MM-021 and PLAN-021 were approved before test authoring. The 32-test collection
and expected 27-failure Red checkpoint are recorded in
`tests/021-red-verification.md`.

## Focused automated result

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_mobile_navigation.py -q --basetemp=.pytest-tmp\mm021-final
# 32 passed in 20.48s
```

The focused suite covers exact endpoint grouping, five-link order and paths,
inline accessible icons, active states, anonymous protected redirects, signed-in
destinations, Profile-only Account shortcuts, user-scoped Cart count, secure
POST/CSRF logout, preserved desktop links, the 42rem CSS contract, safe-area and
content clearance, touch/overflow rules, print behavior, and no JavaScript
dependency.

## Complete regression result

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm021-regression
# 354 passed in 364.25s (0:06:04)
```

This includes every existing MM-001 through MM-020 test plus the first green
MM-021 run. The browser check then found one cosmetic narrow-screen word wrap;
the 30rem rule was changed from a two-column to a one-column Profile shortcut
grid. The final 32-test focused run above passed after that CSS-only correction.

No database migration, package, real-data rewrite, or JavaScript change was
required.

## Browser acceptance result

Mutating browser checks used an isolated loopback fixture on port 5021 with a
temporary SQLite database, 25 products, a fixture conversation, and a fixture
buyer with 12 Cart rows. It was stopped afterward. The real local database
received only a final read-only Explore request.

| Check | Result |
| --- | --- |
| Desktop 1000px | PASS — Main navigation displayed, mobile navigation hidden, brand visible, Explore was the server-selected current section. |
| Exact breakpoint | PASS — at 673px desktop remained visible/mobile hidden; at exactly 672px desktop was hidden/mobile grid displayed. |
| 320px structure | PASS — Home, Explore, Sell, Messages, Profile appeared in the approved order; brand remained visible. |
| Tap targets/grid | PASS — all five items were 48px high and equal 60px columns, above the required 44px minimum. |
| Overflow | PASS — viewport width 320, document scroll width 305, so no horizontal page overflow. |
| Fixed position/clearance | PASS — bar bottom gap was 0; body reserved 76px; at document end the footer bottom was 724px and bar top 747px. |
| Active state | PASS — Explore/Profile had `aria-current`, bold weight, solid top border and background treatment rather than color alone. |
| Signed-in Profile | PASS — visible Account shortcuts, Dashboard, Saved products, Cart 12, and Sign out. |
| Narrow Profile correction | PASS — browser review found `Dashboard` splitting awkwardly; at 320px the final layout uses one 205px-wide column with four 48px controls. |
| Logout safety | PASS — browser DOM showed POST method and a CSRF token; pytest verified missing/invalid tokens fail and valid logout clears the session. |
| No JavaScript | PASS — controlled page contained zero `market.js` scripts but retained five links, active Profile state, visible shortcuts and no overflow. |
| Lightbox layering | PASS — while the fixed bar remained displayed, the open native dialog was the element at the bottom test point and covered it. |
| Console | PASS — no browser errors or warnings. |
| Real local startup | PASS — restarted server returned HTTP 200 at `http://127.0.0.1:5000/products`. |

## Explicit limitations

The available browser controls did not expose a true screen-reader session,
200% browser zoom, forced dark-mode preference, phone safe-area hardware, or a
print preview capture. Those are not claimed as manually passed. Pytest verifies
the safe-area, dark-theme-variable use and print CSS contracts; the browser run
verified actual desktop, breakpoint, 320px, long-page, signed-in, no-script and
modal layouts.

The browser screenshots were inspected during the acceptance run but were not
exported as repository files by the available local browser interface. Existing
evidence files were not altered.

## Cleanup and running state

- The disposable port-5021 fixture server was stopped.
- Temporary viewport overrides were reset and the fixture tab was closed.
- The real local server was restarted with the final implementation.
- `http://127.0.0.1:5000/products` is open as the user-facing result.
- No real logout, cart mutation, message, listing creation, migration, backup or
  reseed was performed.
