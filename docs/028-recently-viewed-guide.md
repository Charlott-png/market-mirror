# MM-028 Learning Guide: Recently Viewed and Related Products

## What you can demonstrate

When a signed-in shopper opens an active product, Market Mirror remembers that
product. Explore and Dashboard show the five most recently opened, different
products. Opening the same product again moves it to the front instead of
creating a duplicate.

The product page also shows up to three active alternatives from the same
category. For example, a camera may show a laptop or mouse because all three
are in Electronics. The current product is never one of its own alternatives.

## Why the database is used

A browser session is like a note kept in one browser for a short time. A
database is a more suitable notebook for this feature because history can
still be available after the user signs out and signs back in. Every history
row stores three facts:

- which user viewed the product;
- which product was viewed; and
- when that latest view happened.

The table uses `(user_id, product_id)` as a **composite primary key**. A normal
primary key identifies a row. A composite key uses two values together. This
means user 7 can have only one row for product 12, while user 8 may also have
their own separate row for product 12.

## How a view moves to the front

The first view inserts a row. A later view of the same product updates its
`viewed_at` time. The pages sort newest time first, so the updated product moves
to the front. This is often called **upsert-style behavior**: insert if the row
is new, otherwise update it.

After each successful view, the helper sorts the user's rows and removes every
row after the fifth. This is **bounded retention**. It keeps the feature fast,
limits database growth and avoids collecting more browsing activity than the
screen needs.

Example:

1. View Camera, Laptop, Mouse: `Mouse, Laptop, Camera`.
2. View Camera again: `Camera, Mouse, Laptop`.
3. View Jacket, Book, Lantern: `Lantern, Book, Jacket, Camera, Mouse`.
4. Laptop is now sixth-oldest, so it is removed.

## Why the page view uses POST

Loading a page with GET should normally only read information. Recording a
view changes the database, so JavaScript sends a small POST request after the
product page loads. The POST includes a CSRF token. CSRF protection helps stop
another website from secretly making a signed-in browser change Market Mirror
data.

If JavaScript is unavailable, the product page still loads and related cards
still appear, but the history is not changed. That is an honest fallback: the
main shopping information remains usable without pretending a POST happened.

## Privacy and current product status

The history query always includes the current user's ID, so one shopper cannot
receive another shopper's rows. It also checks that each product is still
active. If a seller sells or archives an item, that item disappears from the
visible Recently Viewed section even if an old history row still exists.

This feature does not depend on the optional AI-personalization setting. It is
a direct user-interface feature, not training data, and its five-row limit is
fixed. No recent-history information is sent to Gemini or to sellers.

## How related items work

Flask selects related products while building the product page. The database
query requires all of these rules:

- status is active;
- category equals the current product's category;
- ID is not the current product's ID; and
- at most three rows are returned.

The database randomizes eligible rows. Tests should not demand one exact random
order because a different correct order is allowed. Instead, tests check the
rules: correct category, active, unique, current product absent and no more
than three.

These cards are **server-rendered**, which means Flask puts them into the HTML
before sending the page. This is why they remain visible without JavaScript.

## Transactions and two tabs

A transaction groups database changes into one all-or-nothing operation. Two
tabs can report views at nearly the same time, so the helper uses the unique
composite key and a transaction to prevent duplicate history rows. It also
locks or serializes the user's update where the database supports it. The
result remains at most five distinct products.

## Files to explain in a presentation

- `app/models/activity.py`: defines the history table.
- `app/recently_viewed.py`: records, refreshes, sorts and prunes history.
- `app/engagement.py`: handles the protected view POST and Dashboard data.
- `app/marketplace.py`: supplies Explore history and same-category products.
- `app/templates/catalogue.html`: renders Explore's section.
- `app/templates/dashboard.html`: renders Dashboard's section.
- `app/templates/product.html`: renders related products and the view marker.
- `app/static/js/market.js`: sends the protected background POST.
- `migrations/versions/c28d0de02801_mm028_recent_product_views.py`: upgrades
  an older database safely.

## Small practice tasks

1. Predict the five-item order after viewing A, B, C, A, D, E and F.
2. Explain why `(user_id, product_id)` prevents a duplicate for one user but
   still lets two users view the same product.
3. Change one fixture product to archived and predict where it will disappear.
4. Explain why a random-related test checks rules rather than an exact title.
5. In your own words, explain why CSRF protection is needed on the view POST.

Suggested answers: task 1 ends `F, E, D, A, C`; task 3 removes the product from
visible history, Explore results and related candidates; task 4 has multiple
valid random outcomes.

## A short class explanation

“Market Mirror stores one recent-view row per user and product. A repeat view
updates the time, and a transaction keeps only the newest five. Explore and
Dashboard join those private rows back to active products. Product pages use a
separate server-side query for up to three active products in the same
category. Tests were written first, shown failing, and then the feature was
implemented until both focused and full regression suites passed.”
