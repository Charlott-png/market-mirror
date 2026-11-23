# PLAN-025 — Functional checkout, orders, and sold listings

Status: EXECUTED AND VERIFIED — approved 2026-11-06; completed 2026-11-07 (Asia/Shanghai)

Date: 2026-11-06 (Asia/Shanghai)

Approved specification: MM-025, explicitly approved by the user on 2026-11-06.

## 1. Outcome

Replace the current safe demonstration in `POST /cart/checkout` with one atomic,
idempotent local purchase transaction. A successful checkout will create a
completed order and its item snapshots, mark every purchased listing sold,
remove the buyer's purchased cart rows, and redirect to a private confirmation
page headed **Thank you for your purchase**.

This plan implements only a classroom marketplace transaction. It deliberately
does not connect to a payment provider, collect an address, transfer money or
promise delivery.

## 2. Architecture

```text
GET /cart
    │
    ├─ load complete current-user cart and exact total
    ├─ compute deterministic cart fingerprint
    └─ create signed checkout token
             │
             ▼
POST /cart/checkout  (login + CSRF)
    │
    ├─ verify signature, buyer, nonce and age
    ├─ existing order for buyer + nonce? ── yes ──► redirect to receipt
    ├─ reload and lock complete cart/products in stable ID order
    ├─ validate eligibility and fingerprint
    │
    └─ one database transaction
          ├─ INSERT orders
          ├─ INSERT order_items snapshots
          ├─ UPDATE products: active → sold
          ├─ DELETE buyer's purchased cart_items
          └─ COMMIT once
                    │
                    ▼
          303 /orders/<id>/success
                    │
                    ├─ verify current buyer owns order
                    └─ render read-only thank-you receipt
```

The web route will coordinate HTTP responses. A separate checkout service will
own cart fingerprints, signed-token handling, validation, locks and transaction
state. Models will own field validation. Templates will only present data
already authorized and prepared by the server.

## 3. Planned files

| File | Planned responsibility |
| --- | --- |
| `app/models/order.py` | Add `Order` and `OrderItem`, constraints, validators and relationships. |
| `app/models/__init__.py` | Export the new models so SQLAlchemy, migrations, tests and shell tools discover them. |
| `migrations/versions/<revision>_mm025_orders.py` | Create only `orders`, `order_items`, their constraints and indexes from current migration head. |
| `app/checkout.py` | Add constant-size cart fingerprint, signed-token helpers, deterministic locking and the atomic checkout service. |
| `app/cart.py` | Render a checkout token and replace demo checkout with validation/service calls and safe responses. |
| `app/orders.py` | Register the private read-only success-page route. |
| `app/__init__.py` | Register the orders blueprint and expose `Order`/`OrderItem` in the Flask shell context. |
| `app/templates/cart.html` | Add the signed hidden field and accurate classroom-purchase wording. |
| `app/templates/order_success.html` | Render the private thank-you receipt using snapshots and exact totals. |
| `app/static/css/style.css` | Add small scoped order-receipt styles and narrow-screen wrapping using existing design tokens. |
| `tests/test_checkout.py` | Test models, routes, ownership, tokens, exact money, atomicity, idempotency and concurrency. |
| `tests/test_checkout_migration.py` | Test fresh/current upgrade, constraints, data preservation and isolated downgrade/re-upgrade. |
| `tests/test_cart.py` | Replace only MM-019's now-obsolete “checkout is non-mutating” assertions; retain all other cart contracts. |
| `tests/025-browser-checklist.md` | Define isolated desktop/mobile/keyboard/no-JavaScript acceptance checks. |
| `tests/025-red-verification.md` | Record the exact expected failures before implementation. |
| `tests/025-green-verification.md` | Record focused, migration, regression, complete-suite and browser results. |
| `docs/025-checkout-guide.md` | Explain orders, transactions, snapshots, signed tokens and concurrency for a high-school-level reader. |
| `README.md` | Link the guide and describe checkout as a local demo purchase with no real payment. |

No JavaScript file, payment dependency, image file, AI integration or external
service is required.

