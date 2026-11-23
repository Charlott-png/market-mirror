# MM-019 — Shopping cart and safe demo checkout

Status: APPROVED — user explicitly approved MM-019 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

## 1. Purpose and existing behaviour

Market Mirror users can currently browse product cards, open product pages, save products and contact sellers. This feature adds a separate shopping cart so a signed-in buyer can collect several active products, review them together, see a current subtotal and activate a Checkout button.

The cart is not the same as Saved products. **Saved** means “I may want to look at this later.” **Cart** means “I am currently considering these items together.” Saving or unsaving a product must not automatically add or remove it from the cart, and cart changes must not change Saved products.

This specification extends the existing application without removing MM-001 through MM-018, their documentation, generated product pictures, seller profiles, image lightbox, messages, recommendations or existing tests.

## 2. Important checkout interpretation

Market Mirror does not currently have payments, delivery addresses, taxes, shipping, orders, stock reservations, refunds or seller acceptance. Therefore, MM-019 defines Checkout as a **safe classroom demonstration**, not a real purchase.

When a valid signed-in buyer clicks **Checkout**, the server rechecks every cart item and displays a clear confirmation message such as:

> Demo checkout is ready. No payment was taken and no order was created.

The action must not collect payment or address information, mark products sold, create an order, reserve inventory, contact sellers, clear the cart or claim that a purchase succeeded. The cart remains unchanged so the user can continue demonstrating it.

This boundary prevents one visitor from removing another seller's product from the marketplace without a payment/order design. A future separately specified feature can add real orders and payment-provider integration.

## 3. Scope and data ownership

- The first version is an **account-based persistent cart**. A user must sign in to add, remove, view or check out cart items.
- The cart is stored in the database and remains available after signing out and signing in again on the same or another browser.
- Each cart belongs only to its user. A user must never read, change or check out another user's cart by changing a URL, form field, cookie or query parameter.
- Market Mirror products are individual marketplace listings, so a cart may contain each product at most once. MM-019 has no quantity selector.
- A buyer cannot add their own product.
- Only an active product offered by another enabled seller can be newly added.
- No anonymous/session cart, guest checkout, merge-after-login, discount code, shipping, tax, inventory quantity, payment, order history or seller notification is included.

## 4. Database requirements

Add a `cart_items` join table and migration with:

- `user_id`: required foreign key to `users.id`;
- `product_id`: required foreign key to `products.id`;
- `added_at`: required UTC timestamp; and
- a composite primary key or equivalent unique constraint on `(user_id, product_id)`.

The database constraint, not only the web form, must prevent duplicate cart rows. Foreign keys use the project's existing restrictive deletion policy so ambiguous account/product deletion cannot silently destroy purchase-related state.

Do not copy product title, picture, seller or price into the cart row. The cart displays the product's current public information and current price. This avoids stale duplicated data. The page must explain that prices shown are current and can change before a future real purchase system exists.

## 5. Functional requirements

### C-01 — Add to Cart on product cards

- Add an **Add to Cart** control to public cards for active products in the general catalogue, search results, Saved page and public seller profiles.
- Do not add it to the seller's private dashboard cards, because those cards represent the signed-in user's own listings and use owner-preview links.
- For a signed-in visitor viewing another seller's active product, use a POST form protected by the existing CSRF system.
- For an anonymous visitor, show a clear **Sign in to add to cart** link that returns them to the same safe local page after login. Anonymous GET requests must never mutate a cart.
- For a seller viewing their own public card, do not show an enabled Add control. Show short text such as “Your listing” when useful.
- Adding an eligible product creates exactly one cart row and redirects back to a safe local page with an accessible success notice.
- Adding the same product again is idempotent: the cart still has one row and the response explains that the item was already present rather than returning a server error.
- Forms and query parameters must not be allowed to choose a `user_id`, seller, price, status or redirect to an external site. The server takes the cart owner from `current_user` and reloads the product from the database.

### C-02 — Header cart icon and count

- Add a cart link to the main navigation for signed-in users on every normal HTML page.
- The link contains a recognizable cart icon plus visible text or an accessible name. Meaning must not depend on the icon alone.
- Display the total number of rows in the signed-in user's cart. Examples: `Cart (0)`, `Cart (1)`, `Cart (12)`.
- The count is derived from the authenticated user's cart rows on each request; it is not stored in a second counter field.
- The count must never include another user's rows and must update after successful add/remove requests.
- Anonymous navigation may show `Cart (0)` as a sign-in link or omit the cart link, but it must not reveal another user's count or create a guest cart. The implementation plan must choose one consistent presentation and test it.
- The navigation must wrap cleanly at 320 CSS pixels and keep a visible keyboard focus style.

### C-03 — Cart review page

