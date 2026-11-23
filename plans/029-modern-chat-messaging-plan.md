# PLAN-029 — Modern Conversation Chat Interface

Status: IMPLEMENTED — PLAN-029 approved and completed on 2026-11-07

Date: 2026-11-07 (Asia/Shanghai)

Approved specification: MM-029, explicitly approved by the user on 2026-11-07.

## 1. Outcome

Turn the existing individual conversation page into a modern, accessible chat
view without replacing Market Mirror's secure messaging rules.

The implementation will add:

- outgoing blue/right and incoming grey/left bubbles;
- semantic timestamps with browser-local 12-hour display;
- a participant-only, read-only message-update endpoint;
- non-overlapping three-second polling on the latest history page;
- safe DOM appending without duplicate bubbles;
- a scrollable transcript and sticky responsive composer; and
- graceful no-JavaScript and temporary-failure behavior.

No database schema migration, external service or WebSocket server is needed.

## 2. Architecture

```text
Participant opens /messages/<conversation_id>
                       │
                       ├─ Flask checks buyer/seller participation
                       ├─ loads newest 50 messages, then displays them oldest→newest
                       ├─ renders safe bubbles + UTC timestamp fallbacks
                       └─ supplies update URL and highest message ID
                                      │
                                      ▼
                         conversation.js waits 3 seconds
                                      │
                GET /messages/<id>/updates?after_id=<highest>
                                      │
                       ├─ participant check again
                       ├─ bounded query (maximum 50)
                       ├─ allow-listed JSON + no-store
                       └─ no database write
                                      │
                                      ▼
                       validate complete response batch
                       create text nodes for new IDs only
                       preserve/advance scroll appropriately
                       schedule next non-overlapping check
```

The normal reply form remains a CSRF-protected POST followed by redirect. AJAX
sending is deliberately excluded so sending still works without JavaScript.

## 3. Files and responsibilities

| File | Planned change | Reason |
| --- | --- | --- |
| `app/engagement.py` | Add cursor parsing, message serialization, newest-block history query and the participant-only updates route. | The server remains the authority for access, ownership and safe response fields. |
| `app/templates/conversation.html` | Replace the flat message panel with semantic chat shell, bubble list, chat navigation, status region, read form and sticky composer. | Supplies a usable server-rendered baseline and JavaScript hooks. |
| `app/templates/base.html` | Add an empty page-specific scripts block after global scripts. | Loads chat JavaScript only on the conversation page without affecting every page. |
| `app/static/js/conversation.js` | Localize time, poll, validate, deduplicate, append safely, manage visibility/errors/scroll and update the read-form cursor. | Adds progressive enhancement while leaving form sending server-driven. |
| `app/static/css/style.css` | Add bubble, transcript, status, composer, mobile, dark, reduced-motion and print rules. | Produces the modern layout without hiding content from non-JavaScript users. |
| `tests/test_modern_chat.py` | Focused route, rendering, privacy, pagination, polling and read-only tests. | Provides executable MM-029 contracts before implementation. |
| `tests/test_modern_chat_assets.py` | Static HTML/CSS/JavaScript safety and accessibility contracts. | Covers client behaviors that Flask integration tests cannot execute. |
| `tests/preview_modern_chat.py` | Temporary loopback-only two-user chat fixture and isolated incoming-message control. | Enables browser verification without touching real messages. |
| `tests/029-red-verification.md` | Record intended failing tests before implementation. | Preserves the SDD Red checkpoint. |
| `tests/029-green-verification.md` | Record focused, regression, full, browser and environment results. | Makes completion claims auditable. |
| `tests/029-browser-checklist.md` | Repeatable manual/automated browser story. | Makes visual and timing checks reproducible. |
| `docs/029-modern-chat-guide.md` | Beginner explanation and presentation exercises. | Helps the student confidently explain the feature. |
| `docs/verification-matrix.md` | Add AC-029 traceability and honest limits. | Keeps project-wide evidence current. |

No model or migration file should change.

## 4. Server design

### 4.1 Shared participant boundary