## 4. Database design

### 4.1 `Order`

Create `app/models/order.py` rather than expanding the already broad
`activity.py` module.

The `orders` table will use:

```text
id               INTEGER primary key
buyer_id         INTEGER NOT NULL → users.id RESTRICT, indexed
status           VARCHAR(20) NOT NULL, default "completed"
total_amount     Money NOT NULL
currency         VARCHAR(3) NOT NULL, default "USD"
checkout_nonce   VARCHAR(64) NOT NULL
created_at       UTCDateTime NOT NULL
UNIQUE (buyer_id, checkout_nonce)
```

Named checks will enforce:

- `status = 'completed'`;
- `currency = 'USD'`;
- nonce length between 20 and 64; and
- exact valid Money range, using integer cents on SQLite and `NUMERIC(10,2)` on
  PostgreSQL, matching the existing `Product.price` design.

Python validators will use the existing `validated_price`, `bounded_text` and
choice-validation style so invalid values fail clearly before commit where
possible. `created_at` will use `utc_now` and `UTCDateTime`.

### 4.2 `OrderItem`

The `order_items` table will use:

```text
id                 INTEGER primary key
order_id           INTEGER NOT NULL → orders.id CASCADE, indexed
product_id         INTEGER NOT NULL → products.id RESTRICT, UNIQUE
seller_id          INTEGER NOT NULL → users.id RESTRICT, indexed
product_title      VARCHAR(120) NOT NULL
seller_username    VARCHAR(30) NOT NULL
unit_price         Money NOT NULL
currency           VARCHAR(3) NOT NULL, default "USD"
```

Named checks will enforce product-title length, canonical public username,
`USD`, and exact valid Money range. The seller snapshot uses the same 3–30
character lowercase username rules as `User`.

`order_id` uses `ON DELETE CASCADE` internally so a database administrator who
intentionally removes an order cannot leave meaningless item rows. MM-025
exposes no application delete operation. Buyer, seller and product references
remain `RESTRICT` to preserve history.

The global unique product constraint is the database-level final guard against
selling one listing twice.

### 4.3 Relationships

- `Order.buyer` points to `User`.
- `Order.items` is ordered deterministically by `OrderItem.id` and uses
  delete-orphan cascade only within the in-memory order aggregate.
- `OrderItem.product` and `OrderItem.seller` remain available for internal
  authorization/auditing, but the success template displays snapshots rather
  than current mutable names/prices.

No reverse `User.orders` or `Product.order_item` property is necessary for
MM-025. Keeping only relationships used by this feature avoids confusing
several foreign-key paths to `User`.

### 4.4 Migration

Generate a new Alembic revision whose `down_revision` is
`f19c7a42e0b1`. Inspect and simplify the generated script rather than trusting
autogeneration blindly.

The migration will freeze its historical SQLAlchemy types and checks instead
of importing future live model definitions. It will select integer cents/checks
for SQLite and numeric dollars/checks for PostgreSQL, like MM-002. Creation
order is `orders` then `order_items`; downgrade order is the reverse after
dropping intentional indexes.

Migration testing will use temporary databases only. The real `instance`
database will be backed up and upgraded only after all isolated tests pass; it
will not be downgraded during verification.

## 5. Checkout token design

Use `itsdangerous.URLSafeTimedSerializer`, already provided through Flask's
dependency set, with an MM-025-specific salt. Do not add a new package.

The signed payload will contain:

```text
buyer_id
checkout_nonce = secrets.token_urlsafe(24)
cart_fingerprint
```

The serializer supplies the signed creation time. `max_age=1800` enforces a
30-minute form lifetime.

### 5.1 Canonical fingerprint

For the complete cart, build tuples sorted by product ID:

```text
(product_id, product.version, format(product.price, ".2f"), product.currency)
```

Encode them with an unambiguous JSON representation, then calculate SHA-256.
Do not use Python's process-randomized `hash()` function. The fingerprint is
constant-size and includes all pages of a paginated cart.

