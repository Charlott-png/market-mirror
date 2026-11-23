# Market Mirror: Specifications for Phases 3–10

Status: **APPROVED — user approved the package and continued implementation on 2026-10-25**

Document ID: MM-003–016 package, version 1.0

This package turns the approved phase roadmap into concrete feature rules.
Approval of the roadmap established the direction; this package defines the
behaviour, limits, permissions, data, and acceptance criteria for the remaining
features. Existing MM-001, MM-002, and quality documents remain part of the project.
Approval was explicitly recorded in the conversation after the draft was created.

## Reading and approval

Read one numbered specification at a time. The first six features create the
marketplace; the last features prepare data, add AI, deploy, and demonstrate it.
You can approve the whole package or request changes to individual features.
After approval, each feature receives an implementation/test plan, pytest tests,
an observed Red result, implementation, and Green evidence, in that order.
The roadmap's “execute Phases 1–10” instruction authorizes work on this path;
it does not supply missing hosting credentials or prove unperformed acceptance tests.

## Shared requirements for every feature

G-01. Continue using Flask, server-rendered Jinja pages, SQLAlchemy, Alembic,
SQLite locally, and pytest. New packages must have a concrete feature purpose.

G-02. All state changes use POST forms with valid CSRF tokens. GET requests are
read-only. A missing or invalid CSRF token returns 400 and changes no data.

G-03. The authenticated session supplies identity. Never trust posted owner,
sender, user, or seller IDs. Unauthenticated HTML requests to protected pages
redirect to login. Unauthorized private resources return 404 to avoid revealing
their existence. Valid authentication with an invalid public operation returns
a field error (400), conflict (409), or explicitly specified response.

G-04. Plain text remains escaped in templates, including titles, descriptions,
biographies, messages, search terms, and AI explanations. No user HTML is rendered
as trusted markup. SQL uses parameters and fixed sort/column mappings.

G-05. Existing username, price, category, condition, currency, and status limits
remain authoritative. Prices are Decimal dollars in Python and cents in SQLite.
All times are UTC. Stable ordered lists use ID as a final tie-breaker.

G-06. Forms show field errors and preserve safe non-secret values on failure.
Passwords are never echoed. A failed transaction rolls back and leaves no partial
state. Generic public errors contain no exception text, credentials, or paths.

G-07. Labels, visible keyboard focus, semantic headings, text status indicators,
and readable layouts at 320 pixels and 200% zoom are required. Images have useful
alt text. Success, error, empty, and loading/unavailable states must be intentional.

G-08. Tests use only their own temporary databases, upload directories, clocks,
and model artifacts. They do not depend on network access or a running web server.
The earlier regression suite remains part of every final feature run.

G-09. Every implementation has a beginner guide explaining its data flow, key
functions, concepts, and a small hands-on exercise. Technical completion and the
student's ability to explain it are separate checkpoints.

G-10. No checkout, payments, delivery, auction, public API, mobile app, social
login, or live socket messaging is included. Public deployment requires the
Phase 9 operational checks and an explicitly selected hosting destination.

## MM-003 — Accounts, login, logout, and profile editing

Phase: 3. Depends on: MM-002 Green.

Purpose: An account identifies the person performing a marketplace action.
Authentication verifies identity; authorization controls what that identity may do.

### Interfaces and data

| Interface | Access | Result |
|---|---|---|
| GET/POST `/auth/register` | Anonymous | Registration form / account creation |
| GET/POST `/auth/login` | Anonymous | Login form / session creation |
| POST `/auth/logout` | Signed in | Session cleared, redirect home |
| GET/POST `/account/profile` | Signed in | Edit current account's biography |

Registration requires username, email, password, and matching confirmation.
Username is 3–30 ASCII letters/numbers/underscores/hyphens, normalized lowercase.
Email is trimmed, lowercase, at most 254 characters, and structurally validated
without a network deliverability check. Password is 12–128 characters, permits
spaces and Unicode, is not trimmed, and is hashed with Werkzeug's scrypt method.
The database stores only the resulting hash. Registration does not log the user in;
it redirects to login after successful creation.

Login accepts email and password. Wrong email and wrong password give the same
message, “Invalid email or password.” An unknown email still performs a dummy
hash verification. Successful login clears prior session data before setting the
authenticated identity. No “remember me” in this release. Sessions expire after
eight hours and logout is a CSRF-protected POST.