- Create an authenticated `GET /cart` page with one H1 and a clear link back to browsing.
- Show each cart row in newest-added-first order.
- For an active product still offered by another seller, show its picture or existing placeholder, title, current price/currency, condition, seller link and product-detail link.
- Show the number of cart rows and a subtotal calculated from currently eligible active items using exact decimal/money arithmetic. Do not use binary floating-point arithmetic for money.
- With an empty cart, return HTTP 200 with a helpful empty-state message and no enabled Checkout button.
- The page may use pagination if the approved plan selects it, but every cart item must remain reachable and totals/counts must represent the full cart, not only the current page.
- Viewing the cart is read-only. GET must not delete stale rows, change product status, record a purchase or create analytics events.

### C-04 — Remove from cart

- Every cart row, including an unavailable placeholder, has a clearly labelled **Remove from cart** POST form protected by CSRF.
- The server deletes only a row whose `user_id` equals `current_user.id` and whose `product_id` matches the requested item.
- Repeating a removal is idempotent: the user's cart remains correct and no server error occurs.
- A GET request to a removal URL must return method-not-allowed and make no database change.
- Removing from the cart must not unsave a Saved product, change a listing or remove its image.

### C-05 — Products that become unavailable

A product can become sold or archived after it was added. A seller relationship or account can also become unavailable. The cart must handle this safely:

- Keep the cart row until the buyer removes it; a GET request must not silently mutate it.
- Do not expose archived product title, description, image, seller identity or price. Render a generic **Unavailable product** placeholder and a Remove button.
- A sold product may also use the same generic unavailable presentation for one consistent privacy rule.
- Unavailable rows still contribute to the navigation/cart row count because they remain in the cart, but they do not contribute to the payable/demo subtotal.
- Display a notice asking the user to remove unavailable items before checkout.
- If product status changes between page rendering and a POST, the server's fresh database check wins.

### C-06 — Safe demo checkout

- The Cart page contains a **Checkout** POST form protected by CSRF.
- Checkout is enabled only when the cart contains at least one item and every row still refers to an active product offered by another seller.
- On POST, reload or lock the relevant rows/products inside one transaction boundary and revalidate ownership, active status and seller difference. Never trust the earlier HTML, submitted subtotal, submitted count or client-side state.
- If the cart is empty, return a safe validation response and do not claim success.
- If any row is unavailable or otherwise ineligible, return HTTP 409 Conflict (or an equivalently documented validation result), show the refreshed cart and ask the user to remove unavailable items. Make no partial checkout claim.
- If every row is valid, show the demo-checkout confirmation specified in section 2 and the current item count/subtotal.
- Successful demo checkout leaves all cart rows and product rows unchanged. Repeated submissions remain safe and make no duplicate order/payment/message/event records because MM-019 creates none.

## 6. Security, privacy and reliability

- All mutations are authenticated POST requests with valid CSRF protection. GET requests remain read-only.
- Use parameterized SQLAlchemy queries and server-derived `current_user.id`.
- Reject or ignore forged `user_id`, price, quantity, seller, status, subtotal, return URL and checkout-success fields.
- Prevent open redirects. A post-login or post-add return destination must be a validated local path; otherwise use `/cart` or `/products`.
- Another user requesting or posting with a product ID from the victim's cart must not reveal whether the victim has that item. The attacker's cart is the only cart that may change.
- Cart pages must not expose email addresses, password hashes, messages, Saved-product state, interaction history, filesystem paths, CSRF values in logs or unavailable-product details.
- Adding a sold product returns a helpful validation error; adding an archived/nonexistent product uses a non-revealing 404 where appropriate.
- Handle competing duplicate Add requests by relying on the unique database constraint and safely rolling back/reloading rather than returning HTTP 500.
- Database failure during add/remove/checkout validation must roll back. Do not show a success notice after a failed commit.
- Do not add cart actions to recommendation cards created entirely by the current JavaScript in MM-014 unless a separate approved design brings those cards under the shared server-rendered card contract.

## 7. Accessibility and responsive behaviour

- Every Add, Remove and Checkout control has an accessible name that includes its purpose; repeated Remove controls should identify the corresponding visible product where practical.
- Success/error notices use the existing status/error patterns and do not rely only on colour.
- The cart icon is decorative when the adjacent text/accessibility label already provides meaning.
- Keyboard users can reach the cart link, product links, seller links, Remove controls, browse link and Checkout in a logical order with visible focus.
- Product images retain useful alt text; generic unavailable rows do not reveal hidden data in alt text or accessible names.
- The header count, rows, subtotal and Checkout area must reflow without horizontal page overflow at 320 CSS pixels and remain usable at actual 200% zoom when browser controls permit testing.
- Core cart operations are server-rendered and require no JavaScript. JavaScript may enhance presentation later but cannot be the only way to add, remove, count or check out.

