# PLAN-021 — Mobile bottom navigation

Status: APPROVED — user explicitly approved PLAN-021 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

Approved specification: MM-021, explicitly approved by the user on 2026-11-02.

## 1. Outcome and boundaries

Add a CSS-only responsive navigation mode:

- desktop keeps the complete existing top navigation;
- at `max-width: 42rem`, the desktop controls are hidden while the brand remains;
- a fixed bottom bar presents exactly Home, Explore, Sell, Messages and Profile;
- server-side endpoint grouping supplies one accessible active state; and
- the signed-in Profile page becomes the mobile hub for Dashboard, Saved, Cart
  and CSRF-protected Sign out.

No route meaning, database model, authorization rule, JavaScript behavior or
desktop navigation destination changes. No migration, package, external icon
asset, PWA feature or deployment is planned. The application remains local.

## 2. Planned files and responsibilities

| File | Planned change |
| --- | --- |
| `app/navigation.py` | Define the small allow-listed endpoint-to-mobile-section mapping and pure `mobile_nav_section(endpoint)` helper. |
| `app/__init__.py` | Expose `mobile_nav_section` to Jinja through the existing context processor. |
| `app/templates/base.html` | Name the existing desktop nav, add the five-item mobile nav with inline SVGs, labels and active states, and keep it outside main/footer. |
| `app/auth.py` | Pass one explicit `mobile_account_shortcuts=True` flag only when rendering the authenticated Profile page. |
| `app/templates/form.html` | Conditionally include account shortcuts only for the Profile form. Generic login/register/listing forms remain unchanged. |
| `app/templates/_mobile_account_shortcuts.html` | Render Dashboard, Saved, current-user Cart count and CSRF-protected POST Sign out. |
| `app/static/css/style.css` | Add desktop-hidden defaults, 42rem switch, fixed equal-width bar, safe-area/content clearance, active/focus/touch rules, shortcut layout and print override. |
| `tests/test_mobile_navigation.py` | Define server HTML, endpoint mapping, anonymous/authenticated links, shortcuts, cart isolation, CSRF, no-mutation and static CSS contracts before implementation. |
| `tests/021-browser-checklist.md` | Define desktop/mobile breakpoint, fixed-position, overflow, touch, focus, deep-link, shortcut and regression browser cases before implementation. |
| `tests/021-red-verification.md` | Record collection plus expected missing-feature failures. |
| `tests/021-green-verification.md` | Record focused/full/browser results and honest tooling limitations. |
| `tests/preview_mobile_navigation.py` | Optional loopback-only fixture with temporary users, cart rows, messages and long content for safe real-browser checks. |
| `docs/021-mobile-navigation-guide.md` | Explain media queries, responsive duplication, fixed positioning, safe areas, active state and accessible icons for a high-school student. |
| `docs/evidence/021-*` | Store verified desktop and mobile screenshots. |

`app/static/js/market.js` does not change. Navigation must work with that script
removed.

## 3. Endpoint-group helper

Create `app/navigation.py` so active-state logic is not duplicated across Jinja
conditions. The module contains immutable endpoint groups equivalent to:

```text
home
  main.home

explore
  market.browse
  market.detail
  market.seller_profile

sell
  market.create_listing
  market.edit_listing
  market.preview
  market.own_listings

messages
  engagement.inbox
  engagement.thread

profile
  auth.profile
  engagement.dashboard
  engagement.saved
  cart.review
```

`mobile_nav_section(endpoint)` returns exactly one of `home`, `explore`, `sell`,
`messages`, `profile`, or `None`. It performs an exact string lookup; it does not
use URL text, query parameters, referrers or user input.

POST-only endpoints such as status changes, message sends, cart mutations and
logout are not rendered pages and receive no active group. Login, registration,
errors, health, media, AI JSON and operations pages also return `None`.

Expose the function in `page_helpers()` next to the existing categories,
conditions, image, page URL and cart count helpers. The current cart-count cache
and user scoping remain unchanged.

## 4. Base template structure

### 4.1 Desktop navigation

Add `class="desktop-navigation"` to the existing
`<nav aria-label="Main navigation">`. Do not alter its links, Cart count, logout
form, authentication condition or order.

### 4.2 Mobile navigation

Insert one sibling navigation after the footer and before the existing script:

```text
nav.mobile-navigation[aria-label="Mobile navigation"]
  a.mobile-navigation-item → Home
  a.mobile-navigation-item → Explore
  a.mobile-navigation-item → Sell
  a.mobile-navigation-item → Messages
  a.mobile-navigation-item → Profile
```

Every item contains:

