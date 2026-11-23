# PLAN-019 — Shopping cart and safe demo checkout

Status: APPROVED — user explicitly approved PLAN-019 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

Approved specification: MM-019, explicitly approved by the user on 2026-11-02.

## 1. Outcome and boundaries

Implement a persistent, signed-in-user shopping cart with:

- Add-to-Cart controls on public server-rendered product cards;
- an authenticated navigation link with a live cart-row count;
- a cart review page with current product information and exact subtotal;
- user-scoped, CSRF-protected removal; and
- a POST Checkout demonstration that revalidates the full cart but creates no payment, order, reservation, message, analytics event or listing-status change.

The cart remains separate from Saved products. No JavaScript is required. Existing MM-001 through MM-018 files and behaviours remain unless this approved plan names a small integration edit.

The plan chooses the presentation option left open in MM-019: the navigation Cart link appears only to authenticated users, alongside Dashboard, Saved and Messages. Anonymous public cards show a **Sign in to add to cart** link. Signed-in sellers do not receive an Add control for their own cards.

## 2. Planned files and responsibilities

| File | Planned change |
| --- | --- |
| `app/models/activity.py` | Add the small `CartItem` join model with composite key, UTC timestamp and product relationship. |
| `app/models/__init__.py` | Export `CartItem` so migrations, tests and routes discover it consistently. |
| `migrations/versions/<new_revision>_mm019_cart_items.py` | Create/drop only the `cart_items` table and its indexes. The actual revision ID will be generated/verified locally rather than invented in this plan. |
| `app/cart.py` | Add the cart blueprint, eligibility helpers, full-cart loader, Add, Remove, review and demo-checkout routes. |
| `app/__init__.py` | Register the cart blueprint and expose one cached, current-user-only `cart_count` template value. |
| `app/templates/macros.html` | Extend the shared public card macro with Add/Sign-in/Your-listing controls while leaving private owner cards unchanged. |
| `app/templates/base.html` | Add the authenticated cart navigation link, inline decorative cart SVG and accessible count text. |
| `app/templates/cart.html` | Render eligible items, generic unavailable rows, count, subtotal, removal forms, warnings and Checkout form. |
| `app/static/css/style.css` | Add scoped cart/nav-count/summary rules and narrow-screen wrapping; reuse existing button/focus variables. |
| `tests/test_cart.py` | Focused route, model, card, count, privacy, CSRF, concurrency, money and checkout tests. |
| `tests/test_cart_migration.py` or existing migration tests | Fresh-database upgrade/downgrade and constraint/index checks. The test-first stage will choose the least duplicative location. |
| `tests/019-browser-checklist.md` | Browser cases defined before implementation. |
| `tests/019-red-verification.md` | Collected-test count and expected missing-feature failures. |
| `tests/019-green-verification.md` | Focused, migration, full-regression and browser results with honest limitations. |
| `tests/preview_cart.py` | Optional loopback-only browser fixture using temporary database/uploads and ordinary authentication routes; never registered in the real app. |
| `docs/019-shopping-cart-guide.md` | High-school-level explanation of join tables, ownership, derived totals, money and revalidation. |
| `docs/evidence/019-*` | Actual desktop and narrow cart screenshots returned by browser testing. |

`app/static/js/market.js` should not change. Recommendation cards are client-generated and are excluded by MM-019. No payment package, JavaScript framework or new third-party dependency is planned.

## 3. Data model and migration plan

### 3.1 `CartItem` model

Add this logical shape to `app/models/activity.py`:

```text
cart_items
  user_id     integer, FK users.id, primary-key part 1
  product_id  integer, FK products.id, primary-key part 2
  added_at    UTC timestamp, required
```

Both foreign keys use `ON DELETE RESTRICT`, matching the project's conservative relationship policy. Add:

- a product relationship used for eager loading;
- an index on `product_id` for foreign-key/product lookups; and
- an index beginning with `user_id` and then `added_at` for newest-added cart retrieval if query-plan inspection shows the composite primary key alone is insufficient for that ordering.

The composite primary key is the database-level duplicate defence. The table has no quantity, price snapshot, subtotal, checkout flag or order status.

### 3.2 Migration discipline