Both the HTML thread and JSON updates route will call the existing
`participant(conversation_id)` helper. This retains the current non-revealing
404 behavior for guessed conversations.

The server calculates `is_own` using `message.sender_id == current_user.id`.
Neither the HTML form nor update query may supply or override a sender ID.

### 4.2 Cursor parser

Add a small helper that accepts exactly one `after_id` value and rejects:

- missing values;
- duplicate query keys;
- empty text;
- signs, spaces, decimals or scientific notation;
- non-ASCII digits;
- values longer than 19 digits; and
- values outside a signed 64-bit non-negative range.

Invalid input returns a generic HTTP 400 JSON error. The server will not query
whether the cursor belongs to any conversation, preventing cursor-based privacy
leaks.

### 4.3 Latest history block

The thread route will stop using the generic ascending `paginate()` helper for
messages. It will instead:

1. validate the page with the existing `page_number()` rule;
2. count only messages in the authorized conversation;
3. treat page 1 as the latest block;
4. query `created_at DESC, id DESC`, offset by `(page - 1) * 50`;
5. reverse the returned block in memory for chronological display; and
6. reject an out-of-range nonempty page with 404.

This keeps queries bounded while making the default page feel like a chat app.
Page 2 and above are older blocks and will not enable polling.

The template will use chat-specific **Older messages**, **Newer messages** and
**Return to latest messages** links rather than the generic pagination labels.

### 4.4 Update query

Add:

`GET /messages/<int:conversation_id>/updates`

After authorization and cursor validation, query 51 rows for the authorized
conversation where `Message.id > after_id`, ordered by
`Message.created_at ASC, Message.id ASC`.

- Return the first 50.
- `has_more` is true when row 51 exists.
- `latest_id` is the maximum returned ID, or the supplied cursor for an empty
  result.
- Eager-load the sender in the bounded query.
- Do not call `locked_product()`, `consume_limit()` or a write helper.

The response is produced with Flask `jsonify`, receives
`Cache-Control: no-store`, and contains only:

- `id`;
- `body`;
- `sender_username`;
- `is_own`;
- `created_at` in canonical UTC ISO form;
- `fallback_time` in 12-hour UTC form;
- `latest_id`; and
- `has_more`.

### 4.5 Timestamp serializer

Use the existing UTC-aware type. A serializer will:

- normalize a naive legacy value as UTC rather than local server time;
- convert aware values to UTC;
- emit ISO text ending in `Z`; and
- format a stable fallback such as `10:45 AM UTC`.

No locale-dependent server output will be asserted beyond the approved format.

### 4.6 Response failures

- Invalid cursor: generic JSON 400.
- Anonymous request: existing login-required behavior, with no message data.
- Authenticated non-participant: non-revealing 404.
- Database failure: normal safe 500 handling; no raw SQL or message bodies.

No message body will be logged.

## 5. Server-rendered HTML design

### 5.1 Chat shell

`conversation.html` will render:

- a back link to Messages;
- the product title and current listing status;
- a `.chat-shell` region;
- an ordered `#chat-transcript` list;
- `#chat-live-status` with `role="status"` and `aria-live="polite"`;
- the explicit mark-read form when messages exist; and
- the reply composer for non-archived conversations.

The chat shell receives trusted data attributes:

- update endpoint URL;
- current highest message ID;
- whether this is the latest page; and
- a generic sign-in/reconnect message if needed.

No CSRF token, request token or user ID is placed in a JavaScript data
attribute.

### 5.2 Bubble markup

Every message list item includes:

- `data-message-id`;
- `chat-message--outgoing` or `chat-message--incoming`;
- a sender label (`You` or the other username);
- a plain-text, preserve-lines body; and
- a semantic time with ISO `datetime`, UTC fallback text and localization hook.

The ownership class is rendered from the authenticated session.

### 5.3 Composer

The current `MessageForm`, hidden CSRF value and request token remain. The form
will receive `.chat-composer`, with:

- an accessible textarea label;
- two default rows and the current 2,000-character maximum;
- visible field errors where applicable;
- one Send button; and
- normal form method/action.