- one inline SVG with `aria-hidden="true"`, `focusable="false"` and a stable
  `viewBox`;
- one visible `.mobile-navigation-label`; and
- `aria-current="page"` only when the endpoint helper returns its section.

Use static project-owned paths for a house, compass/search, plus/add, chat bubble
and person. SVGs use `currentColor`; there is no `<title>` because the adjacent
visible label supplies the accessible name.

Links always use these `url_for` calls:

```text
main.home
market.browse
market.create_listing
engagement.inbox
auth.profile
```

Anonymous users see the same five links. Flask-Login handles the three protected
destinations and safe `next` values. Do not create special client-side redirects.

## 5. Mobile account hub integration

### 5.1 Route flag

In `auth.profile()`, add `mobile_account_shortcuts=True` only to the existing
`render_template("form.html", ...)` call for both GET and invalid POST rendering.
The successful POST redirect returns to Profile and naturally receives the same
section on its next GET.

No other route passes the flag.

### 5.2 Conditional partial

In `form.html`, immediately after the Profile H1 and before its edit form:

```jinja2
{% if mobile_account_shortcuts|default(false) %}
  {% include '_mobile_account_shortcuts.html' %}
{% endif %}
```

The partial contains a section labelled by an `Account shortcuts` H2, then:

- Dashboard link;
- Saved products link;
- Cart link whose visible text includes `cart_count`; and
- POST logout form using `csrf_token()`.

Do not put user IDs, emails or redirect targets in these controls. Sign out must
remain a form/button, never a GET link.

The shortcut section is hidden by default and displayed only inside the mobile
media query. Although its HTML is present for a signed-in Profile page at desktop
widths, `display: none` removes the duplicate controls from the visual and
accessibility layout there.

## 6. CSS design

### 6.1 Desktop defaults

Add defaults before the mobile media query:

```text
.mobile-navigation { display: none; }
.mobile-account-shortcuts { display: none; }
```

The existing desktop header/nav styles continue to apply. Scope new selectors so
the global `nav a` rule does not add unwanted right margins to bottom items.

### 6.2 Mobile switch at 42rem

Replace/expand the existing `@media (max-width: 42rem)` block so it keeps the
current product/cart stacking and adds:

- `.desktop-navigation { display: none; }`;
- compact brand-only header alignment/minimum height;
- `body { padding-bottom: calc(<bar height> + env(safe-area-inset-bottom)); }`;
- `.mobile-navigation { display: grid; grid-template-columns: repeat(5,minmax(0,1fr)); position: fixed; inset-inline: 0; bottom: 0; ... }`;
- bottom padding including `env(safe-area-inset-bottom)`;
- `.mobile-navigation-item` with no inherited margin, centered icon/label, minimum
  44-pixel height, `min-width: 0`, wrapping and visible focus;
- current-item border/background/font-weight treatment; and
- `.mobile-account-shortcuts` display/layout rules.

Use an explicit background, top border and `z-index` above cards/footer. Dialogs
opened with `showModal()` remain in the browser top layer and therefore stay
above it.

The bar should normally be approximately 4–4.75rem plus safe area. The body
clearance must be at least the same amount so the footer can scroll fully above
the bar.

### 6.3 Narrow and print rules

At the existing 30rem breakpoint, allow long shortcut text and labels to wrap;
do not hide labels. Five grid columns use `minmax(0,1fr)` and each child uses
`min-width:0` to prevent page overflow at 320 pixels.

Add:

```css
@media print {
  .mobile-navigation,
  .mobile-account-shortcuts { display: none !important; }
  body { padding-bottom: 0 !important; }
}
```

No animation or JavaScript class toggle is planned.

## 7. Authentication and safety behavior

- Home and Explore are public GET links.
- Anonymous Sell/Messages/Profile requests go through the existing Flask-Login
  redirect; tests verify a local `next` value and no database mutation.
- Signed-in links use the current session; there is no account selector.
- The Profile Cart count uses the existing request-cached, user-scoped
  `cart_count` value.
- Logout uses POST plus a current CSRF token, clears the session under existing
  code and redirects home.
- The navigation cannot read or alter query-provided roles, counts, endpoints or
  active state.
- SVG path markup is constant source code and never includes database content.

## 8. Test-first execution sequence

1. Obtain explicit PLAN-021 approval.
2. Write `tests/test_mobile_navigation.py` and
   `tests/021-browser-checklist.md` without changing application/template/CSS
   implementation.
3. Run collection. Tests must collect even though `app.navigation` may not exist;
   import the helper inside the relevant test or assert its absence as a normal
   Red failure rather than causing collection failure.