Status and seller eligibility are validated separately from the database. A
status/seller change therefore causes rejection even if its value is not in
the price fingerprint.

### 5.2 Verification order

1. Require exactly one nonblank `checkout_token` form value with a reasonable
   maximum encoded length.
2. Verify its signature and structure.
3. Confirm its buyer ID equals `current_user.id`.
4. Check for an existing `(buyer_id, nonce)` order.
5. If an existing order is found, redirect to it even if the form has become
   older than 30 minutes; the signature must still be valid. This safely
   recovers when the original success response was lost.
6. For a nonce not yet used, enforce the 30-minute age and current fingerprint.

A bad signature, shape, repeated parameter or wrong owner produces HTTP 400.
An authentic but expired/stale form produces HTTP 409 and a refreshed cart.
Token text is never logged.

## 6. Checkout service

`app/checkout.py` will expose small named operations instead of one oversized
route:

- `cart_fingerprint(rows)` — deterministic exact snapshot hash;
- `make_checkout_token(user_id, rows)` — signed buyer/nonce/fingerprint;
- `read_checkout_token(token, user_id)` — structural/signature/age result;
- `lock_checkout_rows(user_id)` — reload current cart/products safely;
- `complete_checkout(user_id, token_data)` — validate and mutate once; and
- small typed/domain exceptions for bad form, stale cart and unavailable cart.

The service receives the authenticated numeric buyer ID from the route and
does not import browser-submitted buyer/product/price data.

### 6.1 Deterministic locks

Every checkout will collect product IDs and lock products in ascending ID order
to reduce deadlocks.

- **PostgreSQL:** use `SELECT ... FOR UPDATE` for the current buyer's cart rows
  and referenced product rows, with eager seller loading performed in a safe
  separate/select-in query where necessary.
