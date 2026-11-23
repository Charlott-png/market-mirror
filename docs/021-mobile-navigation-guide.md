# MM-021 — Mobile navigation learning guide

## What we built

Market Mirror now uses two navigation layouts. A wide screen keeps the complete
top menu. A screen 42rem wide or smaller keeps the Market Mirror brand at the top
and shows five important actions in a fixed bar at the bottom: Home, Explore,
Sell, Messages, and Profile.

This is similar to many phone apps. A thumb can reach the main destinations
without opening a menu, but a laptop still gets the more detailed navigation.

## How the pieces work

`app/navigation.py` is a tiny lookup table. Flask names every page with an
endpoint such as `market.browse`. The lookup converts that name to one section,
such as `explore`. The template uses the result to add `aria-current="page"` to
exactly one link. This is safer than guessing from URL text because the possible
values are written down in one allow-list.

`base.html` contains both navigation structures. CSS hides the mobile one on a
wide screen. At `max-width: 42rem`, a media query hides the desktop controls and
displays the mobile bar. No JavaScript is required, so ordinary links still work
if a script fails or is disabled.

The Profile page includes a mobile-only Account shortcuts panel. It preserves
Dashboard, Saved products, Cart, and Sign out after the larger desktop menu is
hidden. Sign out is still a POST form with a CSRF token; it was not changed into
an unsafe GET link.

## Important concepts

- **Responsive design** means the same HTML adapts to different screen sizes.
- A **media query** activates CSS only when its condition is true.
- **Fixed positioning** keeps the bar attached to the browser viewport while the
  page scrolls.
- **Bottom clearance** is extra body padding. Without it, the fixed bar would
  cover the footer or the last button.
- A **safe-area inset** reserves space used by phone home indicators.
- **Inline SVG** creates sharp icons at any size without another package or web
  request. The visible word beside each icon gives it an accessible name.
- `aria-current="page"` tells assistive technology which navigation section is
  active. The design also uses weight, border, and background—not color alone.
- A **44-pixel target** is easier to tap accurately than a tiny text link.

## Files to explain in a demonstration

1. `app/navigation.py` — exact endpoint grouping.
2. `app/templates/base.html` — desktop and five-item mobile navigation.
3. `app/templates/_mobile_account_shortcuts.html` — mobile account hub.
4. `app/static/css/style.css` — breakpoint, fixed grid, safe area, focus, and
   print rules.
5. `tests/test_mobile_navigation.py` — automated behavior and safety contracts.

## Simple demonstration

1. Open Explore on a wide window and point out the full top navigation.
2. Narrow the window below 42rem and show the brand plus bottom bar.
3. Visit Explore, Sell, and Messages and explain the active marker.
4. Sign in and open Profile to show the Account shortcuts and Cart count.
5. Scroll to the footer and show that it is not hidden behind the fixed bar.
6. Explain that Flask controls meaning and CSS controls layout.
