# MM-028 — Recently Viewed and Same-Category Products

Status: IMPLEMENTED — MM-028 and PLAN-028 approved; verification complete

Date: 2026-11-07 (Asia/Shanghai)

## 1. Purpose

Add two small product-discovery features:

1. A signed-in user can see the five most recent distinct active products they
   opened, on both Explore and Dashboard.
2. Every public product-detail page can show up to three random active products
   from the same category under **You might also like**.

The feature helps shoppers return to products they were considering and move
between related marketplace listings. It does not use Gemini, the trained
recommendation index, browser tracking, or external services.

## 2. Relationship to existing features

Market Mirror already has:

- a CSRF-protected `POST /products/<id>/view` endpoint;
- JavaScript that sends that request after an eligible product page loads;
- consented `InteractionEvent` analytics used by the existing recommendation
  system;
- a Dashboard **Discover more** section backed by `GET /recommendations`; and
- a product-page section currently labelled **You might also like**, which also
  calls `GET /recommendations` and may return up to six indexed/fallback items.

MM-028 will:

- preserve consented `InteractionEvent` analytics exactly as analytics;
- add a separate, user-facing recent-history table;
- make recent history work for every authenticated user even when optional
  personalization analytics is disabled;
- keep Dashboard **Discover more** unchanged; and
- replace only the product-detail recommendation widget with three
  server-rendered random active products from the same category.

This separation prevents a user-facing history feature from secretly changing
the meaning of the existing personalization-consent setting.

## 3. Main design decision: use the database

The user allowed session or database storage. MM-028 chooses the database.

Why:

- history remains available after closing and reopening the browser;
- the same account can see its recent products on another browser;
- the signed session cookie stays small and contains no product-history list;
- signing out and another user signing in on the same computer cannot mix
  histories; and
- one row per user/product makes duplicate handling straightforward.

The database stores only five product references and timestamps per user. It
does not store search terms, page duration, IP address, device details, clicks
inside the page, or anonymous browsing.

## 4. User stories

> As a signed-in shopper, I want to see products I recently opened so I can
> quickly return to something I was considering.

> As a shopper viewing a product, I want to see a few other active items in the
> same category so I can compare alternatives.

> As a user who has not enabled optional personalization, I still want the
> explicit Recently Viewed feature to work without enabling analytics-based
> recommendations.

## 5. Access rules

Recently Viewed:

- is recorded only for an authenticated user;
- is displayed only to that same authenticated user;
- never appears for anonymous visitors;
- never accepts a user ID from a URL, form or JavaScript body; and
- always uses `current_user.id` on the server.

Same-category suggestions:

- are public because product-detail pages are public;
- do not depend on login, history or personalization consent;
- contain public active listings only; and
- use the same result rules for every viewer.

## 6. What counts as a recent view

A recent view is recorded when all of these conditions are true:

1. the visitor is authenticated;
2. the normal public product page loaded an existing `active` product;
3. the page contains the existing same-origin view marker; and
4. JavaScript successfully sends the CSRF-protected view POST.

Opening an archived, missing or malformed product URL is not recorded. A sold
product remains viewable under existing rules but is not added to recent
history because it is no longer an available shopping choice.

Previewing a seller-owned listing through the private preview route is not a
public product view and is not recorded. If a seller deliberately opens the
public detail page for their own active product, it may be recorded like any
other active product.

Modified-link actions such as opening a product in a new tab still record after
that product page loads. Merely seeing a product card, hovering it, receiving
an AJAX search result, opening an image lightbox, or receiving a recommendation
does not count as a view.

JavaScript failure must not stop the product page from working. In that case,
history is simply not updated for that page load.

## 7. Database model

Add a `recent_product_views` table with:

| Column | Rule |
| --- | --- |
| `user_id` | Foreign key to `users.id`, part of the composite primary key |
| `product_id` | Foreign key to `products.id`, part of the composite primary key |
| `viewed_at` | Required UTC timestamp |

Required database rules:

- composite primary key `(user_id, product_id)` guarantees one current row for
  each user/product pair;
- an index beginning with `(user_id, viewed_at)` supports the five-item query;
- foreign keys prevent references to nonexistent users/products; and
- the Alembic migration upgrades and downgrades without touching existing
  product, order, cart, message, save or analytics rows.

The model will be imported through `app.models` so Flask-Migrate and tests can
discover it.

## 8. Ordering, deduplication and retention

Recent history contains at most five distinct products per user.

- First view: insert the `(user, product)` row with the current UTC time.
- Repeat view: update `viewed_at`; do not insert a duplicate.
- Sixth distinct view: keep the five newest rows and delete that user's older
  rows in the same transaction.
- Ordering: `viewed_at DESC`, then `product_id DESC` as a stable tie-breaker.

History for one account must never delete or reorder another account's rows.

Explore and Dashboard query the stored five rows and display only products
whose current status is still `active`. If a recently viewed product later
becomes sold or archived, it disappears from these sections. The underlying
bounded row may remain until a newer view replaces it; it is never shown as
available when it is not active.

