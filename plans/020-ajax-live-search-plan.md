# PLAN-020 — AJAX live search on Explore

Status: APPROVED — user explicitly approved PLAN-020 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

Approved specification: MM-020, explicitly approved by the user on 2026-11-02.

## 1. Outcome and boundaries

Implement a progressively enhanced live search on the public Explore page. After
the visitor types in Search and pauses for 300 milliseconds, JavaScript sends a
read-only request to Flask and replaces the result count, product grid and
pagination without reloading the document. A small spinner and accessible status
message communicate the current state.

The ordinary GET form remains the fallback and the authoritative search rules
remain on the server. MM-020 does not change the database schema, add a package,
introduce a JavaScript framework, create search analytics or make non-text filters
automatic. Pagination links continue to use normal page navigation.

The project remains local, as previously chosen. The Sites workflow therefore
influences responsive/accessibility/browser checks but does not register, package
or publish this existing Flask application.

## 2. Planned files and responsibilities

| File | Planned change |
| --- | --- |
| `app/marketplace.py` | Extract one shared public-search parser/query helper; keep `/products`; add `GET /products/search`; build canonical validated query data; return safe JSON and no-store headers. |
| `app/templates/catalogue.html` | Add stable Explore-only hooks for the form, input, loading/status area, result count, grid and pagination; include reusable partials while preserving the form fallback. |
| `app/templates/_product_grid.html` | Render normal shared cards or the existing empty state for both full-page and AJAX responses. |
| `app/templates/_catalogue_pagination.html` | Render the existing pagination macro with links targeting canonical `/products`, including when invoked by the AJAX endpoint. |
| `app/templates/macros.html` | Allow the pagination macro to receive an optional endpoint while keeping every existing default call unchanged. |
| `app/__init__.py` | Extend `page_url` with an optional endpoint argument so AJAX-rendered pagination links point to `/products`, not `/products/search`. |
| `app/static/js/market.js` | Add one isolated live-search controller: debounce, IME handling, request cancellation/sequence checks, spinner/status management, safe fragment replacement, URL replacement and fallback errors. |
| `app/static/css/style.css` | Add scoped feedback/spinner/visually-hidden rules, reduced-motion handling and narrow-layout protection. |
| `tests/test_live_search.py` | Add server contract, parity, privacy, escaping, card, URL, validation, no-mutation, template-hook and fallback tests before implementation. |
| `tests/020-browser-checklist.md` | Define real-browser behavior before implementation, including debounce, loading, race, failure, focus, no reload and responsive checks. |
| `tests/020-red-verification.md` | Record collection and expected failures against the unchanged application. |
| `tests/020-green-verification.md` | Record focused, full-regression and browser results plus honest tooling limitations. |
| `tests/preview_live_search.py` | Optional loopback-only fixture with temporary data and controlled slow/error responses for deterministic browser checks. |
| `docs/020-ajax-live-search-guide.md` | Explain AJAX, debounce, race conditions, progressive enhancement and accessibility at a high-school level. |
| `docs/evidence/020-*` | Store desktop/narrow screenshots only after real browser verification. |

No migration or model file changes are planned because live search does not store
new data.

## 3. Shared server-search refactor

### 3.1 One source of truth

The current `browse()` route already implements the correct MM-006 rules. Move
only that parsing/query work into a private helper such as
`build_browse_context()` instead of copying it into the AJAX route.

The helper will:

1. allow only one value for each supported parameter;
2. trim and limit `q` to 120 characters;
3. escape `\\`, `%` and `_` for literal `ILIKE` matching;
4. validate category and condition against their existing allow-lists;
5. parse minimum/maximum prices with exact existing money logic;
6. reject a minimum greater than a maximum;
7. allow only `newest`, `price_asc` and `price_desc` sorting;
8. always begin from `Product.status == "active"`;
9. eager-load the seller needed by cards;
10. paginate with the existing fixed page size; and
11. return validated canonical arguments as well as the normal `items`, `total`,
    `page` and `pages` values.

`browse()` will call this helper and render the full page. `live_search()` will
call the same helper and render fragments. Existing invalid-request status codes
and behavior on `/products` remain unchanged.