Archived conversations show the existing read-only policy and no composer.

### 5.4 No-JavaScript behavior

All existing messages, bubble sides, UTC times, older-history navigation,
read-marker form and normal reply form are in server HTML. Only automatic
updates, browser-local time and smart scroll behavior require JavaScript.

## 6. CSS design

### 6.1 Main layout

- `.chat-page` constrains readable width.
- `.chat-shell` uses a surface, border, rounded corners and overflow control.
- `.chat-transcript` is a list with a bounded `max-height`, vertical scrolling,
  stable scrollbar space where supported and `overscroll-behavior: contain`.
- The transcript retains padding below its last bubble so the composer never
  covers content.

### 6.2 Bubble rules

- List rows use flex layout.
- Outgoing row justifies to the end; incoming to the start.
- Bubble width is capped near 75%, with `min-width: 0` and
  `overflow-wrap: anywhere`.
- Outgoing uses a fixed readable blue foreground/background pair instead of
  reusing a dark-mode variable that could reverse contrast.
- Incoming uses a neutral background and normal text color.
- Border radius and spacing provide a chat appearance.

### 6.3 Timestamp/sender rules

Sender and time text are visually smaller but retain readable contrast.
Outgoing metadata uses a blue-background-compatible color. Incoming metadata
uses the standard muted color.

### 6.4 Sticky composer

The composer is a two-column grid (`minmax(0, 1fr) auto`) at normal widths,
sticky at the bottom of the chat shell, with its own solid surface and top
border. The Send button remains at least 44×44 pixels.

At narrow widths or 200% zoom it becomes one column. Mobile rules include the
existing bottom-navigation safe-area spacing and prevent the composer from
covering the fixed navigation.

### 6.5 Preferences

- Dark mode gets explicit readable incoming/outgoing colors.
- Reduced motion disables smooth scrolling/transition declarations.
- Print removes sticky positioning, neutralizes bubble colors and hides the
  composer/live-only status while retaining sender, body and time.

## 7. JavaScript design

### 7.1 Initialization boundary

`conversation.js` exits immediately when `#chat-shell` or required hooks are
absent. The conversation template loads it through a new base `scripts` block,
so unrelated pages do not fetch or execute it.

### 7.2 Local time

For each `time[data-utc-time]`:

1. parse the ISO value;
2. reject invalid dates without changing fallback text;
3. format hour/minute with `Intl.DateTimeFormat` and `hour12: true`;
4. set a complete localized date/time title or accessible label; and
5. mark the element localized to prevent repeated work.

The same function handles initial and appended messages.

### 7.3 Poll scheduler

Use recursive `setTimeout`, not `setInterval`:

- normal delay: 3,000 milliseconds;
- schedule only after the current request and response work completes;
- no request while `document.hidden`;
- one immediate request after the document becomes visible;
- one `AbortController` for the active request; and
- abort on `pagehide`/unload.

If `has_more` is true, schedule the next bounded batch immediately before
returning to the three-second rhythm.

### 7.4 Request rules

Construct the URL with `URL`/`URLSearchParams` using the trusted endpoint and
monotonic cursor. Fetch with:

- `credentials: "same-origin"`;
- `Accept: application/json`;
- `cache: "no-store"`; and
- the active abort signal.

Redirected login HTML, non-JSON content, 401/403/404, or malformed data stops or
recovers according to MM-029 without exposing raw response text.

### 7.5 Complete-batch validation

Before changing the DOM, validate:

- top-level object and exact required batch types;
- messages is an array of at most 50;
- every ID is a safe positive integer;
- body and username are strings within database/model bounds;
- `is_own` is boolean;
- time/fallback values are bounded strings and parse safely;
- IDs are strictly increasing within the response; and
- `latest_id` never moves backward.

If any member is invalid, append none of that batch.

### 7.6 Safe append and deduplication

Initialize a `Set` from existing `data-message-id` values. For each validated
new ID not in the set:

- create list item, article, sender, body and time nodes;
- assign classes from `is_own`;
- set body/username with `textContent` only;
- set time attributes from the validated value;
- append in response order; and
- add the ID to the set.