Login redirects may only target a relative path beginning with one `/`, excluding
`//`, backslashes, and control characters. Invalid targets use the account page.

Only biography is editable (0–500 characters, empty stored as NULL). Username,
email, and password changes require a later specification. Public seller profiles
are introduced in MM-007. Email verification and password recovery are excluded
from the classroom release and must be disclosed as deployment limitations.

Login attempts use a persistent throttle: at most five failed attempts per
normalized account key in 15 minutes, plus at most 30 attempts per client address
in 15 minutes. Registration allows five attempts per address per hour. Stored
throttle keys are HMAC digests, not raw emails or addresses. Exceeding a limit
returns 429 with Retry-After. Trusted proxy configuration must be explicit;
arbitrary forwarded headers cannot choose the client address. Tests inject time.

SECRET_KEY is loaded from the environment, required outside tests, and not
committed. Cookies are HttpOnly and SameSite=Lax; deployed HTTPS enables Secure.

### Acceptance criteria

- AC-003-01: Valid registration adds one normalized user; the stored hash differs
  from the password and verifies correctly. Invalid lengths and mismatched
  confirmation add none.
- AC-003-02: Duplicate normalized identity fails safely, including a simulated
  uniqueness race. Raw SQL/private values do not appear in the response.
- AC-003-03: Login grants access; anonymous access redirects; logout and expiry
  revoke it. Session tampering never authenticates a user.
- AC-003-04: CSRF failure, unsafe redirect, login throttling, and expired throttle
  windows behave as specified using an injected clock.
- AC-003-05: Profile edits affect only the current user's biography. Forged identity
  fields cannot change another account or immutable fields.

## MM-004 — Listing management and lifecycle

Phase: 4. Depends on: MM-003 Green.

Purpose: A seller controls their own products. The server enforces ownership even
when somebody manually changes a URL or hidden form field.

### Interfaces and behaviour

| Interface | Access | Result |
|---|---|---|
| GET/POST `/listings/new` | Signed in | Create listing |
| GET/POST `/listings/<id>/edit` | Owner | Edit content |
| GET `/listings/<id>/preview` | Owner | See any owned status |
| POST `/listings/<id>/status` | Owner | Explicit lifecycle transition |
| GET `/account/listings` | Signed in | Own listings, paginated by status |

Creation accepts title, description, decimal price text, category, and condition.
Currency is server-set USD; seller comes from the session; status starts active.
Decimal parsing rejects float conversion, signs for negative values, comma/symbol
formats, NaN, infinity, more than two fractional digits, and out-of-range prices.
Limits match MM-002. No image handling until MM-005.

Allowed status transitions: active→sold, active→archived, sold→archived,
archived→active. Sold→active is rejected; a seller may archive and explicitly
reactivate a listing if they intend to offer it again. Repeating the current state
is a no-op. Only active and archived listings permit content edits. A sold listing
requires archival before editing. Physical product deletion is excluded: the
“remove” operation archives it, preserving future message and save relationships.

Ownership is immutable. Each submitted edit/status operation includes the last
seen update version; a stale version returns 409 and preserves the newer record.
The comparison and update must be atomic. Creation uses a per-user unique form
request token; replay of the same submission returns the original successful
result rather than a second row. Tokens and persistence require a migration.

### Acceptance criteria

- AC-004-01: A valid submission creates exactly one active listing with the
  authenticated seller. Forged seller, currency, status, or ID is not accepted.
- AC-004-02: Anonymous and unrelated users cannot mutate, edit, or preview it.
- AC-004-03: Every allowed/disallowed status pair is tested, including repeated
  state and two conflicting edits. Archival preserves the row and owner.
- AC-004-04: Boundary/invalid inputs preserve safe form values and write no row.
  Duplicate creation token yields one listing, including concurrent attempts.
- AC-004-05: Own-listings views use 20 per page, newest then ID, and never include
  another user's rows or totals.

## MM-005 — Product images

Phase: 4. Depends on: MM-004 Green.

Purpose: Show products while safely handling files supplied by users.

One optional image is allowed per product. Accept decoded JPEG or PNG only;
maximum file size is 5 MiB, request size 6 MiB, and decoded image area 12 million
pixels. Reject zero-byte, corrupt, animated, SVG, unsupported, or oversized files.
File names and claimed MIME types are not sufficient evidence of image content.