Because status filtering can hide an item, a section may contain fewer than
five cards. It must not fill the gap using older deleted history, invented
products, or another user's activity.

## 9. Recording endpoint behavior

MM-028 extends the existing endpoint rather than adding a second browser call:

```text
POST /products/<product_id>/view
X-CSRFToken: <same-origin token>
Authentication: required
```

Behavior:

- `204` after recent history is recorded;
- `404` for a missing, sold or archived product;
- the endpoint body remains empty;
- the product ID comes only from Flask's integer route converter;
- CSRF and same-origin security remain required; and
- successful repeated calls are idempotent except for moving the product to
  the newest position.

After essential recent-history storage succeeds, the endpoint may continue to
call the existing consent-aware `record_event(..., "view")`. That optional
analytics event is created only when `current_user.personalization` is true.
Failure of optional analytics must not roll back successful recent history.

## 10. Explore Recently Viewed section

On `GET /products`, an authenticated user sees a section titled
**Recently Viewed** near the top of the page, before the main search results.

The section contains:

- zero to five ordinary reusable product cards;
- newest viewed product first;
- current image fallback, title, category, price, condition, seller and product
  link from the database; and
- the existing safe Add to Cart/Your listing behavior.

When there is no visible history, show a short empty message such as:

> Products you open will appear here.

Anonymous Explore pages contain no recent-history heading, query, identifiers
or placeholder.

AJAX search updates only the search-result grid and pagination. It must not
remove, duplicate or reorder the Recently Viewed section.

## 11. Dashboard Recently Viewed section

The private Dashboard receives the same ordered zero-to-five active products
and shows a **Recently Viewed** section after **Your recent listings** and
before **Recent conversations**.

It uses the same reusable card macro and the same empty-state sentence as
Explore. It does not replace:

- account statistics;
- the seller's recent listings;
- recent conversations; or
- the existing **Discover more** recommendation area.

Explore and Dashboard must show the same order when requested without an
intervening product view or status change.

## 12. Product-page “You might also like” section

For a valid active or sold product detail page, query up to three products that:

- currently have `status == "active"`;
- have the same category as the displayed product; and
- do not have the displayed product's ID.

Select candidates in random database order and limit the query to three. If
the category contains only one or two alternatives, show only those. Duplicate
products are forbidden.

The section is server-rendered with the existing product-card macro so it has
working images, seller links, prices, conditions, Add to Cart controls and
no-JavaScript behavior. Seller-authored text remains escaped by Jinja.

The section title remains **You might also like**. If no active alternative
exists, omit the complete section rather than displaying an empty grid.

MM-028 removes the product page's dependency on the JavaScript
`GET /recommendations?product_id=...` request. The public recommendations
endpoint and Dashboard **Discover more** continue unchanged for their existing
uses.

“Random” means different valid alternatives may appear on later requests; it
does not promise that every refresh must produce a different order.

## 13. Query and performance requirements

- Recent history is loaded with a bounded query of at most five active
  products for one user.
- Product and seller data needed by cards must be eager-loaded or otherwise
  bounded; no one-query-per-card pattern is allowed.
- Same-category selection performs one bounded query with `LIMIT 3`.
- Explore's existing paginated result query remains paginated and independent.
- Dashboard's existing bounded listings and conversation queries remain
  bounded.
- No endpoint loads every user's history or all marketplace products into
  Python to choose five or three items.

The project should retain reasonable query counts on the existing 1,000-row
hardening fixture.

## 14. Transactions and concurrency

Two tabs can report the same or different products almost simultaneously.
Implementation must:

- serialize recent-history updates for one user using the project's supported
  SQLite/PostgreSQL locking strategy;
- rely on the composite primary key as the final duplicate protection;
- update timestamps using timezone-aware UTC values;
- prune only after the insert/update is part of the same transaction;
- commit the essential history change before optional analytics work; and
- roll back cleanly on database errors.

After competing requests finish, one user has no more than five rows and no
duplicate product IDs. Exact ordering between genuinely simultaneous requests
may follow database commit/UTC ordering and the stable product-ID tie-breaker.

## 15. Privacy and security

- No anonymous history is stored.
- No history is placed in HTML data attributes beyond the public products
  intentionally rendered as cards.
- One user cannot request another user's history by changing a query string.
- Recently viewed rows are never sent to Gemini or another external provider.
- Logs must not list the user's viewed product IDs or titles.
- CSRF protects the view POST from cross-site history pollution.
- Archived/private listings never appear in recent or related sections.
- Normal HTML escaping, media authorization and trusted `url_for` links remain
  required.

Recent history is a direct account feature, not optional recommendation
profiling. The stored data is deliberately capped at five rows. The existing
personalization flag continues to control only analytics-based events and
profile recommendations.

## 16. Accessibility and responsive behavior

Both sections must:

- use a semantic `<section>` with a heading;
- keep a logical heading order;
- use real links and buttons through the existing card macro;
- retain visible keyboard focus;
- wrap safely at 320–360 px and 200% zoom;
- work above the mobile bottom navigation; and
- not rely on colour to explain empty state or product status.

