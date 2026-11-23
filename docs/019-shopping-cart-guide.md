# MM-019 beginner guide — shopping cart

## What we built

Market Mirror now has a persistent shopping cart for signed-in users. A buyer can add products from public cards, see the number of cart rows in the navigation bar, review products and their current subtotal, remove products and click Checkout.

Checkout is deliberately a classroom demonstration. It checks that all products are still available and clearly reports that no payment was taken and no order was created. It does not mark a seller's product sold or empty the cart.

## Why a cart needs a new table

The cart is a relationship between a user and a product. The `cart_items` table stores pairs:

```text
user_id | product_id | added_at
--------+------------+--------------------
7       | 14         | 2026-11-02 10:00Z
7       | 23         | 2026-11-02 10:04Z
9       | 14         | 2026-11-02 10:08Z
```

User 7 and user 9 may both add product 14 because a cart is not a reservation. The pair `(user_id, product_id)` is the table's primary key, so user 7 cannot have product 14 twice.

This is a **join table**: it joins records from two other tables without copying the product's title, price or seller. When the cart is opened, Market Mirror reads the product's current information.

## Add-to-Cart flow

When a signed-in buyer presses Add to Cart:

1. The browser sends `POST /cart/items/<product_id>` with a CSRF token.
2. The server gets the buyer ID from the signed-in session—not from the form.
3. It reloads the product and checks that it is active, belongs to another user and has an enabled seller.
4. It tries to insert the `(buyer, product)` pair.
5. The database's composite primary key prevents duplicates, including two almost-simultaneous requests.
6. The server commits and redirects to a validated local page with a status message.

Anonymous visitors receive a Sign in to add to cart link. The earlier click is not silently replayed after login because that would perform a state change the user may no longer expect.

## The navigation count

The number beside the cart icon is **derived data**:

```text
COUNT(cart_items) WHERE user_id = signed_in_user
```

Market Mirror does not save a second `cart_count` column. A second stored number could become stale after an error or competing request. Counting the authoritative rows after each redirect keeps it accurate.

The value is cached only for the current request and current user. It is recalculated on the next page request, and one user can never receive another user's cached count.

## Reviewing the cart

`GET /cart` loads only rows belonging to the signed-in user. The page shows 20 rows at a time, newest added first. The count and subtotal still represent the complete cart, not only the visible page.

Eligible products display their current:

- picture or missing-photo placeholder;
- title and detail link;
- price in USD;
- condition; and
- seller profile link.

The subtotal uses Python's `Decimal` money values. Computers cannot represent some decimal fractions exactly as binary floating-point numbers. With ordinary floats, `0.10 + 0.20` may behave like `0.30000000000000004`. Decimal arithmetic gives the expected `$0.30`.

## Products that become unavailable

A seller may mark a product sold or archived after a buyer adds it. Opening the cart must not silently delete that row because GET requests should be read-only.

Instead, the page shows a generic Unavailable product row. It deliberately hides the old title, price, picture and seller so an archived listing cannot leak through the cart. The row remains in the cart count but is excluded from the subtotal. The buyer can remove it with a CSRF-protected POST form.

## Why Checkout checks everything again

The browser page is only a snapshot. A product can change after the page loads, so the server never trusts the displayed status, count or subtotal.

When Checkout is pressed, the server reloads the complete cart and every product:

- empty cart → validation error;
- any unavailable product → conflict message with no partial success;
- every product eligible → demo confirmation.

All paths leave products, cart rows, Saved products, messages and events unchanged. This is called **server-side revalidation**.

## Security rules to remember

- The user ID always comes from `current_user`.
- Add, Remove and Checkout are POST-only and require CSRF tokens.
- Every query and delete includes the signed-in user's ID.
- Hidden form fields are not trusted for price, seller, status, subtotal or ownership.
- Redirect destinations are checked to keep them inside Market Mirror.
- Generic unavailable rows prevent private archived data from leaking.
- Database failures roll back and never display a false success message.

## Main files

- `app/models/activity.py`: `CartItem` database model.
- `migrations/versions/f19c7a42e0b1_mm019_cart_items.py`: database upgrade and downgrade.
- `app/cart.py`: eligibility, Add, Remove, review and demo Checkout.
- `app/templates/macros.html`: card controls.
- `app/templates/base.html`: navigation icon and count.
- `app/templates/cart.html`: cart review page.
- `app/static/css/style.css`: responsive cart layout.
- `tests/test_cart.py`: feature and security contracts.
- `tests/test_cart_migration.py`: migration contracts.

## Demonstration steps

1. Sign in as a buyer.
2. Add two different public products and watch the header count increase.
3. Add one of them again and explain why the count does not increase.
4. Open Cart and calculate the subtotal by hand.
5. Remove one product and confirm the count/subtotal update.
6. Click Checkout and read the no-payment/no-order explanation.
7. Reload Cart and show that Checkout did not clear the rows.

## Practice question

Two buyers add the same product. Then the seller marks it sold.

Explain why both cart rows are allowed, why neither cart reserved the product, why both rows become generic unavailable placeholders, and why Checkout must use current database information instead of the older browser pages.

The strongest short explanation is: “A cart is a user–product relationship; the server scopes every operation to the signed-in user, derives counts and totals from current data, and revalidates availability before any checkout result.”
