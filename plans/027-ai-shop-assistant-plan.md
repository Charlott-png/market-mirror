# PLAN-027 — Gemini AI Shop Assistant

Status: IMPLEMENTED — approved 2026-11-07; completed 2026-11-07

Date: 2026-11-07 (Asia/Shanghai)

Approved specification: MM-027, explicitly approved by the user on 2026-11-07.

## 1. Outcome

Implement an optional, login-protected Gemini shopping assistant as a floating
progressive-enhancement widget. It will answer bounded product-discovery
questions using a fresh, privacy-minimized set of active Market Mirror
products. Gemini may suggest only product IDs and plain-text reasons. Market
Mirror will validate those IDs, recheck availability and create every title,
price, image and URL from its own database.

The feature will be disabled by default and will fail back to ordinary Explore
search without affecting the rest of the site.

## 2. Architecture

```text
Base page
  └─ floating launcher + assistant panel
       ├─ anonymous/disabled → sign-in or Explore fallback; no API call
       └─ signed in + enabled
            │
            │ POST JSON + CSRF
            ▼
       /ai/shop-assistant
            ├─ validate query/history/body size
            ├─ consume per-user rate limit
            ├─ select ≤60 active public product records
            └─ call Gemini through injectable adapter
                         │
                         ▼ strict JSON
            validate exact shape, text and candidate IDs
                         │
                         ▼
            re-query suggested IDs as active products
            build trusted title/price/image/detail URLs
                         │
                         ▼ no-store JSON
       browser creates text nodes, cards and real links
```

There are three trust boundaries:

1. shopper query/history are untrusted request input;
2. seller titles/descriptions are untrusted catalogue data; and
3. Gemini output is untrusted external input.

The database and Flask route—not the model—remain authoritative for product
status, display facts and links.

## 3. Planned file changes

| File | Planned responsibility |
| --- | --- |
| `config.py` | Parse disabled-by-default assistant flag, Gemini model and 3–30 second timeout; allow test adapter injection. |
| `.env.example` | Document safe placeholder settings using the existing private `GEMINI_API_KEY`. |
| `app/ai/shop_catalogue.py` | Select and serialize no more than 60 active product candidates without private fields. |
| `app/ai/shop_assistant.py` | Availability, query/history/result validation, orchestration and post-response active-product recheck. |
| `app/ai/gemini_shop.py` | Isolated `google-genai` structured-output adapter with fixed prompt, no tools, one attempt and safe errors. |
| `app/ai/routes.py` | Add authenticated JSON/CSRF/rate-limited `POST /ai/shop-assistant`. |
| `app/templates/_shop_assistant.html` | Accessible launcher, non-modal panel, transcript, controls, disclosure and anonymous/disabled fallbacks. |
| `app/templates/base.html` | Include exactly one widget and its dedicated deferred script on every base page. |
| `app/static/js/shop-assistant.js` | Open/close/focus, bounded transcript, request lifecycle, safe DOM rendering, abort/stale handling and browser-memory history. |
| `app/static/css/style.css` | Fixed desktop placement, mobile-nav offset, panel/message/card states, focus, dark/print/reduced-motion rules. |
| `tests/test_shop_assistant.py` | Request, catalogue, privacy, route, race, rate, HTML/JS/CSS and no-persistence contracts. |
| `tests/test_gemini_shop.py` | Gemini client/schema/prompt/tool/timeout/error contracts with fake clients only. |
| `tests/027-browser-checklist.md` | Isolated desktop/mobile/keyboard/loading/result/error checks. |
| `tests/027-red-verification.md` | Record pre-implementation collection and intentional failures. |
| `tests/027-green-verification.md` | Record focused/full tests, dependency check and browser evidence. |
| `tests/preview_shop_assistant.py` | Temporary database, fictional login/products and fake Gemini for loopback browser checks. |
| `docs/027-ai-shop-assistant-guide.md` | Beginner explanation of RAG, structured output, trust boundaries and graceful degradation. |
| `README.md` | Link the guide and document optional enabling steps. |
| `docs/verification-matrix.md` | Map AC-027 requirements to evidence and honest remaining manual checks. |