Do not use `innerHTML`, `insertAdjacentHTML` or inline event attributes.

### 7.7 Scroll and status

Before appending, calculate whether the reader is within roughly 80 pixels of
the bottom.

- Near bottom: append, then set scroll position to the new bottom.
- Scrolled up: preserve position and announce **New messages arrived.**
- Initial latest view: move directly to the bottom after layout.
- Reduced-motion preference: never request smooth scrolling.

Temporary network/server problems show **Waiting to reconnect…** and reschedule.
The first later success clears that text. Session/authorization loss stops the
scheduler and shows the approved session-ended message.

### 7.8 Read-marker form

When a higher message ID is appended, update only the explicit read form's
hidden `message_id` value. Never click, submit or fetch the read endpoint.

## 8. Test-first plan

Tests will be written before any implementation file is edited.

### 8.1 Focused integration tests — `tests/test_modern_chat.py`

#### Rendering and ownership

1. Participant sees outgoing and incoming classes based on the session.
2. Forged form/query sender values cannot change ownership.
3. Sender label, body, semantic time and stable message ID are present.
4. Script-like/Unicode/long-word bodies are escaped and readable.
5. Empty conversation has a stable transcript and valid cursor zero.

#### Latest/older blocks

6. Zero, one, 50, 51 and 101 messages produce correct page counts/blocks.
7. Page 1 contains the newest 50 but displays oldest-to-newest.
8. Older pages contain no duplicates/gaps and polling is disabled.
9. Invalid/out-of-range page values retain existing 400/404 rules.
10. A successful reply from any history page redirects to the latest view.

#### Updates authorization and validation

11. Buyer and seller receive the same conversation messages with different
    `is_own` values.
12. Anonymous response contains no private message data.
13. Unrelated authenticated user receives non-revealing 404.
14. Missing/duplicate/empty/signed/spaced/decimal/Unicode/oversized/overflow
    cursors receive safe 400 JSON.
15. A cursor from another conversation does not disclose that conversation and
    behaves only as a number.

#### Response contract

16. Zero updates returns empty list, unchanged latest cursor and false
    `has_more`.
17. One/many updates return stable order and exact allow-listed fields.
18. Fifty-one updates return 50 plus `has_more`, then the next cursor catches up
    without duplicates.
19. Equal timestamps are ordered by ID.
20. `created_at` is canonical UTC and fallback time uses 12-hour UTC.
21. `Cache-Control` includes `no-store`.
22. Email, hashes, tokens, IDs not allow-listed and unrelated bodies are absent.

#### Read-only and query bounds

23. Snapshot all relevant table counts/content before and after repeated polls;
    no row or read marker changes.
24. Monkeypatch write-related helpers to fail if polling calls them.
25. Poll query count stays constant for 0, 50 and 1,000 stored messages.

#### Policy regressions

26. Sold conversation remains readable/sendable.
27. Archived conversation remains readable and has no composer; reply is still
    rejected server-side.
28. CSRF, request-token replay, rate limit and read-marker isolation stay Green.

### 8.2 Client/static tests — `tests/test_modern_chat_assets.py`

Tests inspect the final template/CSS/JavaScript for structural contracts:

- semantic ordered transcript and polite status region;
- outgoing/incoming class hooks and semantic time;
- no message-body `safe` filter;
- base page-specific scripts block and conversation-only script load;
- sticky composer grid, 44-pixel control, wrap/overflow/mobile/dark/print rules;
- exact 3,000 ms scheduler;
- recursive timeout and in-flight guard rather than overlapping interval;
- visibility pause/resume and abort cleanup;
- same-origin/no-store fetch options;
- complete-batch validation and 50-message bound;
- known-ID set and monotonic cursor;
- DOM node creation plus `textContent`;
- absence of `innerHTML`/`insertAdjacentHTML` for chat creation;
- scroll threshold and polite reconnect/session text;
- no automatic read-form submission; and
- local-time formatter with invalid-date fallback.

Static tests do not claim to execute browser behavior; the browser fixture does.

