# MM-021 — Mobile bottom navigation

Status: APPROVED — user explicitly approved MM-021 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

## 1. Purpose

Market Mirror's desktop header currently places every destination in one top
navigation row. On narrow screens that row wraps across several lines and uses a
large part of the screen before the page content begins.

MM-021 introduces a mobile navigation pattern:

- hide the desktop top-navigation controls at mobile widths;
- keep the Market Mirror brand visible in the header;
- show a fixed bottom navigation bar; and
- provide five primary destinations with icons and text labels: **Home**,
  **Explore**, **Sell**, **Messages**, and **Profile**.

The desktop header remains unchanged. The mobile bar is navigation only; it does
not change accounts, products, messages, carts or database data.

MM-021 extends MM-001 through MM-020 without removing search, product images,
seller profiles, lightbox behavior, Saved products, messages, cart, live search,
AI features or existing tests.

## 2. Responsive breakpoint

- Mobile behavior applies at `max-width: 42rem`, matching the project's existing
  primary responsive breakpoint.
- At widths greater than `42rem`, the existing desktop navigation is visible and
  the bottom navigation is hidden.
- At `42rem` and below, the desktop navigation is `display: none` and therefore
  absent from both the visual layout and accessibility tree. The mobile bottom
  navigation becomes visible.
- The brand link remains visible at every width.
- The default/no-styles fallback remains the existing top navigation. Mobile
  navigation must not depend on JavaScript to appear or work.

## 3. Five primary mobile destinations

The bottom bar contains exactly these five items in this order:

| Item | Destination | Icon meaning |
| --- | --- | --- |
| Home | `/` | House |
| Explore | `/products` | Compass or magnifying glass |
| Sell | `/listings/new` | Plus/add listing |
| Messages | `/messages` | Conversation bubble |
| Profile | `/account/profile` | Person/account |

Each item is an ordinary server-generated link. Icons use small inline SVGs
stored in the template, so MM-021 adds no external icon font, image download,
package, CDN request or JavaScript library.

Icons are decorative and use `aria-hidden="true"` because the visible text label
already communicates the link purpose. The text labels remain visible; meaning
must never depend on recognizing an icon.

## 4. Authentication behavior

### Signed-in visitors

All five destinations open normally. Sell, Messages and Profile retain their
existing authentication and authorization rules. The navigation does not accept
or transmit a user ID.

### Anonymous visitors

- Home and Explore open normally.
- Sell, Messages and Profile link to their real protected destinations.
- The existing `login_required` behavior redirects the visitor to Sign in with a
  safe local `next` destination.
- After successful login, the visitor returns to the intended local page under
  the existing authentication rules.
- The mobile bar must not reveal message counts, cart counts, profile details or
  other account information to an anonymous visitor.

The bar does not automatically create an account, product, conversation or cart.

## 5. Preserving secondary account destinations

The current desktop navigation also exposes Dashboard, Saved, Cart and Sign out.
They are not among the five primary items requested for the mobile bar, but
earlier approved features must remain discoverable on mobile.

For signed-in visitors, the Profile page will include a **mobile-only Account
shortcuts** section containing:

- Dashboard;
- Saved products;
- Cart with the current user's safe cart-row count; and
- a CSRF-protected POST **Sign out** button.

The section is hidden at desktop widths because those controls are already in the
desktop header. It appears at mobile widths before or after the profile form in a
logical reading order.

This makes Profile the mobile account hub while keeping the bottom bar to exactly
the five requested primary destinations. The shortcut section must not appear on
registration, login, listing or other generic forms, and it must never appear for
anonymous visitors.

## 6. Active destination state

The current primary destination receives `aria-current="page"` and a clear visual
active style that does not depend only on color.

Use these logical groups:

- **Home:** the home page;
- **Explore:** catalogue, product detail and public seller profile;
- **Sell:** new listing, edit listing, listing preview and the owner's listing
  management pages;
- **Messages:** inbox and individual conversation pages; and
- **Profile:** profile, dashboard, Saved and Cart/account-supporting pages.

If a page does not belong clearly to one group, no item receives
`aria-current`. Never mark more than one bottom item current.

