# PLAN-028 — Recently Viewed and Same-Category Products

Status: IMPLEMENTED — PLAN-028 approved and completed on 2026-11-07

Date: 2026-11-07 (Asia/Shanghai)

Approved specification: MM-028, explicitly approved by the user on 2026-11-07.

## 1. Outcome

Implement a database-backed, five-item Recently Viewed history for signed-in
users and replace the product page's current indexed recommendation widget with
up to three server-rendered random active products from the same category.

Explore and Dashboard will display the same newest-first recent items. The
existing Dashboard **Discover more** recommendation feature remains unchanged.

## 2. Architecture

```text
Authenticated user opens an active product page
                  │
                  ├─ server renders product + 0–3 random active
                  │  same-category alternatives
                  │
                  └─ browser sends existing CSRF-protected view POST
                                      │
                                      ▼
                         lock this user's history update
                         insert or refresh (user, product)
                         keep newest five; delete older rows
                         commit essential history
                                      │
                                      └─ optional consented analytics event

Explore / Dashboard
       │
       └─ query current user's ≤5 history rows
          joined to currently active products + sellers
          render ordinary reusable product cards
```

The database is authoritative for identity, current product status, seller,
price and ordering. JavaScript only reports that a real product page loaded; it
never sends a user ID, timestamp or product metadata.

## 3. Planned file changes

| File | Planned responsibility |
| --- | --- |
| `app/models/activity.py` | Add `RecentProductView` with composite primary key, UTC timestamp and bounded-query index. |
| `app/models/__init__.py` | Export the model so migrations and tests discover it. |
| `migrations/versions/<revision>_mm028_recent_product_views.py` | Create/drop the new table and index without modifying existing rows. |
| `app/recently_viewed.py` | Centralize per-user locking, insert/refresh, five-row pruning and active recent-product query. |
| `app/engagement.py` | Extend the existing view POST and pass recent products to Dashboard. |
| `app/marketplace.py` | Pass recent products to Explore and select up to three random active same-category products for detail pages. |
| `app/templates/catalogue.html` | Render authenticated Recently Viewed cards/empty state outside the AJAX result replacement region. |
| `app/templates/dashboard.html` | Render Recently Viewed between recent listings and conversations. |
| `app/templates/product.html` | Move the authenticated active view marker to the correct shared location and server-render related cards. |
| `app/static/js/market.js` | Preserve one view POST, add explicit same-origin credentials and leave Dashboard Discover more logic intact. |
| `tests/test_recently_viewed.py` | Model, recording, isolation, retention, status, templates, related-product and query-bound tests. |
| `tests/test_mm028_migration.py` | Upgrade/downgrade/schema/index/data-preservation contracts. |
| Existing related test modules | Update only expectations intentionally changed by MM-028. |
| `tests/028-browser-checklist.md` | Desktop/mobile, two-account, AJAX and no-candidate verification. |
| `tests/028-red-verification.md` | Preserve focused pre-implementation failures. |
| `tests/028-green-verification.md` | Record focused, regression, full, migration and browser results. |
| `tests/preview_recently_viewed.py` | Temporary isolated users/products/history for browser checks. |
| `docs/028-recently-viewed-guide.md` | Beginner explanation of keys, upserts, bounded retention, joins and race conditions. |
| `README.md`, `docs/verification-matrix.md` | Link the guide and map AC-028 evidence. |

No new Python package or external service is planned.

## 4. Database migration plan

Create one Alembic revision after the current MM-026 head:

```text
recent_product_views
  user_id     INTEGER  PK/FK users.id
  product_id  INTEGER  PK/FK products.id
  viewed_at   UTC timestamp, required
```

Add an index equivalent to:

```text
(user_id, viewed_at)
```

Migration tests will verify:

1. upgrade from the current schema creates the exact columns, composite key,
   foreign keys and index;
2. existing users, products, product images, saves, carts, messages and orders
   remain unchanged;
3. duplicate `(user_id, product_id)` rows are rejected;
4. invalid user/product references are rejected with foreign keys enabled;
5. downgrade removes only the MM-028 table/index; and
6. a second upgrade works after downgrade.

Before applying the migration to the real local database, make an SQLite backup
with the project's existing backup helper or SQLite backup API. Run migration
and schema checks only after temporary-database migration tests pass.

## 5. Model design

Add `RecentProductView` to `app/models/activity.py`:

- `user_id` and `product_id` are the composite primary key;
- both are non-null foreign keys;
- `viewed_at` uses the existing timezone-aware UTC model type/default;
- index name follows the repository's explicit naming style; and
- a `product` relationship supports controlled eager loading.

The model stores no seller-authored text or duplicate snapshot of price/status.
Every card reads current product facts from `products`.

