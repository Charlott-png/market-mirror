# MM-020 — AJAX live search on Explore

Status: APPROVED — user explicitly approved MM-020 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

## 1. Purpose

The Explore page currently searches correctly after the visitor submits a normal
GET form. MM-020 adds **live search**: after the visitor types in the Search box
and pauses briefly, the result count, product grid and pagination update without
reloading the whole page. A small loading spinner shows while the newest search
request is waiting for the server.

This feature is a progressive enhancement. The existing form, URL parameters and
server-side search remain the source of truth. If JavaScript is disabled, blocked
or fails to load, the visitor can still press **Find products** and receive the
same results through an ordinary page load.

MM-020 extends the existing project without removing or changing MM-001 through
MM-019, product-card images, Add to Cart controls, seller links, Saved products,
recommendations, filtering, sorting or pagination.

## 2. Beginner definition of AJAX

AJAX means the browser can ask the server for a small piece of updated data
without replacing the entire page. The request is still handled by Flask and the
database. JavaScript only sends the search values and places the server's new
result fragment into the existing page.

The flow is:

```text
User types "laptop"
        ↓
Browser waits 300 milliseconds
        ↓
JavaScript sends a read-only GET request
        ↓
Flask validates the filters and searches the database
        ↓
Flask renders safe product-card HTML
        ↓
JavaScript replaces only the count, grid and pagination
```

The 300-millisecond pause is called **debouncing**. It prevents a database request
for every individual keystroke when someone types quickly.

## 3. Scope and chosen behaviour

- Live search applies only to the public **Explore** page at `/products`.
- Typing in the existing `q` field starts a search 300 milliseconds after the
  latest input event.
- The current category, condition, minimum price, maximum price and sort values
  are included in each live request, so typing does not discard existing filters.
- Every live search starts at page 1 because the previous page number may not
  exist for the new query.
- The result count, product grid and pagination are updated together as one
  consistent result.
- The address bar is updated with the validated search/filter query using
  `history.replaceState`, without adding one browser-history entry per letter.
  The resulting URL remains bookmarkable and shareable.
- The existing **Find products** button, Clear filters link and normal GET form
  continue to work. Changing a non-text filter does not have to search
  automatically in MM-020; the visitor may submit the form as before.
- Live search does not apply to the private dashboard, Saved page, seller
  profiles, cart, recommendations or listing editor.

## 4. Server contract

Add a read-only endpoint dedicated to the live result fragment:

```text
GET /products/search
```

It accepts the same allow-listed query parameters as `/products`:

- `q`
- `category`
- `condition`
- `min_price`
- `max_price`
- `sort`
- `page`

The endpoint must call the same shared validation and query-building code as the
ordinary Explore page. There must not be two independent definitions of search
visibility or matching behaviour.

On success it returns JSON with this conceptual shape:

```json
{
  "results_html": "server-rendered product cards or the empty state",
  "pagination_html": "server-rendered pagination links",
  "total": 4,
  "count_label": "4 products",
  "page": 1,
  "pages": 1,
  "canonical_query": "q=laptop&sort=newest"
}
```

`results_html` and `pagination_html` are rendered by Jinja from the same reusable
templates/macros used by the ordinary page. User-provided product text remains
auto-escaped. JavaScript must not build product cards by joining untrusted values
into HTML strings.

The endpoint returns `application/json`. It never changes database state, so it
uses GET and requires no CSRF token. Invalid or repeated parameters receive the
same safe 400-level validation outcome as the full Explore page, represented as
a small JSON error object without database details, stack traces or private data.

## 5. Client behaviour

### LS-01 — Initialization

- JavaScript activates only when the Explore search form, search input, result
  count, product-grid target, pagination target and status target all exist.
- If required elements or browser features are unavailable, it exits cleanly and
  leaves the ordinary form fully usable.
- The server-rendered initial page remains visible; JavaScript does not perform a
  duplicate request merely because the page loaded.

### LS-02 — Debounced typing

- An `input` event cancels the previous 300-millisecond timer and starts a new
  one.
- Empty or whitespace-only text is valid and loads the current filtered catalogue.
- Searches work with Unicode, punctuation and literal `%`, `_`, quote and
  HTML-looking characters under the existing MM-006 rules.
- During an Input Method Editor composition session, such as composing Chinese,
  Japanese or Korean text, intermediate characters do not trigger requests. The
  completed value searches after `compositionend`.

### LS-03 — Loading state

- When a request actually begins, show a small spinner and the accessible status
  text **Searching…**.