### 8.3 Red validation

After writing the two focused files:

1. collect them successfully;
2. run them against the unchanged application;
3. confirm failures are caused by the absent endpoint, markup, CSS and script—not
   broken fixtures or unrelated errors;
4. record counts and representative failures in `tests/029-red-verification.md`;
5. do not weaken assertions to make the Red stage easier; and
6. only then begin implementation.

## 9. Implementation sequence after Red

1. Add server cursor/time serialization helpers.
2. Add latest-block thread query and view context.
3. Add participant-only update endpoint and no-store response.
4. Replace conversation template with semantic chat shell.
5. Add the base page-specific script block.
6. Add conversation CSS and responsive/preference rules.
7. Add `conversation.js` in small units: time, validation, node creation,
   polling, visibility, scroll, status and cleanup.
8. Run focused tests after each meaningful layer.
9. Refactor only while focused tests stay Green.

No schema/data command will be run because MM-029 has no migration.

## 10. Related regression plan

After focused Green, run at least:

- existing marketplace messaging journeys;
- hardening/CSRF/concurrency/message-correction tests;
- Dashboard unread-count tests;
- mobile navigation tests;
- authentication and privacy tests;
- Shop Assistant tests, because both features have chat-like CSS/JavaScript;
- live search/cart/product tests for global template/script regression; and
- the complete pytest suite.

Also run:

- Python compilation;
- dependency consistency with `pip check`; and
- a check proving no migration head/schema change was introduced.

## 11. Browser fixture and verification

### 11.1 Isolated fixture

`tests/preview_modern_chat.py` will create:

- a temporary SQLite database under the project test-temp area;
- fictional buyer and seller accounts;
- one active, one sold and one archived product/conversation;
- alternating, equal-time, long-word, Unicode and harmless HTML-like messages;
- more than 50 messages for history navigation; and
- a fixture-only CSRF-protected control that inserts an incoming temporary
  message in a second browser tab.

The fixture will never read or write the real development database.

### 11.2 Browser story

Verify:

1. login as the fictional buyer;
2. outgoing bubbles are right/blue and incoming bubbles left/grey;
3. all bubbles show readable time and full semantic timestamp;
4. latest view begins near the bottom;
5. an incoming fixture message appears within the next polling cycle without a
   full-page navigation;
6. repeat/overlapping polls create no duplicate;
7. near-bottom view follows the message;
8. scrolled-up view retains position and announces a new message;
9. temporary fixture failure shows reconnect and later recovers;
10. archived conversation has no Send composer;
11. disabling/removing the chat script leaves readable bubbles and normal POST
    form behavior;
12. keyboard reaches history, read action, input and Send in logical order;
13. 320/360-pixel viewport and 200% zoom do not overlap mobile navigation when
    supported by the browser tool;
14. dark/reduced-motion checks are performed where supported; and
15. browser console has no JavaScript errors.

No real message will be sent during browser verification.

## 12. Acceptance-criteria traceability

| Acceptance criteria | Main evidence |
| --- | --- |
| AC-029-01 | Ownership/rendering integration tests, CSS static checks, buyer/seller browser view |
| AC-029-02 | Time serializer/markup tests, localization static checks, browser timestamps |
| AC-029-03 | 0/1/50/51/101 latest/older block tests and browser history navigation |
| AC-029-04 | Buyer/seller/anonymous/unrelated/cross-conversation endpoint matrix |
| AC-029-05 | 50/51 response, allow-list, no-store and database snapshot tests |
| AC-029-06 | Scheduler/visibility/in-flight static tests and timed browser append |
| AC-029-07 | Cursor/dedup static tests, two-batch integration and repeat-poll browser check |
| AC-029-08 | Escaping integration, text-node static test and harmless HTML browser message |
| AC-029-09 | Scroll/static hooks and browser near-bottom/scrolled-up stories |
| AC-029-10 | Failure-state static contracts and browser reconnect/recovery |
| AC-029-11 | Composer markup/CSS plus existing CSRF/replay/rate/archive integration tests |
| AC-029-12 | Read-form cursor/static non-submit checks and read-marker snapshots |
| AC-029-13 | Server-rendered template/static assertions and no-script browser story |
| AC-029-14 | Accessibility/CSS contracts and supported keyboard/mobile/zoom/theme checks |
| AC-029-15 | Related regression and complete pytest suite |
| AC-029-16 | No migration diff, temporary fixture paths and real-data before/after counts if needed |