Apply EXIF orientation, resize within 1600×1600 preserving aspect ratio, remove
metadata, flatten transparent pixels on white, and re-encode JPEG. Store a random
UUID `.jpg` filename under configured storage, outside the source tree. Ignore
the original name for storage. User-supplied path components are never used.

Image replacement stages and validates the new file, moves it to a unique final
name, updates the row, and commits. On commit failure remove the new file and
retain the old reference. Remove the old file only after successful commit.
A reconciliation command reports orphan/missing files; deletion requires a
separate explicit flag, confined to the configured storage root. Crash recovery
must not require erasing other uploads.

GET `/media/products/<filename>` serves only images belonging to active or sold
products, or to the authenticated owner of archived products. Missing/unauthorized
files return 404. Responses use image/jpeg and nosniff. Archived images must not
remain publicly served through an unprotected static folder; caching policy must
avoid continued public exposure after a status change.

### Acceptance criteria

- AC-005-01: Valid portrait/landscape/rotated JPEG and PNG produce correctly
  oriented, bounded JPEGs with metadata removed.
- AC-005-02: Oversize bytes/pixels, disguised executable, corrupt, empty, animated,
  and traversal/reserved/duplicate names fail without overwriting any file.
- AC-005-03: Inject disk-write, move, and database failures. The existing image
  remains usable and rollback/reconciliation handles new orphan files safely.
- AC-005-04: A missing image produces a placeholder; alt text names the product.
  The detail/list layout remains readable at narrow widths.
- AC-005-05: Anonymous access to archived images and path traversal returns 404.

## MM-006 — Browse, search, filters, and pagination

Phase: 5. Depends on: MM-004 Green; MM-005 supplies images when available.

GET `/products` is public. Only active products enter its base query, including
counts. Parameters: `q` (trimmed, ≤120 characters), `category`, `condition`,
`min_price`, `max_price`, `sort`, `page`. Duplicate parameter keys return 400.
Unknown parameters are ignored and not propagated. Empty search means all active
items. Invalid known filters or page syntax return 400 with guidance; a valid
positive page beyond the last page returns 404, except empty page 1 returns 200.

Text search is case-insensitive for ASCII and matches literal title/description
substrings. `%` and `_` are escaped as literal characters. Non-ASCII text must not
crash or be corrupted, but full multilingual case folding is a documented limit.
All active filters are combined with AND. Price bounds use Decimal values and
must be positive, in range, and minimum≤maximum.

Sort keys: `newest` (created time descending), `price_asc`, `price_desc`.
Each adds a deterministic ID tie-breaker. Use 20 products per page; the client
cannot enlarge the page size. Pagination links retain validated search/filters.
Product cards show public title, price/currency, condition, category, image, and
seller username only. Empty results offer a way to clear filters.

### Acceptance criteria

- AC-006-01: Empty, ordinary, Unicode, wildcard, SQL-like, and HTML-like searches
  obey matching rules and never execute SQL or script input.
- AC-006-02: Filter intersections, inclusive price boundaries, inverted ranges,
  unsupported sort keys, duplicate keys, and invalid pages are tested.
- AC-006-03: Stable datasets paginate without duplicates or omissions, including
  identical prices/timestamps. Only active items appear in cards and totals.
- AC-006-04: Query count for one results page stays bounded as catalogue size
  increases; benchmark timings record environment and fixture size.

## MM-007 — Product details and public seller profiles

Phase: 5. Depends on: MM-006 Green.

GET `/products/<id>` shows an active or sold product. Sold products display an
unavailable banner and disable new contact/save actions. Archived or missing
products return 404 publicly; owners use MM-004 preview.

GET `/sellers/<username>` shows normalized public username, escaped biography,
join date, and active products at 20 per page. Email, hash, activity history,
messages, and private totals never appear. A nonexistent seller returns 404;
an empty existing profile returns a helpful 200 page.

No behavioural collection occurs until MM-009's opt-in policy is available.
Displaying a product alone does not authorize tracking anonymous visitors.

### Acceptance criteria

- AC-007-01: Anonymous, owner, and unrelated user request active/sold/archived/
  nonexistent IDs. Each receives the exact visibility outcome above.
- AC-007-02: Unique email/hash canaries never appear in public HTML.
- AC-007-03: Missing optional images and biography do not break either page.
- AC-007-04: Profiles with zero, one, and many active products paginate correctly;
  sold and archived rows do not leak into the public catalogue.