No database model or Alembic migration is planned. The existing `RateLimit`
table provides cost throttling, and assistant conversation is not persisted.
No new dependency is planned because `google-genai` is already locked for
MM-024.

## 4. Configuration design

Add class defaults:

```text
SHOP_ASSISTANT_ENABLED = False
SHOP_ASSISTANT_MODEL = "gemini-3.5-flash-lite"
SHOP_ASSISTANT_TIMEOUT_SECONDS = 12
```

`environment_settings()` will:

1. parse `SHOP_ASSISTANT_ENABLED` with the existing strict boolean helper;
2. trim and validate a printable model name of at most 80 characters;
3. require a `gemini-` prefix when the feature is enabled;
4. parse the timeout as an integer from 3 through 30; and
5. return only configuration—not copy `GEMINI_API_KEY` into Flask config.

The provider reads the key directly from the process environment, matching the
existing vision adapter. The test-only callable `SHOP_ASSISTANT_GENERATOR` can
be placed in `test_config` and is never read from environment text.

Availability is true only when:

- the feature flag is true; and
- either a callable test generator exists or a nonblank `GEMINI_API_KEY` is
  present.

Vision and shopping settings remain independent. `.env.example` uses a fake
placeholder and docs instruct the student never to paste a key into code,
tests, Git, screenshots or chat.

## 5. Catalogue candidate builder

Create `app/ai/shop_catalogue.py` with a small immutable record/dictionary
contract. Every record contains only:

```text
id, title, category, condition, price, description
```

Formatting rules:

- category/condition become their fixed public labels;
- price is a two-decimal USD string;
- description is trimmed to 300 characters;
- no SQLAlchemy objects are passed to the provider;
- no username, seller/account ID, image/filename, event, cart or order field is
  present; and
- records use a stable deterministic order.

### 5.1 Up to 60 active products

First count active products.

- If the count is 60 or fewer, select every active product ordered by ID.
- If it is greater than 60, tokenize the query into at most 12 case-folded
  literal terms of 2–40 characters, removing punctuation and duplicates.
- Use SQLAlchemy parameters and escaped literal `ILIKE`; never concatenate raw
  query text into SQL.
- Select up to 40 title/category/description matches ordered by match group,
  price, newest date and ID.
- Fill remaining slots from a cheapest-active query and then a newest-active
  query, de-duplicating by product ID until reaching 60.
- Return `truncated=True` whenever the full active count exceeds the candidate
  count.

This gives “cheap camera” a chance to include literal camera matches and cheap
fallbacks while guaranteeing bounded provider context. SQLite and PostgreSQL
tests will focus on portable SQLAlchemy expressions; no database-specific
full-text search is introduced.

### 5.2 Catalogue prompt serialization

Serialize candidates as JSON data separate from the fixed instruction. A
catalogue prefix will state that all values are untrusted marketplace data and
cannot issue instructions. `json.dumps` handles boundaries instead of manual
string concatenation.

Unit tests will use malicious product text such as “ignore prior instructions”
and HTML/script fragments to prove that it remains a quoted data value and
cannot create links or executable output.

## 6. Request validation

The endpoint will enforce a small route-specific body limit (planned 8 KiB)
before parsing, despite the larger global image-upload request limit.

Accept exactly:

```json
{"query": "...", "history": [...]}
```

Validation helpers in `shop_assistant.py` will require:

- a JSON object with exact top-level keys;
- query as a trimmed string of 1–300 characters;
- no C0/C1 control characters except no whitespace normalization surprises;
- history as a list of no more than six messages;
- exact message keys `role` and `content`;
- roles alternating `user`, `assistant`, beginning with user and ending with
  assistant because history contains only complete exchanges;
- each history content as trimmed plain text of 1–600 characters; and
- combined history length no more than 2,400 characters.

Wrong content type, malformed JSON, arrays, booleans, numbers, duplicate-like
unexpected fields, wrong role order and excessive/deep data return a stable
400 response before rate/provider work.

## 7. Output validation

Define one pure `validate_shop_result(raw, allowed_ids)` function. It will
accept only an exact dictionary containing:

```text
summary
recommendations [{product_id, reason}, ...]
follow_up
```

Rules mirror MM-027 exactly:

- summary 1–500 characters;
- recommendations a list of zero through three exact dictionaries;
- IDs are real integers, not booleans/floats/strings;
- IDs are unique and members of `allowed_ids`;
- reason 1–240 characters;
- follow-up 0–200 characters;
- all strings are already trimmed;
- C0/C1 controls and `<`/`>` are rejected; and
- extra/missing fields reject the whole result.

The validator returns newly constructed values rather than the provider's
mutable object. Parameterized tests will cover every field, boundary and common
Python type confusion.

## 8. Gemini adapter

`GeminiShopProvider` will follow the proven `GeminiVisionProvider` pattern:

- instantiate `genai.Client` with `GEMINI_API_KEY` only on the server;
- use configured timeout in milliseconds;
- set retry attempts to one;
- accept dependency-injected fake client in tests;
- call the configured model;
- request `application/json` with an explicit response JSON Schema;
- use low/zero temperature and a small output-token cap;
- pass an empty tools list;
- read only nonblank response text and parse JSON; and
- translate every SDK/parse failure into a stable `GeminiShopError` without
  provider body, key, query or catalogue text.

The fixed instruction will cover product-discovery scope, exact IDs, no wider
web, factual limits, no private-data request and untrusted catalogue/query
content. Tests will inspect fake-client arguments rather than contact Google.

The adapter will not use server-side Gemini conversation IDs. Each request is
self-contained so provider state is not stored beyond the call.

## 9. Orchestration and status-race recheck

The orchestration sequence is:

1. validate query and history;
2. build current active candidates;
3. if there are no candidates, return an honest local no-products response
   without calling Gemini;
4. call the injected generator or `GeminiShopProvider`;
5. validate output against the exact sent candidate IDs;
6. issue one new database query for recommended IDs with `status == active`;
7. preserve model order while dropping missing/sold/archived rows;
8. create current title, two-decimal price, public condition and Flask URLs;
9. include cover media URL only when a safe referenced cover exists; and
10. if all IDs disappeared, return a safe no-match/Explore response.

The provider cannot supply display title, price, image or URL. `url_for` creates
both product-detail and optional media URLs. The response carries a truncation
flag so JavaScript can show the candidate-set disclosure.

Tests will use a fake generator that changes a recommended product to sold
before returning, proving that the post-provider query removes it.

## 10. Endpoint and security flow

Add `POST /ai/shop-assistant` to the existing `ai` blueprint with
`@login_required`. Flask-WTF will enforce a same-origin CSRF token supplied in
the `X-CSRFToken` header.

Processing order:

1. authentication/CSRF framework checks;
2. feature/key availability check;
3. content type/body size/shape validation;
4. `consume_limit("shop-assistant", str(current_user.id), 15, 600)`;
5. provider orchestration; and
6. explicit private/no-store JSON response.

A valid request consumes allowance even when the provider fails. Obviously
invalid input does not spend it. This prevents repeated provider-failure abuse
while preserving student-friendly form correction.

Return stable user-facing status families:

- 200 success or honest no-match;
- 400 malformed request;
- existing login behavior for anonymous forged requests;
- 429 existing rate-limit response; and
- 503 disabled/key missing/provider timeout/invalid provider result.

All caught provider failures log only a fixed event name. Tests place canary
query/key/catalogue/response strings into failures and assert they appear in
neither response nor captured logs.

## 11. Widget template

Create `_shop_assistant.html` and include it once near the end of `base.html`.
Use semantic HTML available before JavaScript:

- launcher button with `aria-expanded`, `aria-controls` and accessible name;
- `<aside>` region labelled by its heading and initially hidden;
- close button;
- transcript list with greeting;
- visible label and 300-character textarea;
- Send and Clear chat controls;
- polite status paragraph;
- Google/privacy/AI limitation disclosure; and
- Explore/sign-in fallback links.

For signed-in users, render a normal CSRF hidden value for the script to read.
Never render the Gemini key, model, provider prompt or environment value.

Availability controls whether the interactive form is rendered/enabled. It
must not call Gemini. A test adapter counts calls during GET requests to prove
that rendering every base page is side-effect free.

## 12. JavaScript design

