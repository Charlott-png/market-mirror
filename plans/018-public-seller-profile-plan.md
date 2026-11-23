# PLAN-018 — Public seller profile: implementation and test plan

Status: APPROVED — user explicitly approved PLAN-018 on 2026-10-29 (Asia/Shanghai)

Date: 2026-10-29 (Asia/Shanghai)

Approved specification: MM-018, explicitly approved by the user on 2026-10-29.

## 1. Outcome and boundaries

Upgrade the existing public seller route with a dedicated profile header, full UTC join date, biography, active-listing total and activity-based “Verified Seller” badge at four or more active listings. Retain the existing seller-name links, 20-item pagination, newest-first ordering and public visibility rules.

Only documentation changes at this stage. After plan approval, write and validate tests before modifying the application. Do not create listings or change real account data to demonstrate the badge. No database migration, stored verification flag, package installation, identity-verification service or JavaScript change is planned.

## 2. Planned files

| File | Responsibility |
| --- | --- |
| `app/marketplace.py` | Extend `seller_profile()` to reject repeated page parameters, obtain the seller-scoped pagination result once, derive badge eligibility and prepare UTC join-date display values. |
| `app/templates/seller.html` | New dedicated public profile template, using the existing base layout and product-card/pagination macros. |
| `app/static/css/style.css` | Small seller-profile-specific header and badge rules, including wrapping, focus and light/dark readability. |
| `tests/test_seller_profile.py` | New pytest coverage for badge boundaries, pagination, visibility, dates, escaping, read-only behaviour and navigation. |
| `tests/018-browser-checklist.md` | Browser acceptance scenarios defined before application implementation. |
| `tests/018-red-verification.md` | Test collection and initial expected-failure evidence. |
| `tests/018-green-verification.md` | Focused, regression and browser results, including explicit limitations. |
| `docs/018-seller-profile-guide.md` | Beginner explanation and a small learning exercise. |
| `docs/evidence/018-*` | Actual desktop/narrow profile screenshots, using the image format returned by the browser. |

The shared catalogue template and card/pagination macros need no new behaviour. Existing profile links in product pages/cards already point to the right endpoint and should remain unchanged unless tests reveal a defect. Do not remove historical documents or unrelated template branches as cleanup. A disposable test-only browser fixture helper may be added under `tests/` if needed; it must not be registered in the real application.

## 3. Request and data flow

### 3.1 Reuse the public route

Keep `GET /sellers/<username>` and the endpoint name `market.seller_profile`. Look up the stored normalized username using the existing case-insensitive lookup. A nonexistent seller still returns 404. This is not an authenticated dashboard: do not add `login_required` or substitute the current signed-in user for the requested seller.

For an existing seller, reject more than one `page` parameter with a helpful 400 response. Keep the existing `page_number()` validation for malformed/zero/negative/overlong page values and `paginate()` handling for out-of-range pages. Put the duplicate check in this route, rather than changing pagination behaviour across unrelated features.

### 3.2 One scoped total, two uses

Build the existing product query with both required conditions:

```text
product.seller_id equals the profile seller's ID
AND product.status equals active
```

Order by creation time descending, then ID descending. Call `paginate()` once and keep its returned dictionary. Use its `total` for both the displayed active-listing count and `has_activity_badge = total > 3`. Pass the page's `items`, `page`, `pages` and `total` to the dedicated template.

Do not calculate the badge with `len(items)`, because that is just one page. Do not count all products then subtract statuses in Python. Do not introduce a second independent badge-count query or load every seller product into memory. Reuse existing relationship loading or eager-load the seller for cards if needed to avoid extra per-card lookups.

The count and page rows use the existing pagination mechanism; this feature does not promise a cross-request snapshot while another user changes listings. The header count and badge decision must come from the same count result on each render. A subsequent request recalculates eligibility.

### 3.3 Prepare a stable join date

Use `seller.created_at`, normalized explicitly to UTC, then take its calendar date. The existing UTCDateTime model adapter already normalizes stored timestamps on reading. Derive both a machine-readable ISO date and the human-readable `day month year` label from the same date.

Avoid Windows-incompatible day-format flags such as `%-d`. Use the numeric day directly and an explicit English month-name mapping, or another platform-independent equivalent, so the visible result remains predictable regardless of the host's locale. For example, a stored instant corresponding to 28 October in UTC must display 28 October even if it is already 29 October in another timezone.

No fallback to today's date or listing creation time is allowed. The existing model requires a join timestamp; unexpected corrupt data should not silently invent a date.

## 4. Template and styling design

The new template extends `base.html` and imports `card` and `pagination` with context. Its content has:

1. A “Browse products” link.
2. A profile header containing one H1 with the username and an adjacent conditional badge.
3. A `Joined <time datetime="YYYY-MM-DD">…</time>` line.
4. The escaped biography or existing friendly fallback.
5. When eligible, a visible explanation: “Activity badge: this seller has at least 4 active listings. Identity has not been verified.”
6. An “Active listings” H2, the full total with correct singular/plural text, the existing product cards, and seller-scoped pagination.
7. For an empty seller, a specific no-active-listings message while retaining the profile header and join date.

Only the profile header receives the badge. Do not add it to each product card or to the general marketplace. Render a real text label, not just a coloured icon. Avoid animation and hover-only information. Give the badge/explanation stable semantic hooks for precise tests, without testing the whole page by counting words that could also occur in a seller's biography.

Use scoped class names, a wrapping flex header, `min-width: 0` and appropriate word wrapping for long usernames/biographies. Reuse existing theme variables where they provide readable contrast. The header must not push the page wider than a 320-pixel viewport. No client-side data fetching or new tracking is necessary; the server delivers the complete profile HTML.

## 5. Test-first execution order

1. Obtain PLAN-018 approval.
2. Write the focused pytest cases and browser checklist using isolated fixtures.
3. Run test collection, then run the focused suite against unchanged application code.
4. Record the Red results: expected missing full-date/profile-header/badge/duplicate-page behaviour must fail for the intended reason. Existing access/visibility tests may already pass. Import errors or broken fixtures are not a valid feature Red checkpoint.
5. Implement the minimal route, template and CSS changes.
6. Run the focused suite, resolve failures without weakening required assertions, then run the complete regression suite including MM-017 lightbox checks.
7. Run browser checks on isolated fixtures. Use the real local demo site only for read-only navigation/visual confirmation; do not alter live data for badge thresholds.
8. Save screenshots, verification results and the beginner guide. Identify anything not verified rather than treating source inspection as a browser pass.