### 3.2 Canonical arguments

Build canonical arguments from validated server values, never by reflecting the
raw query string. Use a deterministic order:

```text
q, category, condition, min_price, max_price, sort, page
```

Omit empty values, the default `sort=newest` when it adds no meaning, and
`page=1`. Preserve a non-default valid sort and a page greater than one when the
endpoint is intentionally requested that way. The browser controller always
removes the previous page before live typing, so ordinary typing receives page 1.

Unknown query parameters remain ignored and are not propagated. Repeated known
parameters are rejected before canonicalization.

## 4. Live endpoint contract

Add this exact route:

```text
GET /products/search
```

On success, return `application/json` containing:

```text
results_html      rendered grid contents or empty state
pagination_html   canonical Explore pagination or an empty string
total             integer full result count
count_label       correctly pluralized visible count
page              integer current page
pages             integer page count
canonical_query   validated URL query without a leading question mark
```

Use `jsonify`, `render_template` and Jinja auto-escaping. The endpoint will render
`_product_grid.html` and `_catalogue_pagination.html`, so product cards are not
reimplemented in Python or JavaScript.

Expected `BadRequest`/invalid-page conditions from the shared helper will be
converted to a small JSON object such as `{"error": "Choose valid search
options."}` with the original safe 400/404 status. Do not include the submitted
query, SQL text or exception details. Unexpected database/application failures
continue through the project's central safe error handling; the browser treats a
non-JSON or unsuccessful response as a recoverable live-search failure.

Add `Cache-Control: no-store` to live-search responses. Fragments can contain a
session-specific CSRF token and account-specific Add to Cart/Your listing/sign-in
presentation, so shared caching is unsafe. No CORS headers are added; requests
remain same-origin.

Only GET is defined. The route performs no commit, flush, view event, save, cart,
message or listing mutation.

## 5. Reusable template design

### 5.1 Product-grid partial

Move the existing product-grid inner markup into `_product_grid.html`:

- loop through `items` and call the existing `card()` macro;
- otherwise render the existing **No products found** panel; and
- do not add scripts, inline event handlers or duplicated card HTML.

`catalogue.html` includes the partial inside a stable
`#product-grid` container. The endpoint renders the same partial to a string.
Because `card()` remains authoritative, MM-019 controls and all card images,
seller links, escaping and accessibility behavior remain identical.

### 5.2 Pagination partial and endpoint targeting

The current pagination macro builds links from `request.endpoint`. If used
unchanged by `/products/search`, it would incorrectly point visitors to the JSON
endpoint. Extend the helper/macro as follows:

```text
page_url(number, endpoint=None)
pagination(page, pages, endpoint=None)
```

When `endpoint` is absent, every existing page keeps its current behavior. The
catalogue pagination partial passes `market.browse`, producing ordinary
`/products?...&page=N` links from either route. Tests will cover the cart, seller
and other pre-existing pagination defaults to detect regressions.

### 5.3 Explore-page hooks

Only when `search` is true, add:

- `id="catalogue-search-form"` and a `data-live-search-url` containing the Flask
  generated endpoint;
- `id="q"` retained on the Search input;
- a feedback region containing a small decorative spinner and status text;
- `id="product-result-count"` around the visible count;
- `id="product-results"` with initial `aria-busy="false"`;
- `id="product-grid"`; and
- `id="product-pagination"`.

Private `catalogue.html` uses such as **Your listings** must not initialize live
search or gain an irrelevant status region. The server-rendered initial results
remain complete before JavaScript runs.

## 6. JavaScript controller design

Add a self-contained function/IIFE to `market.js`. It must not share mutable state
with the existing lightbox, interaction-recording, AI suggestion or
recommendation code.

### 6.1 Safe initialization

Find all required hooks. Exit without error if the Explore form/input/results
elements do not exist or if `fetch`, `URL`, `URLSearchParams`, `FormData` or
`history.replaceState` are unavailable. Do not fetch during page load.

The form remains an ordinary GET form; do not cancel its `submit` event. Find
products and Enter therefore retain the reliable full-page fallback.

### 6.2 Debounce and IME

Maintain these small pieces of state:

```text
timer
requestSequence
currentController (optional)
isComposing
```

On ordinary `input`, clear the old timer and schedule a search for 300 ms later.
On `compositionstart`, mark composition active and clear the timer. Ignore input
events during composition. On `compositionend`, mark it complete and schedule one
search for the completed value.

When building the request, use `FormData(form)` and `URLSearchParams`, remove
`page`, and request the Flask-generated live endpoint. This includes current
category, condition, price and sort values without making their change events
automatic.

### 6.3 Latest-request-wins rule

When a search starts:

1. increment `requestSequence` and capture its value;
2. abort the previous controller when supported;
3. create a new controller when supported;
4. show the loading state; and
5. call same-origin `fetch` with `Accept: application/json`.

After every awaited operation, compare the captured sequence with the current
sequence. An old response may not replace HTML, update the address bar, announce
status, hide the newest spinner or clear `aria-busy`. The sequence check remains
required even with `AbortController`, because aborting can race with a response
already finishing.

### 6.4 Response validation and update

Require `response.ok`, JSON content and the expected primitive field types before
touching the page. On a valid newest response:

- assign only server-rendered `results_html` to the grid container;
- assign only server-rendered `pagination_html` to the pagination container;
- assign `count_label` through `textContent`;
- set the canonical address to `/products` plus `canonical_query` using
  `history.replaceState`;
- preserve the Search input's focus, value and caret; and
- announce `N product(s) found` concisely.

Using `innerHTML` here is limited to trusted same-origin Jinja output. Product
objects are not converted into HTML in JavaScript.

### 6.5 Loading, success and failure state

At request start:

- reveal the spinner and visible **Searching…** text;
- set `aria-busy="true"` on `#product-results`; and
- keep old results visible.

At newest-request success:

- hide the visual spinner;
- change the polite status to the concise result announcement; and
- set `aria-busy="false"`.

At newest-request failure:

- leave the previous count/grid/pagination and current canonical URL unchanged;
- hide the spinner and clear busy state; and
- announce **Live search is unavailable. Press Find products to search.**

An intentional abort from a newer request produces no error announcement. A
later input can retry after any real failure.

## 7. CSS and accessibility plan

Add narrowly scoped rules such as:

- `.live-search-feedback` for an inline, wrapping status row;
- `.live-search-spinner` for a small circular border spinner;
- `.live-search-spinner[hidden] { display: none; }` so the HTML `hidden`
  contract wins;
- `@keyframes live-search-spin` for rotation; and
- a reusable `.visually-hidden` class only if needed for completion text that
  should remain available to assistive technology.

The spinner receives `aria-hidden="true"`; meaning comes from the polite,
atomic status region. Under `prefers-reduced-motion: reduce`, remove the spinner
animation while keeping the visual shape and text. Reuse existing theme variables
so light/dark modes remain legible.

The status row and long result text must wrap at 320 CSS pixels. Updating results
does not focus or scroll the grid. Keyboard focus remains in Search, and the
existing focus styling continues to apply to form controls, cards and pagination.

## 8. Test-first execution sequence

1. Obtain explicit PLAN-020 approval.
2. Write `tests/test_live_search.py` and `tests/020-browser-checklist.md` without
   changing application/templates/JavaScript/CSS.
3. Run pytest collection. Collection must succeed; missing endpoint/hooks should
   appear as assertion failures, not import or fixture errors.
4. Run focused tests against the unchanged application and record the Red
   checkpoint. Valid expected failures include endpoint 404 and missing live
   hooks. Any unrelated baseline failure must be fixed in the test harness before
   implementation.
5. Implement the shared server helper and endpoint first, then partial templates,
   JavaScript and CSS.
6. Run focused tests until green without weakening assertions.
7. Run the complete regression suite, including MM-019 cart/card tests and the
   original MM-006 search tests.
8. Run real-browser acceptance on a loopback-only temporary fixture. Use
   controlled delay/error markers only in the test fixture, never in production
   routes.
9. Reload the real local Explore page for a read-only smoke check, save evidence,
   write the beginner guide and restart the local server with the tested code.

No database migration, local database backup, reseed or product mutation is
needed for MM-020.