- The spinner is decorative; screen readers receive meaning from the text through
  a polite live region.
- Set `aria-busy="true"` on the results region while the newest request is active
  and restore it to `false` when that request finishes.
- The spinner is hidden when no search is active. Under
  `prefers-reduced-motion: reduce`, it remains visible but does not rotate.
- The existing results stay visible while loading to prevent the page from
  flashing or collapsing.

### LS-04 — Successful update

- Replace the result count, product grid and pagination only after a successful,
  valid response for the newest requested search.
- Preserve the search input's focus and caret; do not move keyboard focus to the
  grid after each letter.
- Product cards keep all existing server-rendered behaviour, including images,
  seller links, prices, accessible names and the correct Add to Cart/sign-in/own
  listing control.
- Announce a short result message such as **4 products found** through the polite
  status region, then allow the visible spinner to hide.
- A zero-result response shows the existing helpful **No products found** state,
  an accurate `0 products` count and no stale pagination links.

### LS-05 — Overlapping and stale requests

- Starting a newer search aborts the previous fetch when `AbortController` is
  supported.
- A monotonically increasing request identifier is also checked so a slow older
  response can never overwrite a newer result, even if aborting is unsupported or
  the old response was already completing.
- Only the newest request may hide the spinner, clear `aria-busy`, update the URL,
  replace results or announce completion.

### LS-06 — Failure and recovery

- For a network error, timeout-like failure, malformed response or safe server
  error, keep the last good results on screen.
- Hide the spinner, clear `aria-busy` and announce: **Live search is unavailable.
  Press Find products to search.**
- Do not display raw exception text, response bodies or stack traces.
- The ordinary form remains usable immediately after a live-search failure.
- A later input may retry; one failure must not permanently disable search.

## 6. Pagination and URLs

- The live response includes pagination rendered for the current validated query.
- Pagination links remain ordinary links. Clicking one may perform a normal full
  page navigation in MM-020; JavaScript pagination interception is not required.
- Each pagination URL retains validated `q`, filter and sort values.
- The AJAX-only endpoint itself must not become the address-bar URL. After a
  successful update, the browser displays the canonical `/products?...` URL.
- Unvalidated, repeated or unknown parameters are not copied into the canonical
  URL.
- The URL must not contain email addresses, CSRF tokens, internal paths or search
  implementation details.

## 7. Security and privacy

- Public live results include only products with `status == "active"`, exactly as
  the existing Explore page requires.
- Sold, archived, nonexistent and otherwise private listings never appear in
  cards, counts, pagination HTML, error text or timing-specific debug output.
- Queries use parameterized SQLAlchemy expressions and the existing escaped
  literal matching. Search text is never interpreted as SQL, regular expression
  code or executable HTML.
- Only allow-listed filters and sorts affect the query. Repeated supported
  parameters are rejected consistently; unknown parameters are ignored and not
  propagated.
- The response does not expose seller email, password data, messages, Saved state,
  cart ownership, filesystem paths, database errors or request headers.
- The endpoint is read-only, has no analytics mutation requirement and cannot be
  used to add to cart, save, contact a seller or change a listing.
- Add to Cart forms returned inside the server-rendered cards continue to contain
  the current session's valid CSRF protection. Cached fragments must never be
  shared across users in a way that leaks a token or displays another user's card
  state.

## 8. Accessibility and responsive design

- The existing visible Search label remains associated with the input.
- The status container uses a polite live region so typing is not interrupted by
  aggressive announcements.
- Loading, success and failure meaning never depends only on colour or animation.
- The spinner and status fit at 320 CSS pixels without horizontal page overflow.
- Keyboard users can keep typing while requests run and can still reach Find
  products, Clear filters, cards and pagination in a logical order.
- Replacing results must not unexpectedly scroll the page or steal focus.
- Repeated result announcements are concise and do not read every product card.
- The feature remains usable at 200% browser zoom when browser controls permit
  that check; any unavailable manual test is reported honestly.

## 9. Performance and reliability limits

- Debounce delay: 300 milliseconds after the latest completed input.
- At most one live request is considered current at a time.
- The endpoint keeps the existing fixed page-size limit; it does not return every
  matching product in one response.
- The implementation reuses eager loading and pagination so product cards do not
  create an avoidable seller-query-per-card pattern.
- The client does not cache responses in MM-020. This avoids stale listing status,
  price, cart-control and CSRF state.
- A response arriving after the user navigates away or the Explore targets are
  gone must cause no visible error.

