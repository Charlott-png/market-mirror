# MM-018 — Public seller profile and activity-based badge

Status: APPROVED — user explicitly approved MM-018 on 2026-10-29 (Asia/Shanghai)

Date: 2026-10-29 (Asia/Shanghai)

## 1. Purpose and existing behaviour

Give marketplace visitors a clear public profile for a seller: username, join date, biography, that seller's available products, and a “Verified Seller” badge when the seller has more than three active listings.

This extends MM-007 rather than replacing earlier specifications. The application already provides `GET /sellers/<username>`, links seller names to it from product pages and cards, and renders a shared catalogue showing the seller's biography, join month/year and active products. The new work is to improve that presentation, show the full join date and add the exact badge rule. Existing context and documents must remain intact.

## 2. Scope and explicit interpretation

“All items the seller has listed” is interpreted as **all of that seller's currently active public listings**, across pagination, consistent with the approved MM-007 privacy/visibility rules. Sold and archived products remain excluded from the public seller catalogue. This specification does not expose private listing history or change the owner's management pages. If sold items should appear as a separate public history section, request that change before approving this specification; archived items must remain private.

The requested text “Verified Seller” will be used, but it means only that the account meets the active-listing count rule. It is not identity verification, a completed-sales milestone, an assessment of product quality, or a guarantee of safety.

No accounts, listings, uploaded photos, stored join dates or existing database schema will be changed. No external verification provider, payment, review system, messaging feature or deployment is included.

## 3. Functional requirements

### P-01 — Navigation and public access

- Keep the existing `/sellers/<username>` route and seller links on product detail pages and product cards. Clicking a seller's username must show that exact seller's profile, not the signed-in user's account page.
- A profile is readable without signing in. Signed-in owners and other visitors see the same public listing scope.
- Preserve the current case-insensitive username lookup and display the stored normalized username.
- A nonexistent username returns the existing friendly HTTP 404 page. Do not create an account or return another seller as a fallback.
- Provide a clear link back to browsing products. Ordinary keyboard navigation must work.

### P-02 — Profile header and join date

- Display the seller's username prominently as the profile heading, with any eligible badge directly beside it; allow natural wrapping on small screens.
- Show `Joined 29 October 2026` style text derived from that user's stored `created_at` value, not the first listing date, last edit date or current date. Interpret the stored timestamp in UTC for consistent display. Use a semantic `<time>` element with the corresponding ISO calendar date, such as `2026-10-29`.
- Retain the existing public biography. If absent, show a friendly no-biography message. Escape the biography and preserve readable line breaks.
- Clearly label the products section “Active listings” and show its total, with correct singular/plural wording.

### P-03 — Seller-specific product list

- Include only products whose `seller_id` matches the profile's seller and whose status is exactly `active`.
- List newest first, using product ID descending as a deterministic tie-breaker.
- Retain pagination at 20 products per page. All active products must be reachable through seller-scoped pagination, without mixing in another seller's products.
- Product cards retain existing pictures/placeholders, title, price/currency, condition and links to product detail pages. The MM-017 image lightbox must continue working on those detail pages.
- An existing seller with zero active listings receives HTTP 200, their profile details, and a seller-specific message such as “This seller has no active listings right now.” This is not a missing-profile error.
- Invalid page values (zero, negative, nonnumeric, excessively long or repeated `page` parameters) return HTTP 400. A positive page beyond the available range returns HTTP 404, except page 1 for an empty seller, which returns 200.
- Query parameters must not broaden the seller scope or include sold/archived products. No new search/filter controls are required.

### B-01 — Exact badge threshold

- Show the exact visible label **Verified Seller** beside the profile username when the seller has **more than 3 active listings**, meaning 4 or more.
- Zero, one, two or three active listings must not show the badge. Four must show it.
- Count only this seller's active products. Exclude sold and archived products, other sellers' products, saved-item counts, recommendations and sale history.
- Calculate eligibility from the full active-listing total, not the number of cards on the current page. A seller with 21 active listings still has the badge on page 2, even though that page contains only one card.
- Calculate the badge on the server from current database state. A visitor cannot obtain it by adding a query parameter or changing form fields.
- Do not store a separate verification flag or permanently grant the badge. After a change from four active listings to three, the next profile request must remove it; a change back to four restores it. No live page refresh/push is required.
- Use the same seller-scoped total for the displayed active-listing count and badge decision so pagination cannot make them disagree.