## 6. Recent-history service module

Create `app/recently_viewed.py` so route files do not duplicate query and
concurrency rules.

### 6.1 `record_recent_view(user_id, product_id)`

Planned sequence:

1. serialize writes on the user row using the existing SQLite no-op update and
   PostgreSQL `SELECT ... FOR UPDATE` pattern;
2. re-query the product and require `status == active`;
3. find the composite-key row;
4. insert it or replace its `viewed_at` with one timezone-aware UTC value;
5. flush so the new/updated order participates in pruning;
6. select this user's rows ordered by `viewed_at DESC, product_id DESC`;
7. delete every row after position five; and
8. commit in the endpoint, not secretly inside the helper.

The unique composite key remains the final duplicate guard. Tests will use
fixed/injected timestamps where stable order matters rather than sleeping.

### 6.2 `recent_products(user_id)`

Issue one bounded query that:

- joins history to Product;
- filters `Product.status == active`;
- eager-loads Product.seller for the card macro;
- orders by history timestamp then product ID descending; and
- limits to five.

It returns Product objects only, not another user's history records. Calling
code must not accept `user_id` from request input; it passes `current_user.id`.

## 7. View endpoint implementation

Keep the existing route and method:

```text
POST /products/<int:product_id>/view
```

Implementation order:

1. `@login_required` and Flask-WTF CSRF run normally;
2. fetch/recheck the product as active;
3. call the recent-history helper;
4. commit recent history;
5. call existing `record_event(product_id, "view")`, which independently
   checks personalization consent and handles optional failure; and
6. return empty `204`.

If essential storage raises a database error, roll back, log only a stable
event name and return a generic 503. The asynchronous page remains usable.
Optional analytics failure continues to log generically and must not undo the
already committed recent row.

The endpoint will not accept JSON/form data for user, product or time.

## 8. Product view marker and JavaScript

`product.html` currently emits the marker only inside one buyer branch and only
when personalization is enabled. Move it so it renders when:

- the product is active; and
- the visitor is authenticated.

It remains absent for anonymous, sold and private-preview pages. The marker
contains only the trusted route URL and CSRF token.

The existing `market.js` block remains small:

- find `[data-view-url]`;
- send one POST per rendered marker;
- set `credentials: "same-origin"` explicitly;
- include `X-CSRFToken`; and
- ignore network failure because tracking must not break the detail page.

No local/session storage, cookie history, retry loop or background timer is
added.

## 9. Explore integration

In `marketplace.browse()`:

- call `recent_products(current_user.id)` only when authenticated;
- pass `recent_products=[]` for anonymous users without issuing a history
  query; and
- preserve the existing `browse_context()` result and pagination.

In `catalogue.html`:

- import the reusable `card` macro;
- render the section only for authenticated Explore (`search` is true);
- place it above the search form and outside `#product-results` so AJAX cannot
  replace it;
- render up to five cards newest first; and
- show the approved empty-state sentence when the list is empty.

Seller profile and owner-listing uses of the same template must not gain the
section.

## 10. Dashboard integration

In `engagement.dashboard()` load recent products with the same helper and pass
them in the existing render call.

In `dashboard.html` render the section:

1. after **Your recent listings**;
2. before **Recent conversations**; and
3. before the unchanged **Discover more** block.

Use `card(product)` so seller links, images, current prices, status, and
Add-to-Cart/Your-listing controls retain existing behavior.

## 11. Same-category related products

In `marketplace.detail()` keep the current visible-product query, then issue
one additional query:

```text
Product.status == active
Product.category == displayed_product.category
Product.id != displayed_product.id
ORDER BY database random function
LIMIT 3
```

Eager-load each candidate's seller. SQLite and PostgreSQL both support the
SQLAlchemy `func.random()` expression used by this project plan.

In `product.html`:

- import `card` alongside `csrf_field`;
- remove the product page's empty `#recommendations` JavaScript container;
- when candidates exist, render a semantic section headed
  **You might also like** with ordinary cards; and
- omit the section completely when the list is empty.

This eliminates product-page loading/layout shift and makes alternatives work
without JavaScript.

Do not remove or rename Dashboard's `#recommendations` element. The existing
bottom `market.js` block will therefore still fetch Dashboard Discover more,
but it will no longer find a recommendation element on product pages.

## 12. Test-first module: `tests/test_recently_viewed.py`

No implementation begins until this module is written, collected and shown
failing for missing MM-028 behavior.

Planned test groups:

### 12.1 Model and pure helper contracts

- model table/column/primary-key/index metadata;
- same product for different users allowed;
- duplicate pair rejected;
- first view inserts;
- repeat view updates timestamp without duplicate;
- six distinct views retain newest five;
- stable timestamp/product-ID tie-break;
- pruning affects only the current user; and
- active recent query returns at most five in correct order with sellers eager.