Generate one Alembic revision from the current head, then inspect and simplify it. The upgrade must only create `cart_items` and its intentional indexes. The downgrade must only remove those objects in reverse order.

The migration test will run on a fresh temporary SQLite database through the real Alembic configuration, verify columns/primary key/foreign keys/indexes, reject duplicate pairs and invalid parents, then downgrade and confirm earlier tables remain. Schema definitions must remain PostgreSQL-compatible even though PostgreSQL is unavailable on this computer.

Do not run a migration test against `instance/market-mirror.sqlite`. Only after tests and implementation are green will the local development database be upgraded with the normal project command, with an existing backup/rollback path documented first.

## 4. Blueprint, helper and query design

### 4.1 Routes

Create an `app.cart` blueprint with these exact contracts:

| Method and route | Purpose | Success |
| --- | --- | --- |
| `POST /cart/items/<int:product_id>` | Add one eligible product for `current_user` | `302` to a validated local return path, with status notice |
| `POST /cart/items/<int:product_id>/remove` | Remove only the current user's pair | `302` to `/cart`, idempotent |
| `GET /cart` | Review the current user's complete cart | `200` |
| `POST /cart/checkout` | Revalidate and display the non-mutating demonstration | `200` valid, `400` empty, `409` stale/ineligible |

Every route uses `login_required`. No route accepts a user ID. GET is never allowed on Add, Remove or Checkout.

### 4.2 Product eligibility

Use one server-side predicate/helper consistently:

```text
product exists
AND product.status == active
AND product.seller_id != current_user.id
AND product.seller.enabled == true
```

Add loads the product with its seller and, where supported, locks it for the small validation/insert transaction. Missing or archived products return non-revealing 404. Sold, own or disabled-seller products return a helpful 400 validation response without inserting a row.

Checkout applies the same rule to every cart row using fresh database data. The cart review template receives a server-prepared presentation for each row so templates do not accidentally expose fields of sold/archived products.

### 4.3 Add concurrency and idempotency

The route first validates the product, then attempts to create `CartItem(current_user.id, product_id)`. The composite key is authoritative.

If an `IntegrityError` occurs, roll back and check only whether that exact current-user/product pair now exists:

- if it exists, treat the operation as an idempotent “already in your cart” result;
- otherwise re-raise so the normal database error handler reports the real failure.

Do not swallow unrelated constraint/database failures. A competing request test will use separate sessions/transactions where practical; at minimum the database constraint and replay path must be proven.

### 4.4 Safe return path

Public card forms include the current server-rendered local path as `next`. Pass it through the existing `safe_next()` validation and add a cart-specific fallback of `/cart` when it is absent/invalid. Never use an unchecked `Referer`, full URL, scheme, hostname or client-supplied redirect.

Anonymous Sign-in links use the existing login `next` mechanism with the safe local request path. Signing in returns the visitor to the card page; it does not silently perform the earlier Add action.

### 4.5 Cart loading and unavailable presentation

Load current-user `CartItem` rows only, ordered by `added_at DESC, product_id DESC`, eager-loading product and seller. Use a fixed 20-row page to keep response size bounded while preserving the full row count and full-cart subtotal separately.

For each row, prepare one of two view states:

- **eligible**: card information, seller link, current price and Remove form;
- **unavailable**: generic label and Remove form only.

Do not render the archived/sold product title, image, seller or price in HTML, hidden inputs, accessibility names or logs. The form needs only the numeric endpoint path and CSRF token. Tests use unique private canaries to detect leakage.

The navigation count and cart heading count include every current-user row, including unavailable rows. The subtotal uses only eligible rows. A warning appears when any unavailable row exists.

### 4.6 Exact full-cart subtotal

Compute the full eligible subtotal on the server, not from the current 20-row page and not in JavaScript. Use `Decimal`/the project's `Money` type or a database sum that returns the correct money type. Normalize the display to two decimal places and fixed USD currency.

Tests will cover `0.10 + 0.20`, larger values and a cart spanning two pages so binary float or page-only mistakes are visible.

### 4.7 Demo checkout

Checkout loads/locks the current user's cart rows and referenced products as one validation unit, then:

- empty: render the cart with an error and HTTP 400;
- any missing/ineligible row: render refreshed safe presentations, warning and HTTP 409;
- all eligible: render the cart with a visible demo confirmation, full count and current subtotal, HTTP 200.