Random related products must not be inserted after load in a way that causes a
surprise focus or layout shift. Server rendering satisfies this requirement.

## 17. Failure and edge cases

The implementation and tests must cover:

- no history yet;
- one through five distinct views;
- a sixth view pruning the oldest;
- viewing the same product repeatedly;
- separate histories for two users;
- user with personalization disabled;
- anonymous product visit;
- JavaScript disabled or view POST failing;
- invalid/missing/sold/archived product view POST;
- a recently viewed product changing to sold or archived;
- missing product image file;
- own active product viewed from the public detail page;
- concurrent duplicate/different view requests;
- no same-category alternatives;
- one or two alternatives;
- more than three alternatives;
- current product excluded from related results;
- sold/archived/private products excluded from related results;
- sold product detail page still suggesting active same-category alternatives;
- unrelated category never appearing in the related section;
- AJAX Explore search leaving the recent section intact;
- database/migration upgrade and downgrade; and
- optional analytics failure after successful history storage.

## 18. Expected later implementation files

After specification approval, PLAN-028 is expected to map work across:

- a `RecentProductView` model and model export;
- one Alembic migration;
- recent-history recording/query helpers;
- `app/engagement.py` for the view POST and Dashboard context;
- `app/marketplace.py` for Explore and same-category context;
- `catalogue.html`, `dashboard.html` and `product.html`;
- a small adjustment to the existing product view marker/JavaScript contract;
- focused pytest model, route, privacy, concurrency, migration, template,
  query-count and regression tests; and
- browser verification for desktop and mobile layouts.

No implementation file is authorized by this draft.

## 19. Acceptance criteria

| ID | Acceptance criterion |
| --- | --- |
| AC-028-01 | A successful authenticated active-product view POST inserts or refreshes one `(user, product)` recent-history row; anonymous, missing, sold and archived cases store nothing. |
| AC-028-02 | Each user retains at most five distinct rows, repeated views move an item to the front, the sixth distinct view removes only that user's oldest row, and concurrent calls create no duplicates. |
| AC-028-03 | Recently viewed storage works when optional personalization is disabled; consented `InteractionEvent` analytics retain their existing independent rules. |
| AC-028-04 | Signed-in Explore and Dashboard render the same newest-first zero-to-five active recent products with a clear empty state; anonymous Explore renders no recent-history section. |
| AC-028-05 | Sold/archived/missing recent products are not displayed, and no user can read or modify another user's history. |
| AC-028-06 | AJAX search updates do not remove or duplicate Explore's Recently Viewed section, and reusable cards retain safe image/cart/seller behavior. |
| AC-028-07 | A product detail page renders zero-to-three distinct random active same-category products, excluding the current product and every sold/archived/unrelated item. |
| AC-028-08 | Related products are server-rendered and fully usable without JavaScript; no-candidate state omits the whole section cleanly. |
| AC-028-09 | Dashboard's existing Discover more feature and public `/recommendations` endpoint remain functional; only product-detail recommendation behavior changes. |
| AC-028-10 | CSRF, login, UTC timestamps, transaction rollback, bounded retention, escaped output and generic logging protect the history endpoint. |
| AC-028-11 | Database migration upgrade/downgrade and SQLite/PostgreSQL-compatible constraints/indexes pass focused tests without changing existing data. |
| AC-028-12 | Keyboard, mobile, zoom, empty, missing-image and no-JavaScript states remain usable, and focused/full regression tests plus browser checks pass. |

## 20. Out of scope

MM-028 does not include:

- anonymous recently viewed history;
- browser local storage or a history cookie;
- more than five stored/displayed products;
- a full browsing-history page;
- a Clear History control;
- tracking time spent, hovers, lightbox opens or search impressions;
- personalized related products based on private history;
- Gemini-generated recommendations;
- replacing Dashboard Discover more;
- excluding related products because they were already viewed/saved/carted;
- guaranteeing a different random set on every refresh; or
- sending recent history to sellers or external services.

Any of these would require a separate approved specification.

## 21. Concepts to understand

### Composite primary key

The pair `(user_id, product_id)` is the row's identity. The same user cannot
have two history rows for the same product, but two different users can each
have their own row.

### Upsert-style behavior

The first view creates a row. Later views update its timestamp. In simple terms:
“insert if new; otherwise refresh.”

### Bounded retention

The application keeps only the five rows it needs. This limits database growth
and collects less personal activity data.

### Server-rendered recommendation

Flask selects and renders the related product cards before returning the HTML.
The section therefore works even when JavaScript is disabled.

### Race condition

Two browser tabs may update history at almost the same time. Database locks,
the unique key and one transaction keep the result valid even when request
timing overlaps.

## 22. SDD checkpoint

This document is the Specification stage only.

After the user explicitly approves **MM-028**:

1. create **PLAN-028** with implementation and test sequencing;
2. wait for explicit PLAN-028 approval;
3. write and demonstrate failing pytest contracts;
4. implement only after those tests are validated Red; and
5. run focused, related regression, migration and browser verification.