## 8. Acceptance criteria and edge cases

| ID | Expected outcome |
| --- | --- |
| AC-019-01 | An eligible signed-in buyer adds an active product from a public card; one cart row exists and the header count increases by one. |
| AC-019-02 | Repeated and competing Add requests produce one row, no HTTP 500 and an accurate count. |
| AC-019-03 | Anonymous visitors are directed to sign in without mutation; a seller cannot add their own product. |
| AC-019-04 | A second account cannot see, count, remove or check out the first account's cart. Forged owner/price/status fields have no effect. |
| AC-019-05 | The Cart page shows eligible items newest-added-first, current prices, exact full-cart count and exact Decimal subtotal. |
| AC-019-06 | Remove is CSRF-protected, POST-only, user-scoped and idempotent; it does not affect Saved products or listings. |
| AC-019-07 | Sold/archived rows remain removable but reveal only a generic unavailable placeholder, remain in row count and are excluded from subtotal. |
| AC-019-08 | Empty cart returns 200 with a helpful message and cannot report checkout success. |
| AC-019-09 | Valid demo checkout rechecks all rows, clearly says no payment/order occurred and makes no database changes. |
| AC-019-10 | A status change immediately before checkout produces a conflict/validation response with no partial success or mutation. |
| AC-019-11 | Navigation count is present and correct throughout authenticated pages, never leaks across users and wraps accessibly on narrow screens. |
| AC-019-12 | Catalogue/search, Saved and public seller cards get the buyer control; private owner-dashboard cards do not. |
| AC-019-13 | Product cards, seller profiles, search, images/lightbox, saves, messages, recommendations and listing-status rules continue to pass their existing tests. |
| AC-019-14 | Cart pages and actions work without JavaScript, by keyboard and at 320 CSS pixels; actual zoom/dark-mode limitations are reported honestly. |
| AC-019-15 | Migration upgrade creates the constrained table on SQLite and PostgreSQL-compatible schema definitions; downgrade removes only MM-019 objects. |

Additional cases for the future test plan include nonexistent IDs, extremely large IDs, malformed/repeated parameters, Unicode/HTML-like titles rendered safely, missing images, carts with many rows, price changes after Add, disabled users, disabled sellers, stale sessions, database commit failures and direct endpoint requests that bypass buttons.

## 9. Out of scope

MM-019 does not include:

- real payment processing or card details;
- delivery addresses, shipping rates or taxes;
- orders, receipts, invoices, refunds or returns;
- inventory quantities, multiple units or reservations;
- seller acceptance, notification or automatic messages;
- automatically marking products sold;
- anonymous carts or merging a guest cart after login;
- coupons, wish-list synchronization or AI cart recommendations; or
- changing the existing meaning of Saved products.

These are intentionally excluded because each requires additional data, security rules and user expectations. They can be specified separately without weakening this cart foundation.

## 10. Beginner explanation

A cart is a **relationship** between a user and a product. The `cart_items` table is like a small list of pairs:

```text
user 7 → product 14
user 7 → product 23
user 9 → product 14
```

The pair is unique, so user 7 cannot accidentally have product 14 twice. User 9 can still have the same active product in their own cart because a cart is not a reservation.

The header number is **derived data**. Instead of storing a separate number that might become wrong, the application counts the signed-in user's cart rows. The subtotal is also derived from current eligible product prices using exact money arithmetic.

The server must check the product twice: once when it is added and again when Checkout is clicked. This is necessary because another person may change the product between those two moments. Never trust an old browser page when the database may have newer information.

## 11. Subsequent SDD stages

After this specification is approved:

1. Write PLAN-019 with exact files, migration design, routes, context-count strategy, templates, rollback and browser checks.
2. Wait for PLAN-019 approval.
3. Write pytest unit/integration/migration tests and the browser checklist before application implementation.
4. Run and record the expected Red checkpoint against unchanged application code.
5. Implement only the approved behaviour.
6. Run focused tests, the complete regression suite and real browser acceptance checks, then create a beginner guide and evidence.

No implementation, migration, test or template change is authorized by this specification alone.

## 12. Approval gate

Please review especially these three decisions:

1. the cart requires an account and persists in the database;
2. each marketplace product can appear only once and has no quantity control; and
3. Checkout is an honest, non-mutating classroom demonstration because real payment/order handling is outside MM-019.

The user replied **“I approve MM-019”** on 2026-11-02, approving the account-based persistent cart, one-entry-per-product rule and non-mutating demo checkout. The next SDD stage is PLAN-019. No test or application implementation is authorized until that plan is separately approved.