Before and after database snapshots must match for all three paths. Checkout must not call `record_event`, mark products sold, clear cart rows, create conversations/messages, or write an order. The confirmation explicitly says no payment and no order occurred.

## 5. Header count integration

Add a small helper that returns `0` for anonymous visitors and otherwise performs:

```text
COUNT(cart_items.product_id) WHERE cart_items.user_id == current_user.id
```

Expose it through the existing application context processor as `cart_count`. Cache the value on Flask `g` within one request so multiple template references cannot issue repeated queries. Because the value is rendered after Add/Remove redirects, it naturally reflects committed state.

The error handlers already replace the logged-in user with an anonymous user after database failure; keep that behaviour so an error page does not recursively fail while attempting to count the cart.

The authenticated navigation link uses an inline SVG with `aria-hidden="true"` plus visible `Cart` text and a count. The accessible name must communicate both destination and count; tests must not rely on the icon's shape.

## 6. Shared card integration

Extend `card(product, own=false)` without duplicating the whole card:

- `own=true`: retain existing owner preview and show no cart action;
- anonymous and public card: show Sign in to add to cart;
- authenticated product seller: show non-action text such as Your listing;
- authenticated other user and active card: show the CSRF-protected Add form.

The macro already runs on catalogue/search, Saved and seller-profile pages. This one change therefore covers the approved server-rendered public cards. Verify that an unavailable Saved row continues to use its generic placeholder and receives no Add button.

Do not add cart controls to `product.html` or JavaScript recommendation cards in MM-019; the user's request specifically targets product cards and the approved spec excludes client-generated recommendations.

## 7. Template and CSS design

### 7.1 Cart page structure

`cart.html` extends `base.html` and contains:

1. a single `Your cart` H1 and Browse products link;
2. a full-cart row count;
3. an accessible status/error area for add/remove/checkout messages;
4. a responsive list/grid of eligible product summaries and generic unavailable rows;
5. one Remove form per row;
6. an order-summary panel with eligible subtotal and current-price note;
7. an unavailable-items warning when needed; and
8. an enabled Checkout form only when every row is eligible and at least one exists, otherwise a disabled button plus visible reason or no button for the empty state.

Do not place full card markup around unavailable products. Avoid hidden fields for prices/counts/user IDs. Checkout uses only CSRF because the server loads the current user's complete cart.

### 7.2 Responsive/accessibility styling

Use scoped classes such as `.cart-link`, `.cart-count`, `.cart-row` and `.cart-summary`. Reuse theme colours and existing focus styles. Allow the header navigation and cart summary to wrap. Use `min-width: 0` and `overflow-wrap: anywhere` for long titles. The subtotal/action area must stack below rows on narrow screens rather than creating horizontal scrolling.

No hover-only instruction, colour-only availability signal or animation is required. Buttons remain ordinary HTML controls and the page remains complete with scripts removed.

## 8. Test-first execution sequence

1. Obtain PLAN-019 approval.
2. Write `tests/test_cart.py`, migration tests and `tests/019-browser-checklist.md` without application/cart implementation.
3. Run collection. Import missing `CartItem` inside individual tests so absence produces intended test failures, not a collection error.
4. Run the focused suite against unchanged application code and record Red evidence. Expected failures must be missing model/table/routes/markup; fixture, import-at-collection and unrelated baseline failures are invalid Red checkpoints.
5. Implement the model and migration first, then routes/helpers, then templates/CSS.
6. Run focused tests until green without weakening assertions.
7. Run migration upgrade/downgrade tests and schema check using temporary databases.
8. Run the complete regression suite, including MM-017 lightbox and MM-018 seller-profile tests.
9. Upgrade a copied/temporary version of the local database first. After verification, run the approved migration against the local development database; never recreate or reseed it.
10. Run browser acceptance only against an isolated cart fixture for mutations. Use the real local site only for read-only regression if needed.
11. Save screenshots, Green evidence and the beginner guide. Stop the disposable fixture server and restore temporary viewport settings.