- **SQLite:** issue the project's established harmless `UPDATE products SET
  version = version` write-lock operation in sorted ID order, then reload using
  `populate_existing=True`. SQLite's single-writer behavior serializes the
  mutation. The no-op lock must not increase the optimistic version.

After obtaining protection, reload rather than trust ORM objects cached before
the lock. Validate the complete set again.

### 6.2 Eligibility and exact totals

The service will reuse a provider-independent eligibility helper that accepts
an explicit buyer ID rather than reading `current_user`. It checks active
status, distinct buyer/seller and enabled seller.

Calculate totals with `Decimal`, starting at `Decimal("0.00")`, and quantize to
two decimal places. Never accept a posted total and never use `float`.

### 6.3 Atomic mutation

Within the current SQLAlchemy transaction:

1. Create `Order(status="completed", ...)`.
2. Flush it to obtain `order.id` and surface nonce constraints.
3. Create an `OrderItem` snapshot for each locked product.
4. Set every locked active product to `sold`; SQLAlchemy's existing optimistic
   version automatically advances.
5. Delete exactly the snapshotted `CartItem` rows for this buyer.
6. Flush and commit once from the route/service boundary.

The implementation will verify the number of deleted rows matches the checkout
set. A mismatch is a conflict and causes rollback, not partial success.

Do not delete other users' cart rows. Do not alter Saved products, images,
conversations, messages or interaction events.

### 6.4 Failure mapping

- Empty cart: rollback, HTTP 400 cart response.
- Ineligible or stale cart: rollback, HTTP 409 refreshed cart response.
- `StaleDataError` or unique ordered-product conflict: rollback, then return a
  safe HTTP 409 unless the same nonce now identifies the already-completed
  order.
- Same buyer/nonce replay: rollback/reload and 303 to existing order.
- Other SQLAlchemy error: allow the existing safe 503 handler to roll back and
  hide details.

Rendering after a rollback must use newly queried objects, not expired objects
from the failed transaction.

## 7. Cart route and presentation

### 7.1 `GET /cart`

Keep the current pagination and full-cart summary. `cart_state()` will create a
signed checkout token only when:

- total rows are greater than zero; and
- every row is eligible.

The token represents the full cart, not the visible page. Empty or unavailable
carts receive no usable token.

### 7.2 `POST /cart/checkout`

Keep this exact address so existing navigation and forms do not move. The route
will:

- require login and existing global CSRF;
- reject repeated `checkout_token` fields;
- delegate all business decisions to the checkout service;
- render 400/409 cart errors for recoverable validation problems; and
- return `redirect(url_for("orders.success", order_id=order.id), code=303)` on
  success or idempotent replay.

The route will not contain product loops that duplicate service rules.

### 7.3 Cart template

When enabled, the Checkout form adds:

```html
<input type="hidden" name="checkout_token" value="...">
```

Jinja auto-escaping remains active. The old MM-019 text is replaced with a
short explanation that Checkout creates a local order and marks listings Sold,
but does not collect real payment.

No JavaScript is needed, so keyboard and no-script use remain first class.

## 8. Orders blueprint and success page

Create an `orders` blueprint in `app/orders.py` and register it in the app
factory.

`GET /orders/<int:order_id>/success` will:

1. require login;
2. load the order where both `Order.id == order_id` and
   `Order.buyer_id == current_user.id`;
3. eager-load its ordered item snapshots;
4. abort 404 when that scoped query returns nothing; and
5. render `order_success.html` without performing a write.

The template will include one H1, order number, UTC-aware formatted completion
time, a semantic item list/table, snapshot title/seller/price, exact total,
no-real-payment disclosure and an Explore link. It will not link to a sold
product detail that the buyer may no longer be authorized to see.

CSS will reuse `.panel`, `.price`, focus and color variables. New scoped rules
will allow long titles/usernames to wrap and convert multi-column receipt rows
to a readable stack at the existing mobile breakpoint.

## 9. Navigation and integration behavior

No new top or bottom navigation destination is required. The existing cart
count is derived from `cart_items`, so the 303 destination naturally shows zero
after commit without adding a second counter.

Current public discovery already filters `Product.status == "active"`; current
seller management already displays active/sold/archived. Regression tests will
prove those paths respond correctly instead of rewriting them.

The app shell context will include `Order` and `OrderItem` for university demos
and debugging, but no order data will be injected into ordinary templates.

## 10. Test-first sequence

After PLAN-025 approval, work will follow this order exactly:

1. Add `tests/test_checkout.py`, `tests/test_checkout_migration.py` and
   `tests/025-browser-checklist.md` only.
2. Update only the obsolete checkout expectations in `tests/test_cart.py` so
   they describe MM-025 rather than MM-019's demo behavior.
3. Run collection to prove the new tests are syntactically valid.
4. Run the focused tests against the unchanged application.
5. Record the Red failures in `tests/025-red-verification.md`. Expected reasons
   include missing `Order`/`OrderItem`, missing signed token, no success route,
   and the old non-mutating checkout response. Failures caused by broken test
   fixtures or syntax do not count as valid Red and will be corrected before
   implementation.
6. Add the models and migration.
7. Add checkout token/service logic.
8. Integrate the cart route/template.
9. Add the orders blueprint, success template and CSS.
10. Run focused tests until Green.
11. Run migration, cart, marketplace/search/seller/mobile and security
    regressions.
12. Run the complete pytest suite.
13. Upgrade a copied/temporary representation of the current database, inspect
    it, then back up and upgrade the real local database once.
14. Run the isolated browser checklist without changing real demo products.
15. Write the student guide, README link and Green evidence using actual
    commands/results only.

No production/application file will be changed during steps 1–5.

## 11. Planned pytest coverage

### 11.1 Model and constraint cases

- valid order with one/many items and UTC timestamp;
- exact Money round trip on SQLite;
- null required fields;
- empty/short/long nonce;
- unsupported status and currency;
- invalid, over-precision, zero, negative and above-maximum totals/prices;
- invalid title/username snapshots;
- duplicate buyer/nonce;
- duplicate product across two orders;
- missing buyer/order/product/seller foreign keys;
- relationship ordering and account isolation; and
- snapshot values remain unchanged when current product/user objects change.

### 11.2 Token/fingerprint cases

- same canonical cart produces the same fingerprint regardless of query order;
- IDs, versions, exact prices and currency affect the fingerprint;
- token payload contains no title, username, email or raw cart list;
- valid buyer/token decodes;
- missing, blank, oversized, repeated, malformed, bad-signature and wrong-user
  tokens fail without a write;
- authentic expired token with no order gives 409;
- expired signed token for an already committed nonce finds the existing order;
  and
- token values/error messages are absent from logs and responses.

### 11.3 Successful checkout cases

- single item;
- multiple items from multiple sellers;
- full cart larger than one display page;
- exact `0.10 + 0.20 == 0.30` total;
- server snapshots override forged request fields;
- all statuses become `sold` and product versions advance once;
- purchased current-user cart rows disappear;
- other-user cart rows remain;
- Saved/products/images/messages/events remain otherwise unchanged;
- 303 location names the created order;
- navigation count becomes zero;
- `/cart` returns the normal empty state; and
- browse/search/recommendations exclude sold items while seller management
  shows Sold.

### 11.4 Validation and privacy cases

- anonymous checkout redirects safely and cannot write;
- missing/invalid CSRF gives 400 and cannot write;
- empty cart gives 400/no order;
- sold, archived, missing, disabled-seller and own-listing rows give 409/no
  partial change;
- add/remove, price/version/status/seller changes after GET give 409;
- forged form buyer/product/seller/price/total/currency/status/order fields are
  ignored;
- a different buyer gets 404 for another order;
- missing/extreme order IDs are safe;
- receipt output escapes Unicode/HTML-like snapshot content; and
- no email, password hash, message body, token or private canary appears.

### 11.5 Idempotency and atomicity cases

- sequential double POST with one token creates one order;
- concurrent same-token POST creates one order;
- retry after successful response loss redirects to the existing receipt;
- old completed token cannot purchase a newly added cart;
- two buyers racing for one product produce one winner at most;
- a multi-item loser retains the complete cart and produces no partial order;
- simulated failure at order flush, item flush, status flush, cart delete and
  commit restores exact before-state snapshots; and
- injected database-error text is not exposed.

SQLite race tests will use separate clients and database sessions against one
temporary file, not an in-memory database shared unsafely between threads.
PostgreSQL-specific SQL behavior will be asserted at the statement/helper level
when no local PostgreSQL server is configured; the portable unique constraints
remain exercised on SQLite.

### 11.6 Migration cases

- upgrade from empty revision chain to head;
- upgrade from MM-019 with existing users/products/cart rows preserves data;
- expected tables, columns, keys, checks and indexes exist;
- database constraints reject invalid/duplicate raw inserts;
- downgrade only MM-025 removes order tables and leaves MM-019 data;
- re-upgrade succeeds; and
- migration head has no branches.

## 12. Verification commands

Use the project's virtual environment and test-owned temporary paths:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py -q --basetemp=.pytest-tmp\mm025-red
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py -q --basetemp=.pytest-tmp\mm025-green
.\.venv\Scripts\python.exe -m pytest tests\test_marketplace.py tests\test_live_search.py tests\test_seller_profile.py tests\test_mobile_navigation.py tests\test_hardening.py -q --basetemp=.pytest-tmp\mm025-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm025-full
.\.venv\Scripts\python.exe -m flask --app run.py db current
.\.venv\Scripts\python.exe -m flask --app run.py db heads
```