Planned commands from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_live_search.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_live_search.py -q --basetemp=.pytest-tmp\mm020-red
.\.venv\Scripts\python.exe -m pytest tests\test_live_search.py -q --basetemp=.pytest-tmp\mm020-green
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm020-regression
```

## 9. Pytest coverage matrix

| Group | Required cases | Specification coverage |
| --- | --- | --- |
| Endpoint contract | GET success, JSON MIME, exact required fields/types, no-store header, POST/non-GET no mutation | AC-020-01, 13 |
| Full/AJAX parity | Matrix of empty, ordinary, literal wildcard, Unicode, category, condition, price and sorts yields same IDs/order/count | AC-020-04, 10, 11 |
| Visibility | Active appears; sold/archived/private canaries absent from HTML, counts, pagination, JSON and logs | AC-020-11 |
| Validation | Repeated supported values, invalid choices/sort/prices/page, 120/121 characters and extreme page handled with safe JSON | AC-020-10 |
| Canonical query | Deterministic allow-listed values; no empty/default/page-1/unknown/raw repeated data; non-default valid state retained | AC-020-09 |
| Pagination | Zero/one/more-than-one pages; Explore links retain validated state and never target `/products/search`; old macro callers unchanged | AC-020-06, 09 |
| Shared cards | Anonymous sign-in, buyer Add to Cart with CSRF, owner label, images/placeholders and seller links match full page | AC-020-05 |
| Escaping | HTML/quote/Unicode product and query canaries are escaped; server fragment does not produce executable user markup | AC-020-05, 10 |
| Empty results | `0 products`, expected empty panel, empty pagination, no stale-card data in response | AC-020-06 |
| No mutation | Before/after database snapshots for products, cart, saves, messages and interactions remain identical across requests/errors | AC-020-13 |
| Full-page fallback | Existing form method/action/labels/button and initial server results work without any live endpoint call | AC-020-08 |
| Template hooks | Hooks, endpoint data attribute, initial `aria-busy=false`, polite/atomic status and decorative spinner exist only on Explore | AC-020-03, 08, 12 |
| Static accessibility/CSS | Reduced-motion override, hidden contract, theme variables and scoped narrow-safe styles are present | AC-020-03, 12 |
| Safe failures | Expected invalid requests use small safe JSON; database/unexpected failure exposes no SQL/path/private/query details | AC-020-07, 11 |
| Regressions | Original marketplace, cart, seller, Saved, image/lightbox, recommendation and security tests remain green | AC-020-05, 08, 13 |

Pytest is authoritative for the server, templates, fallback, privacy and data
rules. Timing, caret/focus, request races and live DOM replacement require the
real-browser checklist below because static text assertions cannot prove browser
behavior.

## 10. Browser acceptance plan

Define the checklist before implementation, then use an isolated temporary
database and ordinary Explore UI:

1. Load Explore and confirm there is no automatic duplicate AJAX request.
2. Focus Search, type a word slowly, and verify results do not change before the
   300 ms debounce but do change afterward.
3. Use a fixture query delayed long enough to visibly verify the spinner,
   **Searching…**, busy state and unchanged old grid.
4. Confirm the document does not reload: header/page state remains and navigation
   timing does not gain a new document navigation.
5. Verify count, cards, empty state and pagination update together.
6. Apply category/sort with the normal form, then type Search and confirm those
   selections remain part of the live result.
7. Start a controlled slow query, immediately replace it with a fast query and
   verify only the newest query wins after both could have completed.
8. Trigger a controlled fixture failure/malformed response, verify old results
   remain and the fallback message appears, then type a valid query and recover.
9. Verify the address bar uses `/products?...`, never `/products/search`, and one
   letter does not create one Back-history step.
10. As anonymous, buyer and owner, verify returned cards have the correct sign-in,
    Add to Cart or Your listing control. Do not mutate the real local database.
11. Verify Search retains focus/caret while typing and keyboard navigation remains
    logical after replacement.
12. Verify a zero-result query removes old cards/pagination and announces zero.
13. Test 320 CSS-pixel width, two-digit/long text wrapping, no horizontal overflow,
    visible focus and available 200% zoom checks.
14. Check reduced-motion behavior if the browser exposes media emulation; otherwise
    report the limitation and rely on the CSS/pytest contract.
15. Confirm Find products and Enter still perform a normal form search. Confirm a
    direct no-script response contains complete initial results and controls.
16. Inspect browser console errors/warnings and save desktop/narrow evidence.

IME behavior will be exercised with real composition events only if the available
browser controls can produce them. Otherwise the limitation will be stated, with
the event wiring covered by the defined implementation review/static contract.

## 11. Controlled browser fixture

If normal local responses are too fast to observe loading and races reliably,
create `tests/preview_live_search.py`. It will:

- use a temporary SQLite database/uploads directory;
- seed clearly named public, hidden and multi-page products;
- run only on loopback;
- delay a known test-only query before the actual production endpoint executes;
- return a controlled error/malformed payload for known test-only markers; and
- never register those delay/error hooks in `create_app()` or production code.

Stop the disposable server and restore browser viewport overrides after checks.
The real local site receives only a read-only final Explore request.

## 12. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| AJAX and full-page search disagree | One shared parser/query helper and parity matrix across both endpoints. |
| Slow old response overwrites new results | Abort when available plus mandatory monotonically increasing sequence check. |
| Request on every keystroke overloads server | Exact 300 ms debounce; no initial duplicate request. |
| Spinner gets stuck after abort/error | Only newest request owns final loading state; every newest success/failure clears busy state. |
| Page becomes unusable when JavaScript fails | Do not intercept normal form submission; preserve complete initial server rendering. |
| Fragment leaks archived listings or private data | Same active-only query; private canaries in JSON/HTML/count/log tests. |
| Fragment leaks CSRF/account state through cache | `Cache-Control: no-store`, same-origin requests, no client response cache. |
| XSS through dynamic HTML | Only insert same-origin Jinja-rendered, auto-escaped partials; never concatenate product fields in JavaScript. |
| Pagination sends users to JSON | Optional endpoint-aware URL helper plus regression tests for every generated link. |
| Screen reader announces too much | One polite atomic status; do not place the entire changing grid in a live region. |
| Search steals focus or caret | Replace sibling result containers only; never replace/refocus the form/input. |
| IME produces incomplete searches | Suppress input during composition; schedule once on composition end. |
| Existing lightbox/AI JavaScript breaks | Isolated controller with early exit; full suite and browser smoke tests. |

## 13. Rollback and recovery

MM-020 has no database migration or stored data, so rollback is simple and safe:

1. remove the live endpoint and shared helper integration while restoring the
   original `browse()` body;
2. restore the catalogue's original inline grid/count/pagination markup;
3. remove the live-search JavaScript and CSS; and
4. run original marketplace and full regression tests.

The ordinary GET search remains a working fallback even if only the JavaScript is
temporarily disabled. No cart, listing, image or account recovery is required.

## 14. Beginner concepts to document

The final guide will explain:

- **AJAX:** requesting a small update instead of a whole new page;
- **debouncing:** waiting briefly so fast typing creates fewer requests;
- **race condition:** two requests finish in a different order than they started;
- **latest request wins:** identifying which answer still matches the input;
- **progressive enhancement:** starting with a complete form and adding optional
  JavaScript convenience;
- **server as source of truth:** privacy and filtering still happen in Flask;
- **DOM replacement:** changing only the result containers; and
- **accessible loading state:** giving both sighted and screen-reader users useful
  feedback without moving their focus.

## 15. Approval gate

This plan intentionally makes five implementation choices:

1. add `GET /products/search` rather than changing `/products` into a mixed HTML/
   JSON route;
2. refactor the existing search into one shared server helper;
3. return server-rendered card and pagination HTML inside a small JSON response;
4. keep filters and pagination as ordinary submitted/navigation behavior while
   only Search typing is automatic; and
5. use an isolated slow/error fixture for browser timing tests instead of adding
   test behavior to the real application.

The user replied **“I approve PLAN-020.”** on 2026-11-02. The Testing stage may
now begin. Tests and the browser checklist must be written and a Red checkpoint
recorded before any application implementation.