Commands to be run by the assistant from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_seller_profile.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_seller_profile.py -q --basetemp=.pytest-tmp\mm018-red
.\.venv\Scripts\python.exe -m pytest tests\test_seller_profile.py -q --basetemp=.pytest-tmp\mm018-green
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm018-regression
```

These specific temporary paths are owned by pytest and may be cleared when reused. Never point `--basetemp` at real uploads, the instance folder or a directory containing user work.

## 6. Pytest coverage matrix

Reuse `db_app`, `client`, `db_session`, `user_factory` and `product_factory` from the existing fixtures. Create distinct sellers and product titles so accidental cross-seller exposure is detectable. Parse HTML with the standard library where practical; avoid new dependencies or brittle whole-document string comparisons. Assert the rendered badge element and its explanation, not a bare occurrence of “Verified Seller” anywhere in user-supplied text.

| Test group | Required cases and assertions | Spec |
| --- | --- | --- |
| Public navigation | Follow the actual seller href from a product response; confirm requested seller header. Check anonymous, owner and unrelated signed-in visitor. Confirm upper-case URL lookup resolves to normalized stored username. | AC-018-01 |
| Join date | Assert visible date and `<time datetime>` agree with fixed stored `created_at`. Cover leap day, UTC midnight boundary, and a timezone-offset input that normalizes to a different UTC day. Reload the saved user to test persisted timestamp behaviour. | AC-018-02, 09 |
| Date immutability | Edit an isolated listing through the supported flow, reload profile, and assert account join date is unchanged. Do not change account `created_at` to simulate the edit. | AC-018-09 |
| Badge boundary | Parameterize active totals 0, 1, 2, 3, 4 and 5. Below four: no badge/explanation elements. Four or more: exactly one header badge with correct text and visible explanatory markup. | AC-018-04 |
| Count isolation | Add another seller's active listings and this seller's sold/archived products. Assert neither contributes to displayed total or eligibility, nor appears as a public card. | AC-018-03, 05 |
| Pagination | Create 21 active products plus excluded products. Assert 20 cards on page 1, one on page 2, all unique and seller-owned, total 21 and badge on both pages, correct previous/next seller URLs. | AC-018-06 |
| Stable ordering | Use mixed creation timestamps and ties. Compare exact product IDs in card order against timestamp-descending/ID-descending expectations. | AC-018-06 |
| Dynamic badge | Start with four active products. Use the owner's status endpoint to archive one: next request shows three and no badge. Reactivate it through the supported archived-to-active transition: next request shows four and the badge. Separately verify marking a product sold removes it from the active count. Do not bypass the prohibition on sold-to-active transitions. | AC-018-07 |
| Empty and missing | Existing empty seller: 200, profile information and seller-specific empty message. Missing seller: 404. Page 2 for empty seller: 404. | AC-018-08 |
| Page validation | Test `page=0`, `-1`, empty, nonnumeric, decimal, non-ASCII digits, over-eight-digit input and repeated page parameters. Each returns 400 for an existing seller. A valid but unavailable page returns 404. | AC-018-08 |
| Query tampering | Requests such as `?verified=true&status=archived&seller_id=...` do not alter eligibility or listing scope. The page does not gain unapproved search/filter behaviour. | AC-018-11 |
| Biography and privacy | Missing/blank biography fallback; escaped multiline HTML-like biography. Seed distinctive email/hash/private-content canaries and assert their absence. A biography containing badge wording must not fool badge-element assertions. | AC-018-02, 10 |
| Read-only rendering | Snapshot relevant test rows before/after profile GETs; no user/product changes or extra activity records. | AC-018-13 |
| Cards and regressions | Existing card URLs, price/currency and missing-image placeholder remain correct. Catalogue and owner pages do not acquire the public profile header/badge. Existing media-permission and lightbox tests remain passing. | AC-018-12, 13 |

The main rule is small enough to test through the route; a new helper abstraction is not required solely to create a unit-test target. If date-formatting logic is extracted for clarity, add focused unit tests for it in addition to the rendered-response assertions.

## 7. Browser checks and evidence

Define these in `tests/018-browser-checklist.md` before implementation:

- Open a product, activate its seller link and verify the destination username, join date and seller-owned cards. Return using the browse link.
- Compare isolated three-active and four-active sellers. Verify badge absence/presence and that the explanation is visibly readable beside/below the header, not hidden in a tooltip.
- Visit both pages of a 21-item fixture; the second page must retain the badge and full count even though only one card appears.
- Check empty seller and missing-photo fixtures without errors or broken card layout.
- Check desktop and 320-pixel width, long usernames and multiline biographies, plus light/dark mode and actual 200% browser zoom when the browser controls support them. Do not label resizing as a zoom test.
- Use Tab/Enter to follow seller, product, browse and pagination links; confirm focus is visible.
- Verify the server-rendered profile remains usable with JavaScript unavailable, through a controlled no-script fixture if necessary; disclose a simulation rather than claiming a browser preference was changed.
- Follow a profile product link and open/close its existing MM-017 lightbox as a regression smoke check.
- Inspect for new browser errors. Save desktop and narrow-screen screenshots showing the profile header, badge meaning and at least one listing when possible.

Any fixture server must bind only to loopback, use a temporary or in-memory database and separate uploads, and be stopped after use. Do not log in to or edit real accounts to generate evidence. The server fixture must not add test-only endpoints to normal application startup.

## 8. Main risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Badge suggests identity verification | Always pair the requested label with the explicit activity-only explanation. |
| Off-by-one threshold (`>= 3`) | Tests on both three and four; implement `total > 3`. |
| Badge disappears on a small final page | Derive from the pagination total, never the current card count. |
| Sold, archived or another seller's products leak | Keep both seller-ID and active-status conditions in the same query; use canary products in tests. |
| Verification becomes stale | No stored flag or permanent grant; recompute on every profile request. |
| Wrong join day on Windows or timezone boundary | Normalize to UTC and use portable, deterministic formatting with fixed-date tests. |
| Shared catalogue changes break other pages | Use a dedicated seller template and existing macros; keep general catalogue behaviour unchanged. |
| Duplicate query parameters are interpreted inconsistently | Reject repeated `page` values locally before pagination. |
| Long text breaks the mobile header | Wrap username/badge and test narrow layouts; do not rely on truncation to hide content. |
| Tests alter demo data | Use existing isolated fixtures, never the live database or upload folder. |

## 9. Completion and learning handoff

Completion requires a recorded Red checkpoint, passing focused tests and the full regression suite, and real browser evidence for core navigation, badge display and narrow-screen behaviour. Report unresolved failures and unverified optional environment checks explicitly. No existing test pass count is a promised result until the new runs actually finish.

Deliver changed-file links, actual results, screenshots and a beginner guide explaining the route/query/template relationship. Explain **derived data** with the badge rule and **pagination** as a window onto a larger result set. Include this exercise: compare isolated sellers with three and four active listings, then explain why a seller with 21 active listings is still eligible on page 2.

If a rollback is needed, reverse only this feature's route/template/style edits. No database recovery should be necessary because this feature does not change stored records or schema. Preserve previous code, documents and generated pictures.

## 10. Approval gate

Reply **“I approve PLAN-018”** to authorize the test-first sequence: tests and validated Red results, then implementation and verification. No tests have been written or run for MM-018 yet, and no application code has changed at this planning stage.