The exact collected/passed/failed counts will be recorded only after the
commands are actually run. A test timeout will be applied to custom concurrency
workers so a locking defect cannot hang the suite indefinitely.

## 13. Browser acceptance checklist

Use an isolated temporary app fixture containing:

- one buyer;
- two enabled sellers;
- three active products with known pictures/prices;
- a second buyer whose cart shares one product; and
- one unavailable cart row for conflict presentation.

The checklist will verify:

1. buyer signs in and adds two products;
2. cart shows the exact complete total and accurate checkout explanation;
3. keyboard-only activation submits Checkout once;
4. browser follows 303 to the private thank-you page;
5. receipt shows order number, snapshots, exact prices/total and no-payment
   notice;
6. desktop and narrow mobile layouts have no horizontal overflow;
7. mobile fixed navigation remains usable;
8. Cart shows empty and navigation count zero afterward;
9. public Explore no longer shows sold products;
10. seller listing view shows Sold;
11. second buyer sees a generic unavailable cart row;
12. refresh does not create another order;
13. another account receives 404 for the receipt; and
14. checkout and receipt still work with JavaScript disabled.

Actual screenshots may be stored under `docs/evidence/025-*`. Browser checkout
will never run against the real demo database.

## 14. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Two buyers purchase one listing | Sorted locks, optimistic product version, unique `order_items.product_id`, conflict tests. |
| Double-click creates two orders | Signed random nonce, unique buyer/nonce, existing-order replay redirect. |
| Price changes after review | Fingerprint includes product version and exact price; stale form returns 409. |
| Part of checkout commits | One transaction and one commit; forced-failure rollback tests at every stage. |
| Float changes money | Existing Money/Decimal type and explicit exact-money tests. |
| Hidden form fields are forged | Server reloads all buyer/product/seller/price data; signed fingerprint is verified. |
| Deadlock from several products | Lock product rows in ascending ID order; bounded concurrency test. |
| SQLite ignores `FOR UPDATE` | Existing no-op UPDATE technique acquires SQLite writer protection. |
| Receipt leaks another user's order | Buyer-scoped query and indistinguishable 404. |
| Current data rewrites history | Order-item snapshots; receipt reads snapshots. |
| Other carts silently change | Do not delete their rows; existing unavailable placeholder remains. |
| User thinks money was charged | Visible cart and receipt disclosure; no payment fields/provider/dependency. |
| Migration harms demo data | Temporary upgrade tests, backup, forward-only real upgrade, no real downgrade. |
| Error details leak | Existing generic database handler plus explicit canary tests. |