## MM-008 — Private buyer–seller messaging

Phase: 6. Depends on: MM-003, MM-004, MM-007 Green.

Tables: `conversations` (id, product_id, buyer_id, seller_id, created_at),
`messages` (id, conversation_id, sender_id, body, created_at, request_token),
and per-participant read markers (conversation_id, user_id, last_read_message_id).
Foreign keys restrict deletion. Conversation uniqueness is `(product_id,buyer_id)`;
seller is derived from immutable product ownership. Message request tokens are
unique per sender. Database and service checks prevent a buyer being the seller.

POST `/products/<id>/contact` requires an active product and first plain-text
message. It gets or creates the one conversation and records the first message
transactionally. Self-contact returns 400. An existing conversation is reused.
GET `/messages` lists the current user's conversations, 20 per page. GET
`/messages/<id>` shows the selected conversation, 50 messages per page ordered by
UTC creation time then ID. POST `/messages/<id>/send` adds a reply. POST
`/messages/<id>/read` advances only that participant's read marker; GET is read-only.

Only its buyer and seller can read or post. Message length after trimming is
1–2000 characters. Text is escaped; line breaks are preserved as text. The server
sets sender and time. New contact is blocked after sale/archival. Existing
conversations remain readable; replies are allowed for sold products, but archived
product conversations are read-only. The status is rechecked when saving.

Limit sending to 20 messages per user per ten minutes using persistent counters.
Repeat request tokens return the original result without another message.
Notifications are in-app counts; no email delivery, attachments, or live sockets.

### Acceptance criteria

- AC-008-01: Only the two participants can list/read/reply; third-party ID guessing
  and forged sender fields never expose or write private data.
- AC-008-02: Self-contact and nonactive new contact fail without partial rows.
- AC-008-03: Duplicate/concurrent starts produce one conversation. Replayed
  messages produce one message. Transaction failure leaves no partial start.
- AC-008-04: Empty/huge/script text, CSRF failures, throttling, and status changes
  between form loading and submission obey the rules.
- AC-008-05: Equal timestamps order deterministically; read markers do not affect
  the other participant and cannot claim another conversation's message ID.

## MM-009 — Saved products and optional interaction history

Phase: 6. Depends on: MM-007 Green; contact events depend on MM-008.

`saved_products` stores user_id, product_id, and UTC created_at with a unique pair.
POST `/products/<id>/save` expresses desired saved state; POST `/products/<id>/unsave`
expresses unsaved state. Repeating either is successful and creates no duplicates.
Saving requires an active product owned by someone else. Unsaving is allowed for
any of the current user's saved relationships, including unavailable products.
GET `/saved` displays 20 per page with a newest-save/ID order.

When a saved item is sold/archived, show an “Unavailable product” placeholder and
an unsave action without exposing archived details or images. Preserve the relation
until the user removes it. Own-product saves return 400; hidden/missing saves 404.

Optional behavioural events require an explicit profile opt-in, default off.
`interaction_events` records only user_id, product_id, type, UTC time; types are
view/save/contact. Do not record IP, device identifiers, free text, or anonymous
visitors. Owner views are excluded. Deduplicate each user/product/type in a
30-minute window. Retain 90 days; a documented purge command removes older rows.
Turning opt-in off deletes that user's events and invalidates personalization.
The essential saved relation remains because it is a requested user feature.

View events use a separate CSRF-protected POST after a visible page view; GET
does not mutate. Failure of optional event recording must not undo a successful
save or contact. Identity and time are always server-assigned.

### Acceptance criteria

- AC-009-01: Double/concurrent save yields one row; double unsave leaves none.
- AC-009-02: Only the current user's saved page is visible; own/hidden items follow
  the policy and unavailable placeholders contain no private metadata.
- AC-009-03: GET and invalid CSRF cannot mutate saves or history.
- AC-009-04: Default opt-out creates no events; opt-in deduplicates correctly;
  opt-out deletes only that user's history; retention uses an injected clock.
- AC-009-05: Event-write failure leaves successful core actions intact.

## MM-010 — Personal dashboard and usability

Phase: 6. Depends on: MM-004, MM-008, MM-009 Green.

GET `/dashboard` requires authentication. Show current user's listing totals by
status, saved total, unread-conversation count, five most recently updated own
listings, and five recent conversations. Links lead to paginated dedicated pages.
Numbers use authoritative database queries, not stale session values. Ignore
submitted/query-string user IDs; identity always comes from the session.