Use a dedicated deferred `app/static/js/shop-assistant.js` so assistant logic
is independent of the existing `market.js` feature blocks.

Guard immediately if required DOM elements are missing. The script will:

- reveal the enhancement only after initialization;
- open/close the panel and synchronize `hidden`/`aria-expanded`;
- focus the textarea on open and restore launcher focus on close;
- close on Escape without trapping focus;
- keep at most three complete exchanges in an in-memory array;
- validate/trim query length before request;
- send JSON with same-origin credentials, JSON accept/content type and
  `X-CSRFToken`;
- disable Send and set `aria-busy` while one request is active;
- use one `AbortController` and monotonically increasing request sequence;
- ignore stale/aborted responses;
- create transcript/product elements using `createElement`, `textContent`,
  property assignment and trusted server URLs;
- never use `innerHTML`, execute response markup or construct a media URL;
- show safe messages for 400/429/503/network cases;
- add successful assistant summary to bounded browser history;
- clear DOM/history and abort pending work on Clear chat; and
- abort on `pagehide`.

History is not stored in cookies, `localStorage`, `sessionStorage`, IndexedDB
or the server. Static tests will explicitly reject those tokens in the feature
script.

## 13. CSS and responsive design

Add namespaced `.shop-assistant-*` rules only.

Desktop:

- launcher fixed at bottom/right with safe viewport spacing and a z-index below
  the lightbox but above ordinary content;
- panel fixed above launcher, width bounded near 24rem and max-height bounded by
  `dvh` with internal transcript scrolling;
- message/recommendation cards wrap long text; and
- controls meet 44-pixel minimum targets.

At the existing `max-width: 42rem` breakpoint:

- both launcher and panel bottom offset include the 4.75rem mobile-navigation
  height plus safe-area inset;
- panel width uses viewport-relative insets;
- maximum height leaves header and bottom navigation usable; and
- no body overflow is introduced.

Add visible focus/current/loading/error states, dark-mode compatibility,
reduced-motion animation removal and a print rule that hides the entire
assistant. Do not change the mobile navigation's own z-index or behavior.

## 14. Test-first files and cases

No application implementation begins until these tests are written and proven
Red.

### 14.1 `tests/test_shop_assistant.py`

Planned groups:

1. **Configuration/availability**
   - disabled defaults;
   - valid enabled Gemini settings;
   - strict bad boolean/model/timeout rejection;
   - missing/blank key unavailable;
   - callable fake available without a real key.

2. **Pure request/history validation**
   - 1/300 boundaries and Unicode;
   - empty/whitespace/301/control/wrong types;
   - exact keys, roles, alternating complete exchanges;
   - per-message, combined and six-message limits.

3. **Catalogue privacy/bounds**
   - only active rows;
   - exact allowed fields and two-decimal prices;
   - description truncation;
   - no seller/user/image/private fields;
   - ≤60 full and >60 deterministic candidate paths;
   - literal `%`, `_`, quotes and prompt-injection query/product text;
   - stable order and accurate truncation flag.

4. **Pure output validation**
   - valid zero/one/three recommendations;
   - every exact field boundary;
   - booleans/floats/strings as IDs;
   - duplicate/out-of-candidate IDs;
   - extra/missing keys, unsafe brackets/control/whitespace and wrong nesting.

5. **Endpoint security/lifecycle**
   - login and real CSRF header required;
   - GET/method rejection;
   - disabled/anonymous/page-load produce zero calls;
   - malformed/oversize payload does not consume/call;
   - successful query and no-product path;
   - per-user atomic 15/10-minute limit isolated from vision/category scopes;
   - valid provider failure consumes allowance;
   - explicit private/no-store response.

6. **Trusted rehydration/races**
   - server creates current URLs/title/price/condition/image;
   - any model URL/title/price cannot enter response contract;
   - sold/archived/deleted-after-call recommendation drops;
   - order preserved for surviving recommendations;
   - all-stale fallback and full Explore URL;
   - duplicate HTTP retry creates no database/product/cart/order change.

7. **Privacy/logging/no persistence**
   - canary key/query/history/product/output/provider exception absent from logs
     and errors;
   - database table snapshots unchanged except intentional RateLimit row;
   - no interaction/chat/order/cart/save/message write.

