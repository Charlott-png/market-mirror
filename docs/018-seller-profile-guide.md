# MM-018 beginner guide — public seller profiles

## What we built

Every seller now has a public page at `/sellers/<username>`. For example, the demo seller is available at `/sellers/demo-alex`.

The page shows:

- the seller's username;
- the date their account was created;
- their biography, or a friendly message when they have not written one;
- the total number of their active listings;
- their active products, newest first, with 20 products on each page; and
- a **Verified Seller** activity badge when they have at least four active listings.

The badge does not mean that Market Mirror checked the person's real identity. That is why the page also says, “Activity badge: this seller has at least 4 active listings. Identity has not been verified.”

## Why the feature is split into three parts

Think of a restaurant:

1. The **route** is the waiter who receives the request.
2. The **database query** is the kitchen ticket that says exactly what data is needed.
3. The **template** is the plate that presents the result to the visitor.

In `app/marketplace.py`, `seller_profile()` receives a username from the URL. It finds that user, asks the database only for products that belong to that user and have the status `active`, and prepares the badge and date values.

In `app/templates/seller.html`, Jinja turns those values into safe HTML. Jinja escapes the username and biography, so text such as `<script>` is displayed as text instead of being treated as a program.

In `app/static/css/style.css`, the seller-profile rules control appearance. The username and badge can wrap onto another line, which prevents a long name from pushing the page wider than a phone screen.

## The most important idea: derived data

Market Mirror does not save a separate `verified = true` value. Instead, it calculates the badge from current data every time the page is requested:

```text
has_activity_badge = active_listing_total > 3
```

This is called **derived data** because the answer is derived, or calculated, from other stored facts. It avoids stale information. If a seller has four active products and archives one, their total becomes three and the badge disappears on the next request. If the fourth product becomes active again, the badge returns.

The badge uses the same `total` value shown beside “Active listings.” This matters because two separate calculations could disagree.

## Why pagination does not change the badge

Pagination shows a small window into a larger result. A seller with 21 active products has:

- 20 cards on page 1;
- 1 card on page 2; and
- a total of 21 on both pages.

The badge uses the full total, not `len(items)` for the current page. Therefore, it remains present on page 2 even though page 2 has only one card.

## Join dates and UTC

The join date comes from the seller account's `created_at` value. The server converts it to UTC and prepares two versions from the same date:

- a human-readable label such as `29 February 2024`; and
- a machine-readable `<time datetime="2024-02-29">` value.

Using UTC makes the result stable. A visitor's timezone cannot accidentally move the account date backward or forward by one day.

## Privacy and read-only behaviour

The profile query includes two boundaries:

```text
product.seller_id == requested seller's ID
AND product.status == active
```

This prevents another seller's products and the requested seller's sold or archived products from appearing. The page does not show email addresses, password hashes, saved products, messages, or private activity. Opening it performs no database write.

## Small exercise

Use the automated tests or the isolated browser fixtures to compare these cases:

1. A seller with three active listings has no badge.
2. A seller with four active listings has the badge and explanation.
3. A seller with 21 active listings still has the badge on page 2.

Try explaining these three results in your own words. Then answer: why would saving a permanent badge flag be less reliable than calculating it from the active-listing total?

## What to demonstrate in class

1. Open a product such as **Silver laptop**.
2. Click the seller name **demo-alex**.
3. Point out the username, full join date, badge explanation and active-listing count.
4. Open one of the seller's product cards and show that the existing image lightbox still works.
5. Explain that the page is server-rendered and still contains all profile information when JavaScript is unavailable.

The strongest one-sentence explanation is: “The server finds one seller, queries only that seller's active products, derives the badge from the full count, and sends a safe HTML page to the browser.”