## 15. Rollback and recovery

Before upgrading the real local database, copy the SQLite file to a dated
backup while the server is stopped. Record the exact backup location in Green
verification without exposing personal paths unnecessarily.

If application code must be rolled back before any real checkout, restore the
previous code and leave the additive order tables unused. If real local orders
already exist, do not casually downgrade: that would delete order history while
products could remain sold and carts empty. Restore the coordinated database
backup or write an explicit data-reversal procedure after inspecting the exact
orders.

The application will not provide a “reverse order” button in MM-025 because
refund/cancellation rules are out of scope.

## 16. Student documentation

`docs/025-checkout-guide.md` will explain, with a small receipt analogy:

- why `Order` and `OrderItem` are separate;
- how a one-to-many relationship works;
- why snapshots protect history;
- why money uses Decimal/cents instead of float;
- what a transaction and rollback do;
- how signed tokens expose tampering;
- why idempotency makes retries safe;
- how concurrency lets requests overlap; and
- why a working database checkout is still not a real payment system.

It will include safe commands for running focused tests and inspecting orders
in the Flask shell, plus small “try it yourself” exercises that use temporary
test data rather than the real demo catalogue.

## 17. Definition of done

Implementation is done only when:

1. every AC-025 acceptance criterion maps to at least one passing automated or
   documented browser test;
2. Red evidence proves tests existed before application implementation;
3. focused checkout/cart/migration tests pass;
4. complete project pytest suite passes;
5. migration head is singular and temporary upgrade/downgrade checks pass;
6. the real local database is backed up and upgraded once without data loss;
7. isolated desktop/mobile/no-script browser checks pass;
8. no real payment/network service was contacted;
9. documentation is understandable to a high-school student; and
10. changed files contain no secret keys, temporary databases or test uploads.

## 18. Execution record

The user approved PLAN-025 on 2026-11-06. The test files collected successfully
and produced the expected Red baseline before implementation. Models, migration,
checkout service, routes, templates and CSS were then added. Focused, regression,
complete-suite, schema-consistency and isolated browser checks passed on
2026-11-07. Exact evidence is recorded in the MM-025 verification files.