Empty accounts see zero counts and labelled next actions. Use text labels for
statuses rather than color alone. Deleting/archiving/changing related content must
update the next rendered totals. Refactoring must preserve existing route/data
contracts and cannot introduce unrelated feature changes.

### Acceptance criteria

- AC-010-01: Two populated accounts never see each other's private counts or rows.
- AC-010-02: A new account renders 200 with zero counts and usable navigation.
- AC-010-03: Mutating each listing/save/read state changes the corresponding
  summary on the next request, while unrelated counters remain correct.
- AC-010-04: Query count stays bounded with 1000 owned records. Keyboard-only
  and 320-pixel/200%-zoom walkthroughs can complete the main actions.

## MM-011 — Datasets, baselines, and reproducible evaluation

Phase: 7. Depends on: marketplace MVP Green (MM-003–010).

Purpose: Prepare data before measuring AI. A model must be evaluated on examples
it did not learn from. Synthetic examples prove mechanics, not real-market accuracy.

Dataset fields: product_id, duplicate_group, title, description, category,
condition, currency, price, source, licence/provenance, collected_at, synthetic.
No account identifiers, email addresses, messages, or private behavioural history
are included in the catalogue training dataset. Each dataset receives a SHA-256
fingerprint and a data card describing source, permissions, cleaning, limits,
label distribution, and whether prices are listing prices or sale prices.

Provide a deterministic synthetic fixture for demonstrations and tests, clearly
marked synthetic. An external dataset may be incorporated only with verified
permission and provenance. No paid acquisition or broad website scraping is
authorized by this specification. Insufficient real data must be reported honestly.

Validation checks required fields, allowed keys, positive exact two-decimal USD
prices, duplicates, empty text, and extreme values. Quarantine invalid rows with
reason counts. Do not silently invent category labels or replacement prices.
Normalize text only according to documented rules. Duplicate/near-duplicate groups
must not cross partitions. Split groups once with seed 42 into approximately
60% training, 20% validation, 20% test; save exact membership and class counts.
Require each evaluated category to appear in every partition and at least five
independent groups per category; otherwise stop with an insufficient-data report.

All learned transforms fit only training data inside a pipeline. Tune on
validation data. Freeze configuration before one final test evaluation; if changes
are made afterward, label the result exploratory rather than untouched test evidence.

Category baseline: most frequent training category. Price baseline: median of
training prices by category/condition, falling back to category then global median.
Recommendations baseline: active recent items with category diversity.

### Acceptance criteria

- AC-011-01: A known dirty fixture produces exact error counts and clean output;
  missing provenance fails validation.
- AC-011-02: Repeated runs reproduce fingerprints, split memberships, and baseline
  metrics. Duplicate groups are disjoint across partitions.
- AC-011-03: Tests prove preprocessing learns only training rows; no target label,
  target price, IDs, or future interactions leak into predictors.
- AC-011-04: Reports include class counts, baseline metrics, split version, random
  seed, limitations, and synthetic status. No invented result is accepted.

## MM-012 — Category suggestions

Phase: 8. Depends on: MM-011 Green and MM-004 listing forms.

Train a TF-IDF plus logistic-regression classifier on title and description,
predicting the seven approved categories. Training is an explicit offline command,
never performed during a web request. Artifacts record package versions, training
data fingerprint, feature schema, categories, and evaluation report.

POST `/ai/category` requires authentication and CSRF, accepts bounded title and
description, and returns a suggested key/label, model version, and score. The score
is a model estimate, not a calibrated probability claim. Default abstention
threshold is 0.60, frozen before final test evaluation. Empty text, no recognized
features, missing/incompatible artifacts, or score below threshold produces a
successful “No confident suggestion; choose a category” result with no forced value.

The seller must explicitly apply or choose a category; suggestions never save a
listing by themselves. Record acceptance/correction only under the approved
optional event/data policy; do not add private free-text telemetry.

Evaluate macro-F1, accuracy, per-class precision/recall/F1, confusion matrix,
coverage (fraction receiving suggestions), and accuracy among suggested items.
The trained model must exceed the majority baseline's macro-F1 on the same test
split. If it does not, report this and keep manual selection available without
claiming useful learned performance.

### Acceptance criteria