## 13. Edge-case matrix

| Case | Expected result |
| --- | --- |
| No messages | Empty transcript, cursor 0, composer available unless archived |
| Exactly 50 messages | One latest block, chronological display, no older link |
| 51 messages | Newest 50 on page 1, oldest one on older page, no overlap |
| Same timestamp | Lower ID appears first within chronological display |
| Same message returned twice | One DOM bubble because ID is already known |
| New batch while request active | No second request starts |
| More than 50 waiting | Bounded first response, immediate bounded catch-up |
| User switches tab | Polling pauses; one request occurs on return |
| User reads older page | No polling; explicit return-to-latest link |
| User scrolls up | Position preserved; polite new-message status shown |
| Network fails | Existing transcript remains; reconnect status; later retry |
| Session expires with draft text | Poll stops; draft stays in textarea; no forced redirect |
| Conversation guessed | Non-participant gets no message or existence detail |
| HTML-like body/username | Displayed as literal text, never executed |
| Sold product | Conversation and composer remain available |
| Archived product | History remains, composer absent, POST still rejected |
| JavaScript unavailable | Server bubbles/times/history/form continue working |
| Mobile bottom bar present | Composer and final bubble remain above/reachable |

## 14. Risks and controls

| Risk | Control |
| --- | --- |
| Polling leaks private messages | Participant check on every request; non-revealing denial; privacy tests |
| XSS from appended body | Exact JSON validation, DOM creation and `textContent` only |
| Duplicate/out-of-order bubbles | Known-ID set, strictly ordered batch, monotonic cursor |
| Server load from three-second polls | Visible latest page only, one in flight, max 50, indexed bounded query |
| Polling changes unread data | GET has no write path; before/after database snapshots |
| Sticky composer covers content/mobile bar | Shell-owned sticky layout, transcript padding, narrow viewport tests |
| Session redirect replaces unsent draft | Detect HTML/redirect, stop polling and show local status only |
| New global CSS breaks Shop Assistant | Chat-prefixed selectors and related assistant regression tests |
| Pagination loses/skips rows | 50/51/101 and equal-time test matrices with ID tie-breaker |
| Tests overclaim browser behavior | Separate static, integration and browser evidence with honest limitations |

## 15. Rollback boundary

MM-029 can be rolled back without data conversion:

1. remove the updates route and chat helpers;
2. restore the previous conversation template/query;
3. remove `conversation.js` and chat CSS; and
4. remove the base scripts block if no other feature uses it.

Existing conversations and messages remain intact because no schema or stored
message format changes.

## 16. Definition of done

PLAN-029 is complete only when:

1. valid focused Red evidence predates implementation;
2. every AC-029 item maps to passing or honestly limited evidence;
3. authorization, JSON allow-list, no-store and read-only polling checks pass;
4. latest/older blocks contain no gaps or duplicates;
5. bubble ownership, timestamps, composer and no-script fallback pass;
6. polling appends safely, never overlaps and handles hidden/session/failure
   states;
7. CSRF, replay, rate-limit, archive and read-marker behavior remains Green;
8. focused, related regression and full pytest suites pass;
9. compilation, dependency and no-migration checks pass;
10. isolated browser checks pass to the supported extent with no console errors;
11. real database messages remain unchanged by verification; and
12. specification, plan, evidence, matrix and beginner guide statuses are
    accurate.

## 17. SDD checkpoint and approval record

MM-029 was explicitly approved by the user on 2026-11-07.

PLAN-029 was explicitly approved by the user on 2026-11-07. The focused tests
were collected and validated Red before implementation. The implementation,
regression, full-suite and isolated browser checks are complete; see
`tests/029-green-verification.md`.

