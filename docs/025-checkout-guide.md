# Understanding Market Mirror checkout

MM-025 turns the old Checkout demonstration into a real **local database
transaction**. It records a purchase inside Market Mirror, but it does not move
real money or arrange delivery.

## What happens when Checkout is clicked?

The server does not trust prices or product IDs sent by the browser. It opens
the buyer's cart from the database again and checks every product. If all items
are still active and unchanged, it performs four jobs together:

1. creates one `Order`;
2. creates an `OrderItem` line for every product;
3. changes every product from Active to Sold; and
4. removes the buyer's purchased cart rows.

The database commits those jobs as one unit. The browser is then redirected to
the private **Thank you for your purchase** page.

## Order versus OrderItem

Think about a paper receipt from a shop:

```text
Order #42 — buyer, date, total
    ├── Laptop — $450.25 — laptop-seller
    └── Camera — $79.45 — camera-seller
```

The top part is the `Order`. Each printed line is an `OrderItem`. This is called
a **one-to-many relationship**: one order can have many items.

## Why save snapshots?

An order item copies the product title, seller username and price that were
true at checkout. These copies are called **snapshots**. They make the receipt
historically honest even if current marketplace information changes later.

It does not copy private email addresses, passwords, messages, descriptions or
photos.

## Why money is not a float

Computers store ordinary floating-point numbers approximately. For example,
`0.10 + 0.20` can internally look like a number slightly different from 0.30.
That is unsafe for money.

Market Mirror uses Python `Decimal` values. SQLite stores those values as whole
cents, so $12.50 is stored as `1250`. The order tests specifically prove that
$0.10 + $0.20 becomes exactly $0.30.

## What is a transaction?

A **transaction** is an all-or-nothing box around several database changes.
Imagine the server crashes after marking a laptop Sold but before writing its
order. Without a transaction, the data would be confusing.

With a transaction, Market Mirror either finishes every checkout change or
performs a **rollback**, returning the database to its earlier state.

## What is a signed checkout token?

Users can edit hidden browser fields, so hidden does not mean trusted. Market
Mirror creates a token containing:

- the buyer's ID;
- a random checkout number; and
- a fingerprint of the current cart.

The server signs this data with its private application secret. Editing the
token breaks the signature. The fingerprint also changes when the cart, product
version or price changes, so the buyer must review an updated cart instead of
silently buying at a different price.

The token expires after 30 minutes. It contains no product title, username or
email address.

## Why double-clicking is safe

The random checkout number is also stored on the order. The database permits
only one order with the same buyer and number. If the browser repeats the same
request, Market Mirror shows the existing receipt. This property is called
**idempotency**.

## What if two buyers want the same item?

Requests can overlap; this is called **concurrency**. Market Mirror carts do not
reserve products, so two buyers may have the same listing in their carts.

During checkout, the server locks and rechecks products in a stable order. The
database also allows a product to appear in only one `OrderItem`. Therefore at
most one buyer wins. The losing checkout receives a conflict message and keeps
its cart for review; it never gets half an order.

## Try the automated tests

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py -q --basetemp=.pytest-tmp\checkout-guide
```

These tests create temporary databases. They do not purchase your demo items.

## Inspect orders in the Flask shell

After intentionally completing a local demo checkout, stop the server and run
the Flask shell through the same local environment. Query `Order` and
`OrderItem`; do not manually edit them. The models are included in the shell
context for explanation during a university demonstration.

## Important limitation

“Purchase complete” means that the local class-project database recorded the
transaction. Market Mirror does not collect card details, call Stripe or
PayPal, calculate shipping/tax, pay a seller, send a receipt email, or promise
delivery. Those are separate, security-sensitive projects.