- AC-012-01: All outputs map to approved categories; empty/OOV/low-score text
  abstains. A forged output cannot overwrite listing fields.
- AC-012-02: Missing/corrupt/wrong-schema artifacts produce fallback, while product
  creation still succeeds manually.
- AC-012-03: Reports compare identical held-out rows against the baseline and
  include per-class metrics and confusion matrix.
- AC-012-04: Fixed artifacts yield deterministic predictions; request handlers
  do not call training. Only trusted local artifacts are loaded.

## MM-013 — Price suggestions

Phase: 8. Depends on: MM-011 Green; category may be selected manually.

Train an understandable regression pipeline from title/description, category,
and condition. Exclude asking price, sold price, identifiers, and future outcomes
from inputs. Begin with a Ridge regression candidate and compare against the
training-only median baseline on the same split.

POST `/ai/price` requires authentication/CSRF. Input follows listing limits and
approved choices. Output is a positive two-decimal USD estimate, optional range,
method/model version, and a clear advisory label. These are suggested asking
prices, not guaranteed sale prices or independently verified market valuations.

For a supported category with at least ten training examples, use the approved
candidate if it improves validation MAE; otherwise use the category baseline.
For insufficient examples, show “Not enough data” and permit manual pricing.
Negative/non-finite/out-of-range predictions abstain rather than silently clipping.
A displayed range, if used, is based on the validation absolute-error percentile
and explicitly labelled an empirical error range, not a guaranteed confidence interval.
Changing the seller's final price always requires an explicit choice.

Evaluate test MAE in dollars, median absolute error, and per-category MAE with
sample counts. Also report the baseline and large-error examples. Synthetic-data
performance must not be presented as evidence of real market price accuracy.

### Acceptance criteria

- AC-013-01: Inputs reject invalid choices and malformed text; outputs obey
  currency/Decimal boundaries or abstain with a clear reason.
- AC-013-02: Small classes, missing/corrupt models, extreme outputs, and unseen
  text fall back safely without blocking listing creation.
- AC-013-03: Metrics match hand-calculated examples and compare identical held-out
  rows. No target price is present among input features.
- AC-013-04: Applying a suggestion is explicit and still passes ordinary server
  price validation; the saved price does not change in the background.

## MM-014 — Product recommendations

Phase: 8. Depends on: MM-007, MM-009, MM-011 Green.

Start with TF-IDF cosine similarity over public product title/description and
category. Product detail shows up to six similar active products. Exclude the
current item, duplicates, and the viewer's own listings; never recommend archived
or sold records. Use ID tie-breakers for equal scores and cap one seller at two
cards when enough candidates exist. A short reason identifies actual shared
category/description features without exposing other users' behaviour.

For an opted-in logged-in user, the home/dashboard may use a profile averaged
from their last 90 days of consented interactions, weighting view=1, save=3,
contact=4. Saved relationships alone do not authorize private tracking. Opt-out
users and cold starts get diverse recent active products. With few candidates,
show fewer cards; with none, show a useful empty state.

Similarity indexing is offline or explicitly refreshed; every recommendation
must re-check current product visibility when served so a stale index cannot
reveal hidden content. Missing/incompatible artifacts use the recent-item fallback.
Do not train on private messages or raw identity data.

Evaluate deterministic ranking fixtures and, where legitimate held-out interaction
data exists, precision@6, recall@6, catalogue coverage, and category diversity using
a time-respecting split. Without enough real interaction data, report ranking and
fallback checks plus a labelled synthetic demonstration, not a real-user metric.

### Acceptance criteria

- AC-014-01: Candidate lists never contain hidden, sold, current, duplicate, or
  viewer-owned items, including items archived after index construction.
- AC-014-02: Known similar items rank above unrelated ones in controlled fixtures;
  tie ordering and seller caps are deterministic.
- AC-014-03: New/opted-out users, empty catalogue, and unavailable models get the
  specified fallback without private-data exposure.
- AC-014-04: Opt-out removes personalization history and invalidates cached
  results. Evaluation respects time and labels synthetic limitations explicitly.

## MM-015 — Production preparation and deployment

Phase: 9. Depends on: approved feature suites Green. AI may use documented fallbacks.

Deliver production configuration, a reproducible dependency lock, PostgreSQL driver,
production WSGI server configuration, persistent media location, release checklist,
backup/restore instructions, and rollback instructions. A hosting provider, public
domain, billing arrangement, and real credentials are not yet selected. Local
deployment preparation may proceed after specification approval; publishing or
creating paid resources requires an explicit destination and authorization.