8. **Template/static contracts**
   - exactly one widget on home/catalogue/product/auth pages;
   - anonymous, unavailable and available markup/accessibility states;
   - disclosure/sign-in/Explore links;
   - JS safe DOM APIs, CSRF, abort, sequence, length/history and no-storage
     contracts;
   - no `innerHTML`, eval-like APIs or model URL construction;
   - CSS placement, 44px, mobile-nav offset, overflow, reduced-motion, dark and
     print contracts.

### 14.2 `tests/test_gemini_shop.py`

Use fake SDK clients/responses to verify:

- key is read from environment only;
- configured model and milliseconds timeout;
- one attempt/no retry loop;
- structured JSON MIME/schema and exact required shape;
- maximum three recommendation items in schema;
- low temperature, bounded output tokens and `tools=[]`;
- fixed scope/untrusted-data instruction;
- serialized candidate/history boundary;
- valid JSON return;
- blank/malformed/wrong-shaped response failure; and
- SDK errors become stable `GeminiShopError` without sensitive text.

No automated test contacts Google or spends an API quota.

## 15. Existing regression suites

After focused Green, run at minimum:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_shop_assistant.py tests\test_gemini_shop.py -q --basetemp=.pytest-tmp\mm027-focused
.\.venv\Scripts\python.exe -m pytest tests\test_ai.py tests\test_ai_vision.py tests\test_gemini_vision.py tests\test_live_search.py tests\test_mobile_navigation.py tests\test_cart.py tests\test_checkout.py -q --basetemp=.pytest-tmp\mm027-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm027-full
.\.venv\Scripts\python.exe -m pip check
```

The full suite is authoritative. Expected count will be reported rather than
pre-guessed because MM-027 adds parameterized tests.

## 16. Red verification sequence

After PLAN-027 approval:

1. create only the two pytest modules, browser checklist and Red record shell;
2. collect focused tests to prove the contracts are syntactically valid;
3. run focused tests before any app implementation;
4. confirm failures specifically show missing config/modules/route/widget/script
   rather than broken fixtures;
5. record command, collected count, passed/failed count and representative
   missing-feature failures in `tests/027-red-verification.md`; and
6. only then begin implementation.

Some old generic security/config tests may already pass. A valid Red checkpoint
requires the new core provider, endpoint, safe links and widget tests to fail.

## 17. Planned implementation order after Red

1. configuration parsing and availability;
2. pure request/result validators;
3. active catalogue candidate builder;
4. Gemini adapter;
5. orchestration and availability recheck;
6. authenticated/CSRF/rate-limited endpoint;
7. widget template/base inclusion;
8. dedicated safe JavaScript;
9. responsive/accessibility CSS;
10. focused Green and fixes;
11. regression/full/dependency verification;
12. isolated browser verification; and
13. beginner docs, evidence and status updates.

This order makes the trusted server contract Green before connecting the user
interface.

## 18. Browser verification plan

`tests/preview_shop_assistant.py` will use only:

- a database/uploads directory under `.pytest-tmp`;
- fictional user credentials shown in its console;
- active/sold/archived fictional products including cheap and expensive
  cameras;
- a fake deterministic Gemini generator;
- fake delay, no-match, malformed-output, prompt-injection and provider-failure
  query modes; and
- a non-default loopback port.

The checklist will verify:

1. anonymous launcher, sign-in fallback and zero fake calls;
2. authenticated opening/focus/Escape/focus return;
3. “Find me a cheap camera” loading and relevant trusted product cards;
4. real detail-link navigation;
5. follow-up history and clear-chat memory reset;
6. duplicate Send prevention and stale/aborted response handling;
7. no-match, 429 and provider-failure fallbacks;
8. malicious query/product/model text rendered only as text;
9. 320/360px placement above mobile navigation;
10. keyboard-only flow, visible focus, transcript announcements;
11. reduced-motion/dark/200% zoom where browser controls permit; and
12. no console errors or changes to unrelated search/cart/listing behavior.

Browser verification must inspect fake-adapter counters and temporary DB rows,
not merely appearance. It will honestly record any gesture, screen-reader or
zoom behavior that available tools cannot fully establish.

## 19. Real-key verification boundary

Automated and browser tests use a fake generator and never contact Google.

After all isolated checks pass, documentation will offer one optional manual
real-key smoke test:

1. keep the key only in ignored `.env`;
2. enable `SHOP_ASSISTANT_ENABLED=true`;
3. restart the local server;
4. sign in and submit one ordinary fictional-product question;
5. confirm safe answer/fallback and no secret in logs/browser; and
6. disable again if the student does not want ongoing quota use.

The implementation will not read, display, print, replace or commit the
student's real `.env` key. It will not enable billing or promise that a Google
free tier remains available.

## 20. No database migration or real-data mutation

MM-027 introduces no schema change, so no database backup/migration is needed.
Before/after application verification will confirm:

- product/user/order/cart/message/save counts and content are unchanged;
- only deliberate RateLimit rows may be added by real requests;
- tests and browser fixture never point at `instance/market-mirror.sqlite`; and
- no assistant transcript file or table exists.

The current local application can be restarted after implementation, but
successful code verification does not require modifying a real product or
placing an order.

## 21. Acceptance-criteria traceability

| Criterion | Primary planned evidence |
| --- | --- |
| AC-027-01 | Template uniqueness/accessibility/static CSS tests; mobile browser checklist |
| AC-027-02 | Anonymous/disabled/missing-key zero-call endpoint and browser tests |
| AC-027-03 | Query boundary tests; loading/answer/error/clear browser flow |
| AC-027-04 | Active-only/exact-fields/≤60/truncation/history tests |
| AC-027-05 | Gemini fake-client schema/tools/timeout/secret tests |
| AC-027-06 | Parameterized exact result validator and unsafe-output tests |
| AC-027-07 | Post-call status race, server URL/current field and media tests |
| AC-027-08 | Cheap-camera fake provider endpoint/browser scenario and no-match case |
| AC-027-09 | Real CSRF/auth/rate/duplicate/private-cache tests |
| AC-027-10 | Disabled/no-product/timeout/malformed/race/network fallback tests |
| AC-027-11 | Query/product/output injection and safe DOM/link-boundary tests |
| AC-027-12 | Disclosure, canary logging and no-persistence snapshots |
| AC-027-13 | Semantic/static checks plus keyboard/mobile/zoom/reduced-motion checklist |
| AC-027-14 | Focused/regression/full/pip-check/loopback evidence records |

## 22. Beginner learning guide

The final guide will explain at high-school level:

- why Gemini needs a fresh list of products (small RAG example);
- why JSON output is easier to check than arbitrary prose/links;
- why an AI answer is still untrusted input;
- why Market Mirror generates links from product IDs;
- how a product can become sold while the model is answering;
- why rate limits protect both the service and a free quota;
- why browser memory differs from database persistence; and
- how graceful degradation keeps Explore useful without AI.

Practice exercises will ask the student to predict behavior for a cheap-camera
query, a forged product ID, a product sold mid-request, a missing key and a
sixteenth request in ten minutes.

## 23. Definition of done

MM-027 is complete only when:

1. every AC-027 criterion maps to passing or honestly bounded evidence;
2. valid Red evidence predates implementation;
3. no live provider is used by automated tests;
4. active/private candidate boundaries and 60-item cap pass;
5. strict output and trusted-link/status-race tests pass;
6. auth, CSRF, rate, body and cache controls pass;
7. secrets/query/history/catalogue/provider details do not leak to responses or
   logs;
8. widget accessibility/safe-DOM/mobile contracts pass;
9. focused, related regression, full pytest and dependency checks pass;
10. isolated browser fixture/checklist passes to the supported extent;
11. real marketplace data/schema remain unchanged except optional rate rows;
12. docs explain optional real-key enabling and limitations; and
13. specification, plan and verification records receive accurate final
    statuses.

## 24. Approval and completion record

The user explicitly approved **PLAN-027** on 2026-11-07. The preserved Red
checkpoint is `tests/027-red-verification.md`. Implementation then made all 76
focused contracts Green, passed 170 related regressions and passed the complete
536-test suite. Browser verification used only a temporary database and fake
Gemini generator; no real key, quota, product or order was changed.