### 12.2 Endpoint security and behavior

- anonymous POST receives normal login protection and stores nothing;
- real CSRF is required;
- active product returns 204 and records history;
- missing/sold/archived product returns 404 and stores nothing;
- payload cannot choose another user/time/product;
- personalization disabled still records recent history but no interaction
  event;
- personalization enabled records recent history and keeps existing deduped
  analytics behavior;
- optional analytics failure preserves recent history;
- essential database failure rolls back and returns generic failure; and
- repeated/concurrent requests produce one row and no more than five total.

### 12.3 Explore and Dashboard

- anonymous Explore has no heading, history IDs or extra history query;
- signed-in empty state appears on Explore and Dashboard;
- both pages show the same five products newest first;
- another user's products do not appear because of their history;
- current sold/archived history is hidden;
- current image fallback/seller/cart/own-listing behavior remains safe;
- seller/owner catalogue templates do not receive the section; and
- live-search JSON contains only search results and cannot duplicate/replace
  the separate recent section.

### 12.4 Same-category product detail

- exactly three when four or more alternatives exist;
- one/two alternatives render one/two;
- zero alternatives omit the section;
- current product excluded;
- sold, archived and other categories excluded;
- every returned product is distinct and active;
- sold base product can still show active category alternatives;
- seller/product/media/cart links are server-generated and escaped;
- no `GET /recommendations?product_id=` dependency in product markup/JS; and
- several requests always satisfy the constraints without asserting a flaky
  requirement that order must change.

### 12.5 Static/accessibility/query contracts

- semantic headings and reusable cards;
- marker present for authenticated active viewer regardless of personalization;
- marker absent for anonymous/sold/private preview;
- JS has one POST, CSRF, same-origin credentials and no storage/retry;
- recent section is outside AJAX replacement region;
- query counter stays within a documented bounded increase for Explore,
  Dashboard and detail; and
- 1,000-row fixture never loads unbounded history or related candidates into
  Python.

## 13. Migration test module

`tests/test_mm028_migration.py` will use temporary SQLite databases only.

Planned cases:

- upgrade current head to MM-028;
- inspect exact columns/nullability/PK/FKs/index;
- verify existing row counts/content before and after;
- insert valid rows and reject duplicate/invalid references;
- downgrade to current prior head while preserving unrelated tables/data;
- upgrade again; and
- compare SQLAlchemy model metadata with migrated schema expectations.

These tests precede migration of `instance/market-mirror.sqlite`.

## 14. Existing test adjustments

Only intentional behavior changes should modify existing expectations:

- marketplace view tests gain RecentProductView assertions;
- product template/recommendation tests switch from the product-page AJAX
  container to server-rendered same-category cards;
- AI `/recommendations` unit/HTTP tests remain because Dashboard still uses it;
- query-count thresholds may increase only by the documented one bounded recent
  query and/or one bounded related query; and
- mobile/cart/gallery/image-interaction tests retain current behavior.

No test should be weakened merely to make a regression disappear.

## 15. Red verification sequence

After PLAN-028 approval:

1. create the two new pytest modules and checklist/evidence shell;
2. collect all focused tests successfully;
3. run them before creating the model, migration, helper or templates;
4. confirm representative failures are missing table/model/history section and
   wrong product-related behavior—not fixture errors;
5. record command, count and representative failures in
   `tests/028-red-verification.md`; and
6. only then begin application implementation.

Some unchanged security/recommendation contracts may already pass. Valid Red
requires the core model, retention, private sections and same-category behavior
to fail.

## 16. Implementation order after valid Red

1. model and export;
2. Alembic migration;
3. recent-history record/query helpers;
4. view endpoint transaction and consented analytics separation;
5. product marker and view JavaScript contract;
6. Explore recent context/template;
7. Dashboard recent context/template;
8. detail related-product query/template and remove only product AJAX widget;
9. focused Green fixes;
10. temporary migration upgrade/downgrade verification;
11. related regression and full test suites;
12. back up and migrate the local database;
13. isolated browser verification;
14. beginner guide and verification evidence; and
15. update spec/plan statuses only after everything is complete.

## 17. Planned verification commands