Production requires DATABASE_URL, SECRET_KEY, HTTPS, secure cookies, a trusted
host/proxy policy, debug disabled, bounded requests, safe error pages, and persistent
throttle storage. No development seed commands run in production. Migrations are
an explicit release step, not automatically run by every web worker.

Keep `/health`'s original exact public response as a liveness check. Add `/ready`
with only status and 200/503, checking database availability without exposing
details. Optional AI failure does not make the marketplace unready. Safe logs
include event type, request ID, status, and duration, not passwords, form bodies,
tokens, database URLs, email, private messages, or query-string content.

Privacy documentation explains saved data, messages, opt-in interactions, model
data, retention, limitations, and contact route for deletion requests. This release
does not expose self-service account deletion. An operator procedure must verify
the request, archive listings, disable login, erase personal biography/identity,
remove saved rows and events, and anonymize retained conversation authors while
preserving required relationships. Message-content erasure and backup expiry must
follow the published policy and deployment context; no claim of legal compliance
is made without appropriate review. Real-public-user launch waits until this
policy and abuse-reporting/operator responsibility are configured.

Backups cover PostgreSQL and uploads with a manifest, encryption/access controls,
and a tested restore into an isolated environment. A release rollback uses the
previous application artifact and schema compatibility; destructive downgrade is
never the default rollback. Test persistent uploads across process restart.

### Acceptance criteria

- AC-015-01: Missing required production settings fail startup clearly without
  revealing secret values. Debug errors and default secrets cannot reach production.
- AC-015-02: A fresh PostgreSQL instance migrates and passes core integrity,
  authentication, authorization, and money tests. SQLite and PostgreSQL outcomes
  agree at the application interface; raw cents are converted during data transfer.
- AC-015-03: HTTPS smoke journey succeeds on the selected host and uploaded files
  survive restart. Readiness correctly reports database failure/recovery.
- AC-015-04: Restore rehearsal verifies rows and media checksums in isolated
  storage. A rollback rehearsal records exact version and compatibility outcome.
- AC-015-05: Secret/private canaries are absent from logs/errors; privacy retention,
  report handling, and operator deletion procedures have documented rehearsal evidence.

If a host/credentials are unavailable, mark deployment **pending** with a specific
handoff. Do not describe configuration files as a successfully deployed service.

## MM-016 — Final report, evidence, and demonstration

Phase: 10. Depends on: all agreed core functionality and recorded deployment status.

Deliver a project report, architecture and database diagrams, specification-to-test
matrix, model/data cards, reproducible evaluation outputs, demo script, backup local
demo, and clean-install guide. Report feature status as implemented, deferred, or
not verified; do not hide unresolved acceptance criteria.

The main demo uses two controlled accounts. Seller creates a listing, reviews AI
suggestions, and keeps control of final values. Buyer searches, filters, saves,
and sends a message. Seller replies and marks sold. The demo then shows disabled
new-contact actions, recommendation fallback, an ownership denial, and test evidence.
Use fake personal data and do not display passwords or secret settings.

The report explains browser/server flow, ORM/keys, transactions, authorization,
image handling, CSRF/XSS/injection controls, train/test separation, each baseline,
actual metrics, limitations, and future work. Results must come from executed
tests/evaluations, not invented screenshots or assumed success.

### Acceptance criteria

- AC-016-01: A clean environment can follow the documented setup, migrations,
  controlled sample-data preparation, test run, and local startup.
- AC-016-02: A main and offline backup demo are rehearsed, and their actual
  outcomes are recorded with any limitations.
- AC-016-03: Every delivered feature maps to requirements and tests; every AI
  claim cites its saved dataset/split/artifact/evaluation version.
- AC-016-04: The student can explain the major concepts and answer practice
  questions. This criterion requires the student's participation and cannot be
  marked complete by the coding agent alone.

## Decisions approved by accepting this package

Approval accepts the concrete field limits, routes, visibility rules, state
transitions, retention/opt-in rules, AI baseline/abstention behaviour, and excluded
features above. It authorizes planning and subsequent test-first implementation
in dependency order under the user's execution request. Hosting selection, paid
resources, external data permissions, and the student's demonstration remain
explicit later inputs when they become necessary.