### B-02 — Explain what the badge means

- When the badge appears, include a nearby visible explanation: “Activity badge: this seller has at least 4 active listings. Identity has not been verified.” Equivalent clear wording is acceptable.
- Do not rely on colour, a check icon, hover-only tooltip or screen-reader-only text to convey its meaning. Icons, if used, are decorative and do not replace the label.
- This feature only adds the badge to the public profile header. Adding badges throughout catalogue cards and product pages is out of scope.

### S-01 — Privacy, accessibility and compatibility

- Never expose email addresses, password hashes, messages, saved items, browsing activity, personalization settings, private totals or filesystem paths.
- Use escaped template values and parameterized database queries. Do not render biography text as trusted HTML.
- Maintain existing media authorization, missing-image fallback and authentication rules elsewhere in the application.
- Keep the profile usable at 320 CSS pixels and 200% browser zoom, with visible keyboard focus and no horizontal overflow introduced by the header or badge.
- The page must work without JavaScript; this feature requires no client-side requests or new tracking.
- Viewing the profile is read-only. No database migration, identity check, automatic listing creation or external service call is required.

## 4. Acceptance criteria and edge cases

| ID | Expected outcome |
| --- | --- |
| AC-018-01 | Anonymous and signed-in users can follow a product's seller link to the correct public profile. |
| AC-018-02 | Header displays the correct stored username, full UTC join date and biography/fallback. |
| AC-018-03 | Every card belongs to that seller and is active; another seller's products and sold/archived products do not appear. |
| AC-018-04 | Active counts 0, 1, 2 and 3 have no badge; counts 4 and above have exactly one header badge with its explanation. |
| AC-018-05 | Sold/archived products do not contribute to eligibility, even when the seller's total product count exceeds 3. |
| AC-018-06 | A seller with 21 active items has two correctly scoped pages and the badge on both; ordering is deterministic. |
| AC-018-07 | A 4-to-3 active status change removes the badge on the next request; a return to 4 restores it. |
| AC-018-08 | Zero active products gives a helpful 200 profile; nonexistent seller and out-of-range page give 404; invalid/repeated page input gives 400. |
| AC-018-09 | UTC date boundaries render consistently; viewing or editing a listing does not change the displayed join date. |
| AC-018-10 | HTML-like biography text is escaped; unique email/hash/private-data markers are absent from the public response. |
| AC-018-11 | Fake `verified` or status/filter query parameters cannot change eligibility or reveal excluded listings. |
| AC-018-12 | Header, badge and cards remain readable on narrow screens and by keyboard; the page requires no JavaScript. |
| AC-018-13 | Existing catalogue, owner management, product detail/lightbox and media permission tests remain passing. |

## 5. Subsequent SDD stages

After specification approval, create a separate implementation and test plan. After plan approval, write pytest unit/integration tests using temporary databases and uploads, validate collection and expected missing-feature failures, then implement the page changes. Include threshold boundaries, pagination, transitions, escaping, privacy and date cases. Use actual browser checks for navigation and responsive/accessibility behaviour rather than claiming that Python HTML assertions prove the visual result.

Run the existing regression suite, save real evidence and document any unverified browser/device cases. Do not modify the user's real listings to manufacture test thresholds. No tests or implementation are claimed complete by this specification.

## 6. Beginner explanation

A public profile is a read-only view of one account's public information. The account table already stores when the user joined, and each product stores which seller owns it. The server uses that relationship to select the correct products.

The badge is **derived data**: we calculate it from other data rather than saving a separate value that could become outdated. The rule is simply `active_listing_count > 3`. Using the full count matters because pagination shows only a small slice of the seller's products at a time.

After implementation, a useful exercise is to compare two isolated test sellers with three and four active listings. Explain why the second gets the badge and why marking one of their items sold removes it. Then explain why this rule does not establish that the seller's identity has been checked.

## 7. Approval gate

The user replied **“I approve MM-018”** on 2026-10-29, approving the active-only public listing scope and activity-based badge explanation. The requirements above are unchanged. The next stage is PLAN-018, followed by tests and implementation under the existing SDD workflow. Application code remains unchanged at this stage.