Use workspace-local pytest temporary folders to avoid Windows protected-temp
problems:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_recently_viewed.py tests\test_mm028_migration.py -q --basetemp=.pytest-mm028-focused
.\.venv\Scripts\python.exe -m pytest tests\test_marketplace.py tests\test_ai.py tests\test_live_search.py tests\test_cart.py tests\test_mobile_navigation.py tests\test_product_image_interactions.py tests\test_multi_image_gallery.py tests\test_hardening.py -q --basetemp=.pytest-mm028-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-mm028-full
.\.venv\Scripts\python.exe -m pip check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\local.ps1 check
```

The full suite is authoritative. Final counts will be reported from actual
runs rather than guessed now.

## 18. Browser verification plan

`tests/preview_recently_viewed.py` will create only a temporary database and
generated placeholder images on a non-default loopback port.

Scenarios:

1. anonymous Explore has no Recently Viewed section;
2. sign in with personalization disabled;
3. open products A, B, C and verify C/B/A on Explore and Dashboard;
4. reopen A and verify A/C/B with no duplicate;
5. open three more distinct products and verify exactly five;
6. mark one recent product sold and verify it disappears;
7. sign in as a second user and verify independent empty history;
8. return to the first user and verify persistence;
9. AJAX-search and clear filters without moving/removing recent cards;
10. inspect product page with zero, one, two and more-than-three category
    alternatives;
11. verify current/sold/archived/unrelated products never appear;
12. disable JavaScript and verify server-rendered related cards still work;
13. check 320/360px and keyboard focus/card controls; and
14. confirm Dashboard Discover more still loads without browser errors.

Available automation may not prove a statistically random distribution. It
will prove every observed selection satisfies the required active/category/
distinct/exclusion/maximum-three constraints.

## 19. Local database migration procedure

Only after temporary migration tests and focused Green:

1. stop the verified local Waitress process chain;
2. create a timestamped SQLite backup under `instance/backups`;
3. run `local.ps1 migrate`;
4. run `local.ps1 check` and inspect the current revision;
5. verify existing product/user/order/cart/message counts are unchanged;
6. verify the new history table begins empty;
7. start one clean local server; and
8. run one deliberate browser history scenario.

No real product, price, seller, order or image is changed by the migration.
The first intentional product view after deployment creates the first history
row.

## 20. Acceptance-criteria traceability

| Criterion | Primary planned evidence |
| --- | --- |
| AC-028-01 | Auth/CSRF/status endpoint tests and history row assertions |
| AC-028-02 | Insert/review/prune/isolation/concurrency helper tests |
| AC-028-03 | Personalization off/on and analytics-failure tests |
| AC-028-04 | Explore/Dashboard private order and empty-state tests/browser checks |
| AC-028-05 | Cross-user and status-change privacy tests |
| AC-028-06 | AJAX boundary and reusable-card tests/browser flow |
| AC-028-07 | Parameterized zero/one/two/three+ same-category tests |
| AC-028-08 | Server-render/no-JS/static template and browser checks |
| AC-028-09 | Existing AI recommendation tests plus Dashboard browser check |
| AC-028-10 | CSRF/transaction/logging/bounded retention tests |
| AC-028-11 | Temporary migration upgrade/downgrade/schema/data checks |
| AC-028-12 | Accessibility/static/mobile/browser/full regression evidence |

## 21. Beginner learning guide

The final guide will explain at high-school level:

- why a composite key prevents the same product appearing twice;
- how “insert or update” makes a repeat view move to the front;
- why only five rows are kept;
- how a SQL join turns stored IDs into current product cards;
- why current status is checked again before display;
- why CSRF protects a history-writing POST;
- why a GET page should not secretly write browsing history;
- why related products can be server-rendered without JavaScript;
- why random selection tests constraints instead of exact order; and
- how database transactions protect two tabs updating together.

Small exercises will ask the student to predict the order after repeated and
sixth views, explain why another user's rows cannot appear, and identify which
same-category products are eligible.

## 22. Definition of done

MM-028 is complete only when:

1. valid focused Red evidence predates implementation;
2. all AC-028 requirements map to passing or honestly bounded evidence;
3. one user retains at most five distinct ordered rows under repeat/concurrent
   views;
4. privacy, status and cross-user isolation tests pass;
5. Explore/Dashboard sections and empty states pass server/browser checks;
6. product related cards always satisfy active/same-category/distinct/current-
   exclusion/maximum-three rules;
7. Dashboard Discover more and `/recommendations` remain Green;
8. migration upgrade/downgrade and local backed-up upgrade succeed;
9. focused, related regression, full pytest, dependency and schema checks pass;
10. desktop/mobile/keyboard/AJAX/no-JavaScript browser checks pass to supported
    extent;
11. existing real marketplace data are unchanged except deliberate new view
    rows created during final smoke testing; and
12. spec, plan, evidence and beginner documentation statuses are accurate.

## 23. Approval record

MM-028 and PLAN-028 were explicitly approved by the user on 2026-11-07.
The tests were written and shown failing before implementation. The focused,
related-regression, full-suite, migration and browser checks then passed. See
`tests/028-green-verification.md` for the recorded evidence.