## 10. Acceptance criteria

| ID | Expected outcome |
| --- | --- |
| AC-020-01 | Typing a query and pausing 300 ms sends a GET request and updates count, grid and pagination without a document reload. |
| AC-020-02 | Rapid typing is debounced; a slow older response cannot replace the newest results. |
| AC-020-03 | A visible small spinner, `Searching…` status and `aria-busy=true` appear while the newest request is active and clear afterward. |
| AC-020-04 | Existing category, condition, price and sort selections are included; a live query always begins on page 1. |
| AC-020-05 | Successful results use the normal cards with images, seller links and correct MM-019 Add to Cart/sign-in/owner controls. |
| AC-020-06 | Empty text and zero matches produce accurate catalogue/empty states with no stale cards or pagination. |
| AC-020-07 | Network/server/malformed-response failure preserves the last good grid, announces the fallback and leaves normal form submission working. |
| AC-020-08 | JavaScript disabled or unsupported leaves the existing GET form, filters, sorting and pagination fully functional. |
| AC-020-09 | The canonical `/products` URL updates only for the newest successful request and remains safe, validated, bookmarkable and shareable. |
| AC-020-10 | Unicode composition, literal wildcard characters, quotes, HTML-looking input, 120-character input and direct over-limit requests are handled safely. |
| AC-020-11 | Active-listing visibility and private-data rules match the ordinary Explore response exactly. |
| AC-020-12 | Keyboard focus/caret remain in Search; live announcements are concise; reduced motion and 320-pixel layouts remain usable. |
| AC-020-13 | No live request mutates products, carts, saves, messages, views or accounts. Existing features and the complete test suite continue to pass. |

## 11. Edge cases for the later test plan

The Planning and Testing stages must cover at least:

- one character, whitespace, empty text and exactly 120 characters;
- a direct 121-character query;
- emoji and non-Latin text;
- `%`, `_`, backslash, quotes, SQL-looking and `<script>`-looking text;
- repeated and invalid filter parameters;
- minimum price greater than maximum price;
- zero, one and more-than-one-page result sets;
- typing while on page 2;
- typing quickly enough to produce overlapping requests;
- an older request completing after a newer request;
- abort support present and absent;
- IME composition events;
- HTTP 400, HTTP 500-like safe response, rejected fetch and malformed JSON;
- input during a failed request followed by a successful retry;
- anonymous, signed-in buyer and product-owner card controls;
- a product becoming archived between two searches;
- missing product image fallback;
- JavaScript disabled;
- keyboard-only use, reduced motion, narrow viewport and available zoom checks; and
- browser console errors and accidental full-page reloads.

## 12. Out of scope

MM-020 does not add:

- autocomplete suggestions or a suggestion dropdown;
- fuzzy matching, typo correction, stemming or semantic/vector search;
- voice search;
- search history, recent-search storage or tracking analytics;
- automatic searching when non-text filters change;
- infinite scrolling;
- AJAX pagination;
- highlighting matched words inside cards;
- third-party search services;
- changes to product ranking; or
- live search on seller profiles, Saved, cart, dashboard or recommendations.

These can be specified separately. Keeping MM-020 focused makes it possible to
explain and test the core AJAX, debounce and race-condition concepts clearly.

## 13. Subsequent SDD stages

After this specification is approved:

1. Write PLAN-020 with the shared-query refactor, endpoint contract, reusable
   templates, JavaScript state machine, CSS changes, exact tests, browser checks
   and rollback strategy.
2. Wait for explicit PLAN-020 approval.
3. Write pytest unit/integration tests and browser acceptance checklist before
   application implementation.
4. Run and record the expected Red checkpoint.
5. Implement only the approved behavior.
6. Run focused tests, the complete regression suite and real browser acceptance,
   then write a beginner explanation and verification evidence.

No route, JavaScript, CSS, template or test implementation is authorized by this
specification alone.

## 14. Approval gate

Please review especially these decisions:

1. live search begins 300 ms after typing stops;
2. it reuses the existing secure server search and server-rendered product cards;
3. the ordinary form remains the no-JavaScript and failure fallback;
4. only typing in Search is automatic in MM-020; other filters keep their current
   submit-button behavior; and
5. pagination links remain ordinary full-page links in this first AJAX version.

The user replied **“I approve MM-020.”** on 2026-11-02. The next stage is
PLAN-020; implementation will still wait until that plan is separately approved
and the test definitions have been written and validated under the established
SDD workflow.