Planned commands from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_cart.py tests\test_cart_migration.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_cart.py tests\test_cart_migration.py -q --basetemp=.pytest-tmp\mm019-red
.\.venv\Scripts\python.exe -m pytest tests\test_cart.py tests\test_cart_migration.py -q --basetemp=.pytest-tmp\mm019-green
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm019-regression
```

If the migration cases are added to the existing file rather than `test_cart_migration.py`, substitute that exact test path and record the real command. Test temp paths must never point to `instance/`, uploads or user work.

## 9. Pytest coverage matrix

| Group | Required cases | Spec coverage |
| --- | --- | --- |
| Model constraints | Valid row; duplicate pair; invalid user/product FK; UTC `added_at`; relationship loads | AC-019-02, 15 |
| Migration | Fresh upgrade, columns, composite PK, FKs/indexes, duplicate rejection, downgrade preserves prior schema | AC-019-15 |
| Authentication | Anonymous GET cart and POST actions redirect to login; no mutation; safe login `next` | AC-019-03 |
| Add success | Other seller's active product creates one row, commits, flashes safe notice, redirects locally, count becomes 1 | AC-019-01 |
| Add rejection | Own, sold, archived, missing, disabled-seller and extreme IDs; exact status/no row | AC-019-03, 07 |
| Add replay/race | Sequential duplicate and competing inserts produce one row and no 500; unrelated integrity failure is not swallowed | AC-019-02 |
| CSRF/methods | Missing/invalid CSRF rejected for Add/Remove/Checkout; GET methods return 405; database unchanged | AC-019-06, 09 |
| Account isolation | Two rich carts; each page/count/subtotal contains only its rows; attacker removal/checkout changes nothing for victim | AC-019-04 |
| Forged fields/redirect | `user_id`, price, subtotal, status, quantity and external/encoded/backslash redirects cannot alter server decisions or escape site | AC-019-04 |
| Card placement | Public catalogue/search, Saved and seller profile have correct buyer/anonymous control; dashboard/private cards and unavailable rows do not | AC-019-12 |
| Header count | Anonymous presentation; authenticated 0/1/many; add/remove updates; unavailable counted; no cross-user count; bounded query count | AC-019-01, 11 |
| Cart rendering | H1, browse link, newest-added order, picture/placeholder, title/current price/condition/seller/product links, Remove names | AC-019-05 |
| Money | Empty, `0.10 + 0.20`, maximum-valid prices, status exclusion and >20-row cart; exact full-cart subtotal, two decimals | AC-019-05 |
| Pagination | 21 rows give 20+1 unique rows; full count/subtotal unchanged; cart-scoped links and deterministic ordering | AC-019-05 |
| Unavailable privacy | Sold/archived canary title/email/seller/image/price absent; generic row/removal present; counted but excluded from subtotal | AC-019-07 |
| Remove | Own row removed; missing repeat safe; victim row untouched; Saved row/listing/image unchanged; count/subtotal refreshed | AC-019-06 |
| Empty checkout | Empty page 200 and helpful state; direct checkout returns documented validation and no writes | AC-019-08 |
| Valid demo checkout | Full fresh validation; confirmation says no payment/order; database tables before/after identical; repeated request identical | AC-019-09 |
| Stale checkout | Product changes active→sold/archived between render and POST; HTTP 409, safe refreshed row, no partial claim/write | AC-019-10 |
| Failures | Inject commit/query failures for Add/Remove/Checkout; rollback, friendly response, no false success/partial row | Security/reliability |
| Escaping/privacy | HTML-like title safely escaped; forbidden email/hash/message/history/path markers absent; CSRF not logged | Security/accessibility |
| Regressions | Existing Saved, messages, cards, seller profiles, search, media/lightbox, AI recommendations and status transitions pass | AC-019-13 |

Use table/database snapshots for non-mutating checkout, but exclude expected session/CSRF mechanics from database assertions because those are not database rows. Avoid brittle whole-page matching; parse semantic elements and stable IDs/classes.

## 10. Browser acceptance plan

Define the checklist before application implementation, then verify with a loopback-only temporary app and ordinary pages/forms:

1. Sign in as a seeded buyer using the normal login form.
2. From catalogue, use keyboard to Add two products and observe notices/header count after each redirect.
3. Add a product from a seller profile and one from Saved; confirm shared-card behaviour.
4. Open Cart and verify pictures/placeholders, titles, seller/product links, count and exact subtotal.
5. Attempt duplicate Add and verify one row/count.
6. Remove one row and verify count/subtotal; repeat the URL/form scenario safely.
7. Use a fixture whose product becomes sold/archived through a controlled server/test setup; verify only generic unavailable content, row count retention, subtotal exclusion and blocked Checkout.
8. Restore an all-eligible isolated fixture and click Checkout. Verify the exact no-payment/no-order confirmation and unchanged cart/count.
9. Sign in as a second buyer; verify zero/independent count and no first-buyer content.
10. Check desktop and 320-pixel viewport with long title/count; inspect horizontal overflow and focus styles.
11. Use Tab/Enter through navigation, Add, Browse, product/seller, Remove and Checkout controls.
12. Run a controlled no-script fixture and repeat core Add/Remove/Checkout.
13. Check product detail/lightbox and seller-profile navigation as regression smoke tests.
14. Inspect browser warnings/errors and save desktop/narrow screenshots showing header count, rows and summary.

The fixture database and uploads live under `.pytest-tmp` or another temporary project-owned path, never `instance/`. Browser actions must not modify the real demo cart or products. Actual 200% zoom and dark-mode checks are attempted only if browser controls expose them; a 320-pixel resize is not called a zoom test.

## 11. Main risks and mitigations

| Risk | Mitigation |
| --- | --- |
| A cart is mistaken for a reservation | Keep products active; explain that cart does not reserve; revalidate Checkout. |
| Checkout implies real purchase | Exact visible no-payment/no-order message; no order/status/cart mutation. |
| One user accesses another cart | Derive owner only from `current_user`; scope every query/delete/count. |
| Duplicate Add causes 500 | Composite key plus narrow IntegrityError recovery and race test. |
| Sold/archived product leaks | Server view-state mapping; generic HTML/accessibility content; canary tests. |
| Header count disagrees | Derive from cart rows after commit; request-local cache only. |
| Subtotal uses page or float | Full eligible query with exact money arithmetic; 0.10+0.20 and 21-row tests. |
| Seller changes status during checkout | Fresh validation/lock; all-or-nothing response; no mutation. |
| Shared macro breaks owner cards | Explicit `own=true` branch and catalogue/saved/seller/dashboard regression matrix. |
| Global context query breaks error pages | Anonymous fallback after database errors; request cache; injected-failure tests. |
| Migration damages local data | Temporary upgrade/downgrade first; scoped revision; no reset/reseed. |
| Narrow header overflows | Wrapping nav/count CSS and real 320-pixel browser check. |

## 12. Rollback plan

Because demo Checkout never mutates products or creates orders, rollback is limited to this feature:

1. stop the server;
2. downgrade one Alembic revision to remove `cart_items` if intentionally rolling back data;
3. reverse only cart blueprint/model/export/context/template/CSS integration; and
4. rerun the pre-MM-019 regression suite.

Before a destructive downgrade, export or copy the local SQLite database. Downgrade removes cart rows, so it is data-destructive even though products/users remain; never run it merely as a test on the real database.

## 13. Beginner learning handoff

The guide will explain:

- a many-to-many join table as pairs of IDs;
- why the composite key prevents duplicates;
- why `current_user.id` must come from the session, not the form;
- why totals/counts are derived rather than stored twice;
- why money uses Decimal rather than float;
- why product eligibility is checked both at Add and Checkout; and
- why a cart is not the same as a completed order.

The student exercise will create two isolated users and one product, add the same product to both carts, then explain why that is allowed, why neither cart reserves it and why changing the product to sold blocks both checkouts.

## 14. Completion criteria

MM-019 is complete only when:

- approved tests have a valid Red checkpoint, then all turn Green;
- migration upgrade/downgrade and database constraints are verified on temporary databases;
- the entire regression suite passes;
- real browser evidence covers add, count, review, remove, stale product, demo checkout, account isolation, keyboard and narrow layout;
- no real payment/order claim or hidden database mutation occurs;
- the local development database is upgraded without reset/reseed and the server starts normally; and
- evidence and the beginner guide report any unverified browser/device checks honestly.

## 15. Approval gate

The user replied **“I approve PLAN-019”** on 2026-11-02. This authorizes writing the cart/migration tests and browser checklist, validating their Red results against unchanged application code, and only then implementing MM-019.