An anonymous protected-route redirect displays Sign in; while on Sign in, no
bottom destination has to be marked current.

## 7. Fixed-position layout

- The bottom bar uses `position: fixed`, `left: 0`, `right: 0`, and `bottom: 0`.
- It spans the viewport width and uses a sufficiently high stacking level to stay
  above ordinary page cards and footers, but it must not appear over a modal
  dialog/top-layer lightbox.
- The five links use an equal-width grid.
- The bar has a visible top border and the existing surface/background theme
  colors so it remains distinct in light and dark modes.
- Add bottom space to the document at mobile widths so the bar never covers the
  final form control, pagination link, cart button, footer or validation message.
- Include `env(safe-area-inset-bottom)` in the bar padding and page clearance for
  phones with a home-indicator/notch safe area.
- No page-level horizontal overflow is allowed at 320 CSS pixels.
- At extremely small effective widths, labels may wrap within their equal grid
  cell, but links must remain reachable and the page must not be widened.

The header is no longer sticky/fixed on mobile. Only the bottom bar is fixed.

## 8. Touch, keyboard and accessibility requirements

- The bottom element is `<nav aria-label="Mobile navigation">`.
- Each item has an accessible name matching its visible label.
- Each link offers at least a 44 CSS-pixel touch height.
- Icon and label are vertically arranged and centered.
- Keyboard focus uses the project's existing visible focus outline and is not
  clipped by the fixed bar.
- Keyboard order follows Home, Explore, Sell, Messages, Profile.
- Active state uses `aria-current="page"`, a visible background/border/weight
  difference, and not color alone.
- Screen readers encounter only one primary navigation at a time at normal media
  settings: desktop navigation above the breakpoint or mobile navigation below
  it.
- The Account shortcuts section has its own accessible label and a real POST form
  for Sign out.
- The fixed bar does not cover focused elements when users tab to the end of a
  page. Page bottom clearance must include the safe-area value.
- At 200% zoom, every destination remains operable when browser controls permit
  testing; unavailable zoom tooling must be reported honestly.

## 9. Visual design

- Reuse Market Mirror's `--surface`, `--text`, `--muted`, `--brand`,
  `--brand-dark`, and `--line` variables.
- Keep icons consistent at approximately 1.25–1.5rem.
- Keep labels short and readable, approximately 0.7–0.8rem, without hiding them.
- Do not use emoji as navigation icons because their appearance differs between
  devices and they may be announced inconsistently.
- Do not use hover as the only interaction signal.
- Respect the existing dark color scheme.
- The bar has no animation requirement and therefore introduces no motion issue.

## 10. Security and privacy

- Navigation uses only allow-listed Flask `url_for` destinations.
- Do not accept destinations, usernames, counts or active states from query/form
  parameters.
- Protected destinations continue to rely on server authentication.
- Sign out remains POST-only and CSRF-protected; never turn it into a GET link for
  mobile convenience.
- The Cart shortcut count is derived from the current authenticated account and
  must not leak across users.
- Inline SVGs contain static project-owned path data only; no user content is
  inserted into SVG/HTML attributes.
- The bottom navigation performs no fetch, tracking, analytics or database write.

## 11. Print and non-screen behavior

- Hide the fixed mobile navigation in print styles so it does not appear on a
  printed page.
- Do not add bottom clearance in print.
- The ordinary document content and brand remain printable.

## 12. Acceptance criteria