4. Run focused tests against unchanged code and record Red evidence. Expected
   failures are missing mobile nav markup, helper, account shortcuts and CSS.
5. Implement the helper/context integration, template markup/partial and CSS in
   that order.
6. Run focused tests until green without weakening the approved contracts.
7. Run the complete suite, especially MM-019 Cart and MM-020 live-search/browser
   markup tests.
8. Run browser acceptance against a temporary loopback fixture. Use the real
   local database only for a read-only final layout/startup check.
9. Save evidence and guide, stop the disposable server, reset viewport/media
   overrides, restart the real local server and leave the verified page open.

No migration, database backup or reseed is needed.

Planned commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_mobile_navigation.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_mobile_navigation.py -q --basetemp=.pytest-tmp\mm021-red
.\.venv\Scripts\python.exe -m pytest tests\test_mobile_navigation.py -q --basetemp=.pytest-tmp\mm021-green
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm021-regression
```

## 9. Pytest coverage matrix

| Group | Required cases | Specification coverage |
| --- | --- | --- |
| Base structure | Distinct Main/Mobile nav labels; brand outside hidden nav; bottom nav exactly five links in approved order | AC-021-01–03, 10 |
| Link contracts | Exact `url_for` paths; ordinary anchors; no external URL, user ID, script handler or mutation form | AC-021-03–05, 12 |
| SVG/labels | One SVG and visible label per item; `aria-hidden`, `focusable=false`, `viewBox`, no external icon/image dependency | AC-021-03, 10, 12 |
| Active helper | Every allow-listed endpoint maps to the expected section; login/error/JSON/POST-like endpoints map to none | AC-021-06 |
| Active markup | Representative Home, Explore/detail/seller, Sell/preview, Messages/thread and Profile/dashboard/Saved/Cart pages have exactly one correct `aria-current`; unrelated page has none | AC-021-06 |
| Anonymous behavior | All five present; protected GETs redirect to login with local intended destination; no data rows created | AC-021-04 |
| Signed-in navigation | Five protected/public links return expected success/redirect without weakening owner rules | AC-021-05, 13 |
| Profile hub | Profile alone contains Account shortcuts; Dashboard/Saved/Cart links and visible current cart count; other generic forms lack section | AC-021-07 |
| Cart isolation | Two users with 0/1/many rows see only their own Profile shortcut count | AC-021-07, security |
| Logout | Shortcut is POST form with CSRF; GET rejected; bad/missing token rejected; valid token clears authenticated access | AC-021-07, security |
| No mutation | GET every nav destination as appropriate and compare database snapshots | AC-021-04, 12 |
| Desktop CSS | Mobile nav/shortcuts hidden by default; desktop nav unchanged | AC-021-01 |
| Mobile CSS | Exact 42rem media query; desktop hidden, mobile grid/fixed/insets/z-index/top border, five columns and account section shown | AC-021-02, 08 |
| Safe area/content | Both bar padding and body clearance reference `env(safe-area-inset-bottom)`; bottom controls not obscured contract | AC-021-08 |
| Touch/overflow/focus | Minimum 44px, child `min-width:0`, wrapping, visible focus and current-state non-color treatment | AC-021-09, 10 |
| Theme/print | Existing variables used; print hides bottom/shortcuts and resets bottom clearance | AC-021-11 |
| No JavaScript/dependency | Feature tokens absent from `market.js`; requirements unchanged; server HTML contains complete links | AC-021-12 |
| Regression | Existing desktop Cart count/logout, AJAX search hooks/cards, seller/lightbox/messages and full suite stay green | AC-021-13 |

Avoid brittle SVG path-string assertions. Tests should verify structure,
accessibility attributes and project-owned inline markup, while browser checks
verify actual appearance.

## 10. Browser acceptance plan

Define the checklist before implementation, then use real layout/computed styles:

1. At 1000×800, verify desktop Main navigation visible, mobile nav and mobile
   Account shortcuts hidden, and existing Cart count/logout intact.
2. At 673 CSS pixels, verify desktop mode; at exactly 672 pixels (42rem with the
   normal 16px root), verify the mobile switch; report if browser root sizing
   changes the calculated boundary.
3. At 320×800, verify brand visible, desktop nav `display:none`, fixed bottom nav
   visible with five items in exact order.
4. Measure each item at least 44 pixels high, equal grid widths, full bar aligned
   to viewport bottom, and `scrollWidth <= innerWidth`.
5. Search via MM-020 and scroll to the page end; verify live results, last card,
   pagination/footer and controls can scroll above the fixed bar.
6. Test Home and Explore anonymously; select Sell, Messages and Profile and verify
   safe Sign-in redirect/return destination without side effects.
7. Sign in through the isolated fixture, visit all five destinations and inspect
   one correct active state on representative grouped pages.
8. On Profile, verify Account shortcuts, a two-digit Cart count, Dashboard/Saved/
   Cart links and visible keyboard focus. Use valid logout only at the final
   fixture step and verify the session ends.
9. Use Tab/Shift+Tab through the bottom order and ensure focus is not clipped.
10. Open the product image lightbox and confirm the modal/top layer covers the
    bottom navigation.
11. Use a controlled no-script response and confirm the bar and navigation still
    work.
12. Inspect short landscape height, long labels/content, narrow reflow and
    available 200% zoom/dark-mode checks.
13. Inspect print media only if browser emulation is available; otherwise rely on
    pytest/CSS contract and state the limitation.
14. Inspect console warnings/errors and save desktop/mobile screenshots.

Do not click real logout, cart mutations, message send or listing creation on the
user's local database. Mutating acceptance uses only temporary fixture data.

## 11. Browser fixture plan

Create `tests/preview_mobile_navigation.py` if needed. It will:

- use temporary SQLite/uploads paths under `.pytest-tmp`;
- seed one seller, one buyer, at least 12 buyer cart rows and a conversation;
- seed enough long products for a scrolling/pagination page;
- provide real login through the existing form with fixture-only credentials;
- optionally remove `market.js` for a no-script response; and
- run on a dedicated loopback port with no production-only code changes.

The fixture will not weaken authentication, skip CSRF or modify the real database.

## 12. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Bottom bar covers content | Body bottom clearance equals/exceeds bar plus safe area; browser end-of-page measurement. |
| Hiding header makes Cart/Saved/logout unreachable | Approved Profile-only Account shortcuts with current Cart count and POST logout. |
| Duplicate navs confuse screen readers | CSS `display:none` toggles whole nav structures; distinct accessible labels. |
| Five labels overflow at 320px | Equal `minmax(0,1fr)` grid, zero child minimum, wrapping, compact labels/icons; measured browser check. |
| Active item is wrong on detail pages | Pure exact endpoint mapping plus comprehensive parameterized tests. |
| Anonymous protected links leak or mutate | Direct protected endpoints, existing Flask-Login, safe-local redirect and snapshots. |
| Logout becomes unsafe shortcut | Preserve POST/CSRF form; method/token tests. |
| Icon is read twice | Static SVG `aria-hidden=true`, visible label supplies name. |
| Fixed bar covers lightbox | Native modal remains top-layer; browser smoke test. |
| Global `nav a` styles distort bar | Scoped mobile item overrides for margin, padding and display. |
| Desktop layout regresses | Mobile elements hidden by default; >42rem browser and full regression checks. |
| MM-020 search loses usable viewport | Long-page mobile testing with live results and fixed-bar content clearance. |

## 13. Rollback and recovery

MM-021 stores no data. To roll back:

1. remove the mobile nav from `base.html` and restore the desktop nav without its
   extra class if desired;
2. remove endpoint helper/context exposure;
3. remove the Profile flag/partial include and shortcut partial;
4. remove mobile/print CSS additions while retaining existing responsive rules;
5. run the focused prior navigation/layout tests and full suite.

The desktop header remains the functional fallback throughout, so a CSS issue can
also be temporarily mitigated by disabling only the new mobile media rules.

## 14. Beginner concepts to document

The final guide will explain:

- **responsive design:** one site adapting to different screen sizes;
- **media query:** CSS that activates below 42rem;
- **fixed positioning:** keeping the bar at the viewport bottom;
- **content clearance:** reserving space so fixed UI does not cover content;
- **safe-area inset:** space used by phone home indicators/notches;
- **inline SVG:** scalable icons stored directly in HTML;
- **accessible name:** visible labels making icon meaning clear;
- **active navigation:** server endpoint mapped to `aria-current`; and
- **progressive/no-JavaScript behavior:** ordinary links rendered by Flask.

## 15. Approval gate

This plan commits to these implementation choices:

1. a pure CSS switch at `max-width: 42rem` with no navigation JavaScript;
2. a server-side exact endpoint mapping for active state;
3. five always-rendered primary links for both anonymous and authenticated users;
4. Profile-only mobile Account shortcuts to preserve Dashboard, Saved, Cart and
   secure Sign out; and
5. inline SVG icons with visible labels and no external dependency.

The user explicitly approved this plan on 2026-11-02. The Testing stage may now
begin; pytest contracts and the browser checklist must be written and validated
Red before application implementation.