| ID | Expected outcome |
| --- | --- |
| AC-021-01 | Above 42rem, the existing desktop navigation is visible and the mobile bottom navigation is hidden. |
| AC-021-02 | At 42rem and below, desktop navigation controls are hidden, the brand remains visible, and the fixed bottom navigation appears. |
| AC-021-03 | The bar contains exactly Home, Explore, Sell, Messages and Profile in that order, with visible labels and meaningful decorative SVG icons. |
| AC-021-04 | Each destination uses the correct Flask URL; anonymous protected destinations safely redirect through Sign in without mutation or an external redirect. |
| AC-021-05 | Signed-in users can navigate to all five destinations; server authentication and ownership rules remain unchanged. |
| AC-021-06 | Exactly one appropriate item receives `aria-current=page`, including grouped detail/conversation/account pages; unrelated pages may have none. |
| AC-021-07 | Signed-in Profile contains mobile Account shortcuts for Dashboard, Saved, Cart count and CSRF-protected POST Sign out; other forms do not. |
| AC-021-08 | The fixed bar and safe-area padding never cover final page content, form controls, pagination, notices or footer actions. |
| AC-021-09 | The layout has no page-level horizontal overflow at 320 CSS pixels, labels remain readable and links have at least 44-pixel touch height. |
| AC-021-10 | Keyboard focus is visible and ordered; icons are hidden from assistive technology; both navs have distinct accessible labels. |
| AC-021-11 | Light/dark theme colors remain legible; print hides the mobile bar and removes its extra page clearance. |
| AC-021-12 | Navigation works with JavaScript disabled and adds no external dependency or database migration. |
| AC-021-13 | Cart, Saved, Dashboard, Sign out, search/AJAX, cards, messages, seller pages, lightbox and all earlier features continue to pass their tests. |

## 13. Edge cases for the later test plan

The Planning and Testing stages must cover at least:

- widths immediately above, exactly at and immediately below 42rem;
- 320 CSS-pixel portrait and a short landscape viewport;
- anonymous, newly signed-in and established signed-in sessions;
- every primary endpoint group and pages with no active group;
- zero, one and two-digit cart shortcut counts without cross-user leakage;
- safe login return for Sell, Messages and Profile;
- logout method, CSRF and session removal;
- long page content and very short pages;
- form errors and notices near the bottom of the viewport;
- pagination, cart Checkout and message-send controls near page end;
- on-screen keyboard/focus behavior when available;
- browser Back/Forward and direct deep links;
- light/dark color schemes when emulation is available;
- 200% zoom when supported;
- safe-area CSS contract;
- JavaScript disabled;
- print stylesheet contract; and
- existing lightbox/dialog stacking above the navigation.

## 14. Out of scope

MM-021 does not add:

- a hamburger drawer;
- a JavaScript menu or animated transition;
- drag/swipe navigation;
- notification/unread badges;
- a Cart item as a sixth primary bottom destination;
- automatic route prefetching;
- native mobile-app installation/PWA behavior;
- custom icon packages;
- a database migration; or
- changes to the meaning or permissions of any destination.

## 15. Beginner explanation

A **media query** is a CSS rule that applies only when the screen matches a
condition. Market Mirror will use one layout on wide screens and another on narrow
screens:

```css
/* Wide screens: normal top navigation */

@media (max-width: 42rem) {
  /* Hide the desktop links and reveal the fixed bottom navigation. */
}
```

The HTML contains both navigation structures, but CSS makes only the appropriate
one available for the current screen. The bottom bar is **fixed**, so it stays at
the bottom while the page scrolls. Because fixed content can cover the page, the
mobile layout must also reserve matching bottom space.

Every icon also has a text label. This helps students, screen-reader users and
anyone who does not recognize a particular symbol.

## 16. Subsequent SDD stages

After this specification is approved:

1. Write PLAN-021 with exact template structure, endpoint-group mapping, Account
   shortcuts integration, CSS selectors, test matrix, browser checks and rollback.
2. Wait for explicit PLAN-021 approval.
3. Write pytest coverage and the browser checklist before implementation.
4. Run and record the expected Red checkpoint.
5. Implement only the approved behavior.
6. Run focused tests, the complete regression suite and real responsive browser
   acceptance, then write a beginner guide and evidence.

No HTML, CSS, test or application change is authorized by this specification
alone.

## 17. Approval gate

Please review especially these decisions:

1. mobile begins at `42rem` and the desktop navigation is fully hidden there;
2. the bottom bar has exactly the requested five destinations and visible labels;
3. anonymous visitors may see all five, with protected destinations safely
   redirecting to Sign in; and
4. Profile becomes the mobile account hub, with mobile-only Dashboard, Saved,
   Cart and Sign out shortcuts so earlier features remain discoverable.

The user replied **“I approve MM-021.”** on 2026-11-02. The next stage is
PLAN-021; tests and implementation will still wait for their proper SDD gates.
