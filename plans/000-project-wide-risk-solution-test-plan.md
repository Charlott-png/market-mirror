# Market Mirror: Project-Wide Risk, Edge-Case, Solution, and Testing Plan

| Field | Value |
|---|---|
| Plan ID | PLAN-QA-000 |
| Approved specification | MM-QA-000 version 1.0 |
| Coverage | Weeks 1–16 and cross-cutting quality |
| Status | Approved |
| Created | 2026-10-25 |
| Approved | 2026-10-25 |
| Context policy | Additive; MM-001 remains unchanged |

## 1. How to use this plan

This is a **risk map**, not permission to build every feature immediately. When a future feature begins, its specification must select the applicable issue IDs from this plan. Its implementation plan must map those issues to tests. Only then may tests and code be written.

Each row uses three solution layers:

- **Prevent:** stop the problem before it changes data or exposes information.
- **Detect:** make the failure visible through validation, logs, health checks, or metrics.
- **Recover:** return the user and system to a safe, understandable state.

Test abbreviations:

| Code | Test level | Meaning |
|---|---|---|
| `U` | Unit | Test one validator, model method, or service function in isolation |
| `I` | Integration | Test Flask route, database, template, or file behaviour together |
| `E2E` | End-to-end | Test a complete user journey across several features |
| `SEC` | Security | Test permissions, hostile input, secrets, or unsafe actions |
| `A11Y` | Accessibility | Test keyboard, labels, semantics, contrast, or responsive layout |
| `ML` | Machine learning | Test data, baselines, metrics, artifacts, drift, or fallback |
| `OPS` | Operations | Test deployment, startup, health, backup, or recovery |
| `M` | Manual | Repeatable human inspection where automation is not proportionate |

Priorities follow MM-QA-000: `P0` protects data/security, `P1` protects core journeys, `P2` improves resilience/usability, and `P3` is advanced future hardening.

## 2. Cross-cutting controls

These protections apply whenever the relevant type of feature appears.

| ID | Priority | Problem and impact | Required solution | Required tests | MVP decision |
|---|---|---|---|---|---|
| X-INPUT-001 | P1 · High · Likely | Empty, whitespace-only, oversized, Unicode, emoji, control-character, malformed, or locale-formatted values may bypass assumptions or damage page layout. | **Prevent:** central field limits, normalization rules, allow-listed choices, server validation. **Detect:** field-specific errors. **Recover:** keep safe user input and focus the first error. | `T-XINPUT-U1`: table-driven boundary values at below/min/max/above limits; exact boundary accepted and above rejected. `T-XINPUT-I1`: invalid form returns 400/200 form error without database change or reflected script execution. | Required |
| X-AUTHZ-001 | P0 · Critical · Possible | A user changes another user's listing, save, message, or profile by changing a URL/form identifier. | **Prevent:** load resource, verify current user ownership/participation server-side, then mutate. Hide buttons only for usability. **Detect:** safe warning log with user/resource IDs, not private content. **Recover:** 403 or non-revealing 404; no change. | `T-XAUTHZ-SEC1`: create owner, attacker, resource; attacker sends every read/write/delete request; expect 403/404 and unchanged row/file. `T-XAUTHZ-SEC2`: anonymous request redirects only to local login URL. | Required |
| X-CSRF-001 | P0 · Critical · Possible | Another site tricks a logged-in browser into posting a destructive request. | **Prevent:** CSRF token on every state-changing form; GET never mutates. **Detect:** rejected-token log without token value. **Recover:** 400/403 and unchanged data. | `T-XCSRF-SEC1`: omit, alter, and reuse an expired token for create/edit/delete/save/message; each rejected and state unchanged. | Required |
| X-DATA-001 | P0 · Critical · Possible | Duplicate submissions, races, partial commits, or stale edits create inconsistent data. | **Prevent:** database uniqueness/foreign keys, transactions, idempotent operations, optional version timestamp. **Detect:** integrity errors and rollback logging. **Recover:** rollback entire operation and show retry/current-state message. | `T-XDATA-I1`: two sessions perform same unique action; one logical record remains. `T-XDATA-I2`: force second database operation to fail; first operation must roll back. | Required |
| X-MONEY-001 | P1 · High · Likely | Floating-point prices produce rounding errors; locale/currency ambiguity misleads users. | **Prevent:** one documented currency, decimal database type, two decimal places, min/max rules. **Detect:** validation error. **Recover:** retain input for correction; never guess currency. | `T-XMONEY-U1`: test 0, negative, 0.01, 10.10, excessive decimals, commas, text, maximum, over-maximum. Assert stored/retrieved value is exact. | Required |
| X-TIME-001 | P2 · Medium · Likely | Local time, daylight saving, and equal timestamps produce incorrect order or confusing ages. | **Prevent:** store UTC-aware timestamps; convert only for display; add ID tie-breaker. **Detect:** reject naive timestamps in services. **Recover:** display exact date if relative calculation is unsafe. | `T-XTIME-U1`: values around midnight/DST and equal timestamps sort deterministically. `T-XTIME-I1`: created timestamp comes from server, not hidden client field. | Required |
| X-PRIV-001 | P0 · Critical · Possible | Emails, password hashes, private messages, behavioural history, secrets, or local paths leak into HTML, JSON, logs, or errors. | **Prevent:** explicit response fields, template review, log redaction, production error pages. **Detect:** automated forbidden-string scans in responses/log captures. **Recover:** rotate exposed secret, invalidate sessions, remove logs, document incident. | `T-XPRIV-SEC1`: request all public pages/API responses and assert forbidden fields absent. `T-XPRIV-SEC2`: trigger error with sensitive input and assert logs/error page omit it. | Required |
| X-A11Y-001 | P1 · High · Likely | Keyboard, screen-reader, low-vision, or mobile users cannot finish core journeys. | **Prevent:** semantic HTML, labels, error association, visible focus, alt text, adequate contrast, 320px reflow. **Detect:** automated HTML checks plus manual keyboard/zoom review. **Recover:** no critical action depends only on color, hover, drag, or JavaScript. | `T-XA11Y-M1`: complete register/list/search/save/message with keyboard at 200% zoom and 320px. `T-XA11Y-A1`: each input has accessible name; one H1; logical landmarks/order. | Required |
| X-PERF-001 | P2 · Medium · Possible | Unbounded queries, N+1 relationships, huge files, or per-request model loading make pages slow. | **Prevent:** pagination, indexes, eager loading, file limits, startup model cache. **Detect:** query-count and response-time measurements with seeded large data. **Recover:** smaller page, timeout, cached/fallback result. | `T-XPERF-I1`: seed 1,000 products/100 conversations; core list pages stay paginated and below agreed query count. `T-XPERF-ML1`: repeated prediction does not reload artifact. | Required in basic form |
| X-FAIL-001 | P1 · High · Possible | Database, storage, model, or configuration becomes unavailable and causes an unhandled crash or partial update. | **Prevent:** startup validation and narrow exception boundaries. **Detect:** health/log signal with safe message. **Recover:** rollback; show friendly error; optional AI uses deterministic fallback. | `T-XFAIL-I1`: inject database/storage/model failure at each boundary; expect no partial state, no stack trace to user, and documented fallback/status. | Required |
| X-TEST-001 | P1 · High · Likely | Tests pass for the wrong reason, share state, depend on order, or touch real data. | **Prevent:** isolated temporary DB/uploads, factories, explicit assertions, deterministic seed. **Detect:** random/reversed test order and fresh-process run. **Recover:** remove shared globals and rebuild fixtures. | `T-XTEST-1`: run each test alone and full suite twice; same result. `T-XTEST-2`: assert configured DB/upload paths are temporary before destructive fixture cleanup. | Required |
| X-SDD-001 | P1 · High · Likely | Code drifts away from approved behaviour or future work silently breaks earlier features. | **Prevent:** requirement IDs in specs/plans/tests; Red evidence before implementation; regression suite on every feature. **Detect:** traceability review. **Recover:** revert unapproved behaviour or create a revision spec. | `T-XSDD-M1`: each P0/P1 requirement has at least one named test; every implementation file belongs to an approved plan; all earlier suites remain Green. | Required |

## 3. Week 1 — Foundation and development environment

MM-001 is already Green. These entries preserve its contract and identify setup/hardening risks; they do not retroactively change MM-001.

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W01-ENV-001 | P1 · High · Likely | `python` is missing, opens Microsoft Store, points to the wrong version, or `.venv` activation is blocked. The student cannot run the project. | **Prevent:** prerequisites and version check in README; use `python -m` commands; explain execution-policy workaround. **Detect:** setup script/README check prints interpreter path/version. **Recover:** install official Python 3.11+ and recreate `.venv`; never copy a broken environment. | `T-W01-M1 (M)`: on a clean Windows account follow README exactly; verify prompt shows `.venv`, interpreter path is inside project, and imports work. Repeat failure path with missing Python and verify instructions lead to repair. | Setup revision spec if needed |
| W01-DEPS-002 | P1 · High · Possible | Dependency install is offline, partially completed, globally installed, or incompatible. | Pin safe version ranges/lock later; separate runtime/dev files; install only inside `.venv`; document proxy/offline limitation. A failed install leaves no claim that setup succeeded. | `T-W01-OPS2`: build a new environment from dependency files; import Flask/pytest and run suite. Confirm global interpreter does not provide the proof. | Dependency maintenance spec |
| W01-SERVER-003 | P2 · Medium · Possible | Port 5000 is busy, working directory is wrong, debug is accidentally enabled, or server is exposed beyond localhost. | Clear startup command; useful errors; configurable port for local use; debug only via explicit development command; bind locally. | `T-W01-M3`: occupy port 5000 and verify understandable failure/recovery; run from wrong folder and verify README correction; inspect startup says debug off for `python run.py`. | Foundation hardening |
| W01-WEB-004 | P1 · High · Possible | Home/health/404 return wrong status/type, leak diagnostics, lose CSS, or overflow at 320px. | Preserve existing exact contracts; minimal health fields; semantic templates; responsive CSS; custom 404. | Existing `TEST-002`–`TEST-007`; add periodic `T-W01-A4`: 320px/200% zoom, CSS unavailable, keyboard Home link, and health forbidden-field scan. | MM-001 regression |
| W01-GIT-005 | P0 · Critical · Possible | `.venv`, `.env`, secrets, database, uploads, caches, or machine paths are committed. | `.gitignore` before first commit; staged-file inspection; secret scanning; `.env.example` contains names only. | `T-W01-SEC5`: create representative ignored files, run `git status --ignored`, confirm sensitive/generated files ignored and specs/source tracked. Inspect staged diff before every release. | Repository policy spec |

## 4. Week 2 — Database design and migrations

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W02-SCHEMA-001 | P0 · Critical · Possible | Duplicate emails/saves, null required fields, invalid foreign keys, or orphan records appear because validation exists only in forms. | Put `NOT NULL`, unique, check, and foreign-key constraints in schema as well as services. Enable SQLite foreign keys. Translate integrity errors into safe messages. | `T-W02-I1`: bypass forms and insert each invalid row directly; database rejects it and transaction rolls back. Create valid parent/child records and verify relationships. | MM-002 database spec |
| W02-PRICE-002 | P1 · High · Likely | Float rounding, zero/negative/extreme prices, or more than two decimals create incorrect values. | Use fixed decimal/numeric field, documented currency, min/max validator, exact formatting. | `T-W02-U2`: parameterized price boundary matrix; store 0.10 and verify exact round trip; invalid values never commit. | MM-002 |
| W02-DELETE-003 | P0 · Critical · Possible | Deleting a user/product accidentally removes messages/events, leaves orphans, or violates later reporting needs. | Choose policy per relationship: soft-delete product/user identity where history matters; cascade only pure join rows; restrict ambiguous deletion. Document it before migrations. | `T-W02-I3`: delete/archive each parent with saves, messages, events; assert exact retained/anonymized/deleted rows and no orphan references. | MM-002 plus privacy revision |
| W02-MIGRATE-004 | P1 · High · Possible | Migration applies halfway, cannot downgrade, destroys data, or behaves differently on PostgreSQL. | Back up before destructive migration; review generated SQL; transactional migrations where supported; test upgrade from previous schema on SQLite and production-like DB. | `T-W02-OPS4`: seed old schema, upgrade, verify rows/constraints; attempt downgrade when supported; inject failure and verify recoverable state. | Migration plan for each schema change |
| W02-SEED-005 | P1 · High · Likely | Re-running seed duplicates data or production seeding overwrites real records. | Seed command is explicit, development-only, idempotent or requires empty DB; stable demo identifiers; confirmation outside testing. | `T-W02-I5`: run seed twice; counts remain expected. Run against non-empty production-config test DB; command refuses destructive action. | MM-002 |
| W02-LOCK-006 | P2 · Medium · Possible | SQLite reports “database locked” during simultaneous writes; partial operations remain. | Keep transactions short; rollback on exceptions; do not perform slow AI/file work while holding DB transaction; use PostgreSQL in production. | `T-W02-I6`: concurrent writes with controlled delay; app either succeeds consistently or gives retryable error, never half-created records. | Cross-cutting data plan |

## 5. Week 3 — Registration, login, and sessions

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W03-IDENTITY-001 | P1 · High · Likely | Blank/long/malformed email or username, duplicate case variants, surrounding whitespace, or Unicode lookalikes create unusable/duplicate accounts. | Normalize documented fields (trim; email case policy), enforce length/format and database uniqueness, display field error without exposing existing account details unnecessarily. | `T-W03-U1`: boundary/Unicode/case/whitespace table. `T-W03-I1`: register equivalent identities twice; only one user exists and response is safe. | MM-003 auth spec |
| W03-PASSWORD-002 | P0 · Critical · Possible | Plain password is stored/logged, weak password accepted, confirmation mismatch, or hash compared incorrectly. | Use Werkzeug password hash functions; minimum length; no password logging; confirmation validation; never return hash. | `T-W03-SEC2`: register known password; DB value differs and verifies; response/logs contain neither password nor hash. Wrong password fails and DB unchanged. | MM-003 |
| W03-ENUM-003 | P1 · High · Possible | Login/registration responses reveal whether an email exists; unlimited attempts allow guessing. | Generic login failure; similar response timing where practical; basic rate limit or documented class-project limitation; security log without passwords. | `T-W03-SEC3`: compare unknown-user/wrong-password visible messages/status; both generic. Repeated attempts trigger limit if implemented. | MM-003; rate limiting may be P2 |
| W03-SESSION-004 | P0 · Critical · Possible | Session survives logout, uses insecure cookie settings, becomes stale after deletion, or accepts tampered identity. | Flask-Login; signed cookies; production Secure/HttpOnly/SameSite; logout clears session; reload user each request. | `T-W03-I4`: login, access protected page, logout, replay old client request; denied. Tampered cookie is rejected. Deleted/deactivated user session loses access. | MM-003 |
| W03-REDIRECT-005 | P0 · Critical · Possible | Attacker supplies `next=https://evil...` and login redirects user off-site. | Accept only safe local relative targets; otherwise dashboard/home. | `T-W03-SEC5`: test absolute URL, `//evil`, encoded variants, valid local path; only local target allowed. | MM-003 |
| W03-STATE-006 | P2 · Medium · Likely | Logged-in user opens login/register; expired session loses an unsaved form; multiple browser sessions confuse state. | Redirect authenticated users away from auth pages; clear expiry message; avoid claiming unsaved content is stored; later consider draft recovery. | `T-W03-I6`: authenticated GET to auth pages follows documented redirect; expired session POST makes no mutation and explains re-login. | MM-003 |

## 6. Week 4 — Product listing CRUD

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W04-FIELDS-001 | P1 · High · Likely | Blank/whitespace/overlong title or description, unsupported category/condition, or control characters enter database or break cards. | Trim where appropriate; min/max lengths; allow-listed choices; server validation; preserve safe values on errors. | `T-W04-U1`: parameterized boundaries for every field. `T-W04-I1`: invalid POST shows field errors, retains safe input, creates zero products. | MM-004 CRUD spec |
| W04-OWNER-002 | P0 · Critical · Possible | Another user edits, deletes, marks sold, or forges `seller_id`. | Ignore client seller ID; assign `current_user.id`; ownership query/check for every mutation; POST plus CSRF. | `T-W04-SEC2`: attacker sends direct edit/delete/status requests and forged seller field; 403/404, owner/product unchanged. | MM-004 |
| W04-RETRY-003 | P1 · High · Likely | Double click or refresh creates duplicate listings or repeats delete. | Redirect-after-POST; disable submit for usability; optional idempotency token for creation; delete endpoint handles missing/already deleted predictably. | `T-W04-I3`: submit identical request twice; expected documented outcome (one logical listing). Repeat delete; no 500 and no unrelated deletion. | MM-004 |
| W04-STATE-004 | P1 · High · Possible | Sold/archived/deleted product remains editable or appears active; invalid state transition occurs. | Define state machine (`active → sold/archived`); central transition function; queries explicitly filter status. | `T-W04-U4`: all allowed/disallowed transitions. `T-W04-I4`: sold item cannot return to active unless spec permits; browse behaviour matches state. | MM-004 |
| W04-CONFLICT-005 | P2 · Medium · Possible | Two sessions edit same product; last save silently destroys newer changes. | Add `updated_at`/version in edit form; compare on POST; reject stale update and show current version. MVP may document last-write-wins if time-limited. | `T-W04-I5`: load two edit forms, save A then B; if locking implemented B gets conflict and A survives; otherwise limitation is explicit. | MM-004 P2 decision |
| W04-VALIDATION-006 | P2 · Medium · Likely | Validation error erases the user's long description or selects wrong options. | Re-render bound form with safe submitted values and per-field messages; never commit partial row. | `T-W04-I6`: submit one bad field among valid long values; response retains valid values and DB has no new/changed row. | MM-004 |

## 7. Week 5 — Images and uploads

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W05-TYPE-001 | P0 · Critical · Possible | Executable/script is renamed `.jpg`, MIME lies, file is corrupt, zero-byte, or an image decompression bomb. | Extension and MIME allow list plus actual image decode/verification; pixel and byte limits; re-encode accepted images; reject animated/unsupported formats by policy. | `T-W05-SEC1`: valid JPEG/PNG plus renamed script, SVG, corrupt bytes, zero-byte, huge dimensions, over-size body. Only verified images stored; rejected file never served. | MM-005 upload spec |
| W05-NAME-002 | P0 · Critical · Possible | Filename contains `../`, absolute path, reserved Windows name, Unicode tricks, or collides with another upload. | Ignore original storage name; generate random UUID plus trusted extension; resolve and assert path remains under upload root; store original name only if sanitized and needed. | `T-W05-SEC2`: traversal/absolute/reserved/duplicate names; stored paths stay inside isolated upload directory and existing file is never overwritten. | MM-005 |
| W05-LIFECYCLE-003 | P1 · High · Likely | Validation creates orphan file; replacement/delete leaves old file; DB commit fails after upload. | Stage temporary upload, validate, commit record, finalize file; cleanup on exception; defined placeholder; cleanup job/reconciliation report. | `T-W05-I3`: force form/DB/file failure at each stage; assert no orphan/new broken reference. Replace/delete and verify exact old-file policy. | MM-005 |
| W05-DISPLAY-004 | P2 · Medium · Likely | Rotated, enormous, stretched, or missing image breaks layout; no useful alt text. | Normalize EXIF orientation; resize thumbnail; CSS aspect handling; placeholder; alt text derived from product title, not filename. | `T-W05-I4`: portrait/landscape/EXIF/missing file render without overflow at 320px; image has meaningful alt. | MM-005 |
| W05-STORAGE-005 | P1 · High · Possible | Upload directory is missing/read-only/full or production disk is ephemeral, causing disappearing images. | Startup/storage check; configurable storage service/path; production persistent/object storage; friendly failure and DB rollback. | `T-W05-OPS5`: unavailable/read-only simulated storage; listing is not partially created and user sees retry message. Deployment restart retains test image. | MM-005 and W15 deployment |
| W05-SERVE-006 | P1 · High · Possible | Browser executes uploaded active content or guesses private paths. | Serve only re-encoded image types with correct content type and safe headers; never execute uploads; random names; public-product policy explicit. | `T-W05-SEC6`: request stored file and assert image MIME, no HTML execution, no directory listing, unknown path 404. | MM-005 |

## 8. Week 6 — Browse, search, filters, sorting, pagination

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W06-QUERY-001 | P1 · High · Likely | Empty/whitespace/Unicode/punctuation/very long search or SQL/HTML-looking text crashes or behaves unsafely. | Trim; length cap; parameterized ORM query; escape output; empty search means browse all active items. | `T-W06-I1`: query matrix including quotes, `%`, `_`, `<script>`, emoji, 5000 chars; no 500/injection/XSS, documented result and safe length error. | MM-006 search spec |
| W06-FILTER-002 | P1 · High · Likely | Unknown/duplicate/contradictory filters or min price greater than max price produce wrong data. | Parse through one validated filter object; allow-listed values; decimal parsing; field-level query error or ignore policy explicitly specified. | `T-W06-U2`: filter parser table. `T-W06-I2`: every pairwise filter combination returns intersection, never union or inactive rows. | MM-006 |
| W06-SORT-003 | P1 · High · Possible | Invalid sort injects SQL; equal values jump between pages; null values order unpredictably. | Map public sort keys to fixed ORM columns; always add ID tie-breaker; define null policy. | `T-W06-I3`: invalid sort falls back/rejects safely; identical price/date set appears once across consecutive pages in deterministic order. | MM-006 |
| W06-PAGE-004 | P1 · High · Likely | Page 0, negative, text, huge page, changed result count, or deletion makes current page empty. | Positive integer parser, page-size cap, safe 404/empty/last-page policy; links preserve validated query parameters. | `T-W06-I4`: boundary pages and deletion between requests; no 500, duplicate, or missing active item across stable pagination. Verify filters in next/previous URLs. | MM-006 |
| W06-STATUS-005 | P0 · Critical · Possible | Sold/archived/deleted product leaks into public results or unauthorized private listing appears. | Base public query always applies visibility predicate before filters; central reusable scope. | `T-W06-SEC5`: seed every status/user; public search/filter/sort never returns hidden records in HTML/counts. | MM-006 |
| W06-SCALE-006 | P2 · Medium · Possible | Search scans all rows, cards trigger N+1 seller/image queries, or user requests huge page size. | Index status/category/created/price and selected search fields; fixed maximum page size; eager load card dependencies; measure query plan/count. | `T-W06-PERF6`: 10,000 seeded products, page response under agreed classroom budget and bounded queries; requested size above cap ignored/rejected. | MM-006 P2 |

## 9. Week 7 — Product detail, seller profiles, and events

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W07-VISIBILITY-001 | P0 · Critical · Possible | Direct URL reveals archived/deleted/private product or seller's email/hash. | Central visibility query; owner-specific preview separated; template receives explicit public view model; never serialize full User object. | `T-W07-SEC1`: anonymous/other/owner request every state; assert allowed status and forbidden fields absent from HTML. | MM-007 detail/profile spec |
| W07-MISSING-002 | P1 · High · Likely | Product, seller, image, category, or optional field is missing after cleanup/migration. | Database constraints for required relations; placeholders for optional content; 404/410 policy for removed products; never crash template. | `T-W07-I2`: delete/miss each optional asset and request detail/profile; friendly result with correct status and no stack trace. | MM-007 |
| W07-PROFILE-003 | P2 · Medium · Likely | Seller has no active listings, hundreds of listings, or only sold items. | Empty state, pagination, active-only public scope, owner dashboard for hidden states. | `T-W07-I3`: zero/one/many/mixed-status seller data; counts and cards match policy and remain paginated. | MM-007 |
| W07-VIEWS-004 | P2 · Medium · Likely | Owner refreshes or bot floods page, inflating views and recommendations; anonymous tracking raises privacy issue. | Do not count owner; de-duplicate within short session/window; record minimal event data; rate/bot limitation documented. | `T-W07-I4`: owner repeated views create none; same visitor rapid refresh follows dedupe policy; separate users produce expected events. | MM-007 event policy |
| W07-QUERY-005 | P2 · Medium · Possible | Detail/profile performs one query per related product or event and becomes slow. | Eager load required seller/image; paginate seller products; never load all events for display. | `T-W07-PERF5`: query-count assertion with 100 products; count stays bounded rather than increasing per product. | MM-007 |

## 10. Week 8 — Buyer–seller messaging

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W08-PARTICIPANT-001 | P0 · Critical · Possible | User guesses conversation ID or forges sender/buyer/seller IDs to read/send private messages. | Server derives sender from session and conversation participants from product/current user; participant check on every GET/POST. | `T-W08-SEC1`: owner, buyer, unrelated user, anonymous; only participants read/send. Forged hidden IDs ignored; no message created. | MM-008 messaging spec |
| W08-CONTENT-002 | P0 · Critical · Likely | Empty/huge/script/HTML/control-character message causes spam, storage abuse, or XSS. | Trim; non-empty/max length; plain-text rendering with escaping; optional rate limit. | `T-W08-I2`: boundary matrix including `<script>`; valid text displayed literally, invalid rejected, database unchanged, page contains no executable markup. | MM-008 |
| W08-SELF-003 | P1 · High · Likely | Seller starts a buyer conversation with self or contacts own listing through manipulated request. | Compare current user to seller before creating conversation; give owner dashboard link instead. | `T-W08-I3`: direct POST on own product returns documented error/redirect and zero conversations/messages. | MM-008 |
| W08-DUPLICATE-004 | P1 · High · Possible | Double click or concurrent requests create duplicate conversations/messages. | Unique `(product,buyer,seller)` conversation constraint; get-or-create in transaction; PRG; optional message idempotency token. | `T-W08-I4`: simultaneous conversation creation yields one row. Repeat message request follows documented one-message behaviour. | MM-008 |
| W08-STATE-005 | P2 · Medium · Likely | Product becomes sold/deleted during conversation; unclear whether messaging remains available. | Specify rule: historical conversation readable; new contact disabled; existing reply allowed or closed explicitly. Show product state banner. | `T-W08-I5`: transition product through states between messages; permissions and banner match approved policy, history preserved. | MM-008 |
| W08-ORDER-006 | P2 · Medium · Possible | Equal timestamps, multiple sessions, stale unread counts, or page refresh disorder messages. | UTC timestamp plus ID tie-breaker; server-calculated read marker; paginate long threads. | `T-W08-I6`: equal timestamps sort deterministically; reading as one participant does not mark other participant's state; 500 messages paginate. | MM-008 |
| W08-ABUSE-007 | P2 · High · Possible | Spam, harassment, or prohibited content has no response path. | MVP: rate limit/document limitations and basic report/block future design; do not promise active moderation. Retention/privacy policy. | `T-W08-SEC7`: if block/report included, blocked user cannot send but history policy holds; otherwise verify limitation appears in report. | Optional MM-008 hardening |

## 11. Week 9 — Saved products and interaction events

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W09-UNIQUE-001 | P1 · High · Likely | Repeated/concurrent save creates duplicates or double unsave crashes. | Unique `(user_id, product_id)` constraint; idempotent desired-state service; transaction catches race. | `T-W09-I1`: save twice/concurrently yields one row; unsave twice yields zero rows and no 500. | MM-009 saves spec |
| W09-VISIBILITY-002 | P1 · High · Possible | User saves own/hidden/deleted product or saved page displays newly hidden product incorrectly. | Validate product visible and policy on own saves; saved page joins against visibility; show unavailable placeholder only if historical retention is desired. | `T-W09-I2`: attempt each user/status combination; result and count match policy; no private fields leak. | MM-009 |
| W09-CSRF-003 | P0 · Critical · Possible | GET link or cross-site request changes saved state. | POST/DELETE-style form with CSRF; no mutation on GET; session user only. | `T-W09-SEC3`: GET and missing/invalid token leave state unchanged; valid POST changes only current user's relation. | MM-009 |
| W09-EVENT-004 | P2 · Medium · Likely | Double events, missing events, client-forged user/time/type, or bot noise corrupt recommendation data. | Server sets identity/time/type allow list; de-duplication policy; event write failure must not break core save/contact action if analytics is optional. | `T-W09-I4`: forged fields ignored; repeated action follows dedupe policy; force event failure and verify documented core-action/fallback behaviour. | MM-009 event spec |
| W09-PRIVACY-005 | P1 · High · Possible | Behavioural history is retained indefinitely or exposed to other users. | Minimal event fields, retention/anonymization rule, no public event endpoint, delete/anonymize with account policy. | `T-W09-SEC5`: cross-user and public access denied; account deletion/anonymization fixture leaves no directly identifying event according to policy. | MM-009/privacy spec |

## 12. Week 10 — Dashboard, refactoring, and usability

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W10-SCOPE-001 | P0 · Critical · Possible | Dashboard counts/cards include another user's products, saves, or messages. | Every query starts from `current_user`; central dashboard service; never accept user ID from query string for private dashboard. | `T-W10-SEC1`: seed two rich accounts; each dashboard response contains only its identifiers/content/counts. Manipulated `user_id` ignored. | MM-010 dashboard spec |
| W10-EMPTY-002 | P2 · Medium · Likely | First-time user sees blank tables or broken counters. | Purposeful empty states with next action; zero counts; no fake data. | `T-W10-I2`: account with no records renders 200, zero counts, accessible guidance links, no template errors. | MM-010 |
| W10-SCALE-003 | P2 · Medium · Possible | Hundreds of listings/saves/conversations load at once or trigger N+1 queries. | Paginate sections or separate pages; bounded summary counts; eager loading; query-count measurement. | `T-W10-PERF3`: large fixture keeps response/query count bounded and navigation retains section/status filters. | MM-010 |
| W10-STALE-004 | P2 · Medium · Possible | Counts disagree after delete/status/message changes or related row is missing. | Compute from authoritative queries; update in same transaction; safe placeholders for missing optional relation. | `T-W10-I4`: perform each mutation then request dashboard; expected counts/state update exactly, no dangling card. | MM-010 |
| W10-REFACTOR-005 | P1 · High · Likely | Moving routes/templates/services changes behaviour while “cleaning” code. | Freeze external behaviour in regression tests first; refactor in small commits; no simultaneous feature changes. | `T-W10-REG5`: run all weeks 1–9 suites before and after refactor; response contracts/data effects identical. | MM-010 plan |
| W10-A11Y-006 | P1 · High · Likely | Dashboard tabs/actions cannot be used by keyboard or at 320px; status depends on color. | Semantic headings/tables/lists, labeled controls, text status, responsive stacking, visible focus. | `T-W10-A6`: keyboard through every action; 320px and 200% zoom without clipped controls; screen-reader names describe destructive actions. | MM-010 |

## 13. Week 11 — Test quality, datasets, and baselines

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W11-ISOLATION-001 | P0 · Critical · Possible | Tests delete or modify development/production DB/uploads. | Test config requires temporary paths and `TESTING`; refuse fixture cleanup outside temp root; separate credentials. | `T-W11-SEC1`: deliberately pass non-temp path and confirm test setup aborts before deletion; assert production URL never loaded. | MM-011 testing spec |
| W11-FLAKY-002 | P1 · High · Likely | Tests depend on time, random order, network, machine path, or earlier tests. | Freeze/inject time, fixed seeds, no external network, independent factories, deterministic ordering. | `T-W11-T2`: run suite alone, reversed/randomized, twice, and in fresh process; identical result. | MM-011 |
| W11-DATA-003 | P1 · High · Likely | Dataset contains duplicates, missing text/labels, impossible prices, inconsistent categories, or extreme outliers. | Reproducible validation script and data report; explicit cleaning rules; quarantine rather than silently invent labels. | `T-W11-ML3`: known dirty fixture produces exact issue counts; cleaned output satisfies schema and preserves audit summary. | MM-011 data spec |
| W11-LEAKAGE-004 | P0 · Critical · Possible | Same/near-duplicate product appears in train and test, or preprocessing sees test data, giving fake high scores. | Split/group before fit; scikit-learn Pipeline; remove label-revealing fields; duplicate grouping. | `T-W11-ML4`: assert disjoint IDs/groups; spy/inspection shows vectorizer fit only on training rows; leakage column excluded. | MM-011 |
| W11-IMBALANCE-005 | P1 · High · Likely | Overall accuracy hides failure on small categories; synthetic data misrepresented as real. | Report class counts, macro F1/per-class metrics; stratify when possible; clearly label synthetic source; merge/remove unsupported class only by documented rule. | `T-W11-ML5`: imbalanced fixture demonstrates accuracy trap; evaluation report must include macro and per-class scores. | MM-011 |
| W11-BASELINE-006 | P1 · High · Likely | Incorrect or weak baseline makes any model look useful. | Define baseline before model; evaluate on identical held-out rows and metric code; save results/version. | `T-W11-ML6`: hand-calculable tiny dataset verifies metric/baseline; model comparison refuses mismatched split. | MM-011 |
| W11-PROVENANCE-007 | P1 · High · Possible | Dataset licence/source/cleaning cannot be explained in report. | Data card with source, licence, collection date, fields, cleaning, limitations, synthetic status; no unsupported personal data. | `T-W11-M7`: release checklist fails if data card fields or source file hash/version are missing. | MM-011/report |

## 14. Week 12 — Automatic category suggestion

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W12-TEXT-001 | P1 · High · Likely | Empty/short/long/misspelled/multilingual/emoji/adversarial text gives meaningless result or exhausts resources. | Input length limits; combine normalized title/description; minimum-information check; “no suggestion” fallback; do not pretend multilingual support. | `T-W12-ML1`: boundary corpus returns prediction only when sufficient; huge text bounded; all inputs finish without crash. | MM-012 categorization spec |
| W12-CLASS-002 | P1 · High · Likely | Unseen or tiny category is never predicted; majority class dominates. | Minimum examples rule; macro F1/confusion matrix; class weighting or data improvement only after analysis; user always chooses final category. | `T-W12-ML2`: per-class thresholds/report; minority examples evaluated; unsupported class produces documented manual fallback. | MM-012 |
| W12-CONFIDENCE-003 | P1 · High · Likely | Low-confidence prediction is shown as fact or automatically overwrites user's selection. | Show “suggested”; confidence threshold calibrated on validation data; never silently save; user override wins. | `T-W12-I3`: low confidence leaves field unchanged/manual; high confidence offers option; submitted user category persists even when model disagrees. | MM-012 |
| W12-ARTIFACT-004 | P1 · High · Possible | Vectorizer and model versions mismatch, file is missing/corrupt, or arbitrary pickle is loaded. | Save one trusted Pipeline plus metadata/version/hash; load only packaged trusted artifact at startup; validate expected categories/version. | `T-W12-ML4`: missing/corrupt/wrong-version artifact disables suggestion safely; app core still starts; no user-supplied artifact loading. | MM-012/W15 |
| W12-METRIC-005 | P1 · High · Possible | High overall accuracy hides category failure or test set was tuned repeatedly. | Locked test set used once for final report; validation for tuning; macro F1, per-class recall, confusion matrix, error examples. | `T-W12-ML5`: evaluation output contains required metrics and fixed split fingerprint; compare to most-common baseline. | MM-012 |
| W12-CORRECTION-006 | P2 · Medium · Possible | User corrections are ignored or immediately treated as clean training truth, causing drift/poisoning. | Record suggestion and final choice separately with consent/privacy; review/validate before future training; model version recorded. | `T-W12-I6`: override stores final category and optional audit fields correctly; retraining script excludes unreviewed corrections by default. | Optional MM-012 learning loop |

## 15. Week 13 — Price suggestions

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W13-CURRENCY-001 | P1 · High · Likely | Dataset mixes currencies, units, free/zero items, or string-formatted prices. | One documented currency; normalize or reject external data; data schema with positive decimal; never silently convert without rate/date source. | `T-W13-ML1`: dirty currency/unit fixture is rejected/quarantined with exact reasons; training data contains one currency and valid range. | MM-013 price spec |
| W13-SPARSE-002 | P1 · High · Likely | New category/condition has few or no comparable items. | Hierarchical fallback: model only if supported, then category median/range, then overall safe “insufficient data”; minimum sample count. | `T-W13-ML2`: seen, sparse, unseen combinations select the correct fallback and never crash. | MM-013 |
| W13-OUTLIER-003 | P1 · High · Likely | Luxury/collectible/mistyped prices distort training and predictions. | Distribution report; robust transform/algorithm; documented outlier handling; do not delete legitimate rare items without review. | `T-W13-ML3`: known outliers do not dominate median/baseline; cleaning report counts them; legitimate retained cases remain traceable. | MM-013 |
| W13-RANGE-004 | P0 · High · Possible | Model predicts negative, zero, absurd, or falsely precise “correct” price. | Clamp only to justified domain, present rounded range and limitations, never auto-set final price; validate output finite. | `T-W13-U4`: mocked NaN/infinite/negative/extreme outputs trigger fallback; UI labels estimate/range; user's chosen price remains authoritative. | MM-013 |
| W13-EVAL-005 | P1 · High · Likely | Model's average error hides terrible category performance or fails to beat median. | Compare same split against category-median baseline; MAE overall and per category/condition; median absolute error; reject model if no useful gain. | `T-W13-ML5`: hand-calculated MAE fixture; report comparison and go/no-go rule; worse model is not promoted. | MM-013 |
| W13-FAIRNESS-006 | P2 · Medium · Possible | Suggestion systematically undervalues certain categories/conditions or users treat it as appraisal. | Error analysis by supported groups; exclude user identity; clear “not a professional valuation”; allow ignore/override. | `T-W13-ML6`: grouped error table produced; UI contains limitation; no user identity feature in training pipeline. | MM-013 |

## 16. Week 14 — Recommendations

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W14-COLD-001 | P1 · High · Likely | New user/product or empty text has no vector/history and returns nothing or crashes. | Recent/popular active-product fallback; category-based fallback when possible; handle empty vocabulary explicitly. | `T-W14-ML1`: zero-history user, new product, blank text, empty catalog; each returns documented safe result/empty state without exception. | MM-014 recommendation spec |
| W14-EXCLUDE-002 | P1 · High · Likely | Results include current, owned, saved, sold, archived, deleted, or duplicate products against policy. | Apply eligibility filter after scoring and before limit; de-duplicate IDs; fetch extra candidates to replace excluded ones. | `T-W14-U2`: candidate fixture with every exclusion; final IDs are unique, active, allowed, and never current product. | MM-014 |
| W14-DIVERSITY-003 | P2 · Medium · Likely | Five nearly identical listings create boring filter bubble; popular category dominates. | Simple category/seller repetition cap or maximal-marginal-style re-ranking; show reason; keep design explainable. | `T-W14-ML3`: synthetic near-duplicate set meets documented diversity cap while retaining relevant items. | MM-014 |
| W14-FEEDBACK-004 | P2 · Medium · Possible | Repeated refresh/bot events or one accidental click dominates user profile and popularity loop. | Weight strong events carefully; de-duplicate recent views; cap contribution; popularity uses time window; allow fallback/reset policy. | `T-W14-ML4`: repeated same event cannot exceed cap; save/contact weighs as documented; removing history returns cold-start fallback. | MM-014 |
| W14-MANIPULATE-005 | P2 · Medium · Possible | Seller stuffs keywords/categories to appear in many recommendations. | Field length/category validation; combine category/text with limits; monitor extreme similarity frequency; no seller-controlled hidden keywords. | `T-W14-ML5`: keyword-stuffed listing does not monopolize top results across unrelated seeds; document limitation. | MM-014 hardening |
| W14-PRIVACY-006 | P0 · Critical · Possible | Recommendation reason reveals private saves/views or another user's behaviour. | Profile computed server-side for current user; public UI uses generic reason (“similar category”), not private event details; minimal retention. | `T-W14-SEC6`: cross-user requests cannot obtain profile/events; HTML/JSON reasons contain no private product history beyond user's own visible context. | MM-014 |
| W14-EVAL-007 | P1 · High · Possible | Recommendations look plausible in one demo but have poor coverage or stale/invalid results. | Fixed manual relevance sample plus coverage, uniqueness, eligibility, diversity, and fallback metrics; timestamped artifact/catalog. | `T-W14-ML7`: evaluation report generated from fixed queries; 100% eligibility/uniqueness, documented coverage/diversity thresholds. | MM-014 |

## 17. Week 15 — Integration and production preparation

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W15-LOAD-001 | P1 · High · Likely | Model loads on every request, blocks startup, consumes memory, or is incompatible with package versions. | Load once in service/startup; lazy optional loading with lock if necessary; artifact metadata compatibility check; measure memory/time. | `T-W15-ML1`: instrument loader; multiple predictions call load once. Wrong version follows fallback and logs one safe diagnostic. | MM-015 integration spec |
| W15-FAIL-002 | P1 · High · Possible | AI exception/timeout turns listing/detail page into 500. | AI boundary catches expected errors; short timeout where external work exists; category manual, price baseline, recommendation recent-items fallback. | `T-W15-I2`: inject exception/timeout for each AI service; core page remains usable, response explains unavailable suggestion, no partial data. | MM-015 |
| W15-CONFIG-003 | P0 · Critical · Possible | Missing secret/database URL, debug enabled, weak cookies, or development DB used in production. | Environment-specific config class; fail fast for required production values; no default production secret; secure cookie/HTTPS settings. | `T-W15-OPS3`: production config matrix with each missing/unsafe value; startup refuses safely. Development/test still start with isolated values. | MM-015 |
| W15-LOGS-004 | P0 · Critical · Possible | Logs expose passwords, cookies, messages, emails, or model input while failing to identify errors. | Structured event IDs; allow-listed context; redaction; no request bodies/auth headers; log level/config. | `T-W15-SEC4`: trigger auth/message/AI failures with canary secrets; captured logs contain event/error type but no canary/private body. | MM-015 |
| W15-DEPS-005 | P1 · High · Possible | Unpinned upgrade breaks model artifact or introduces known vulnerable package. | Compatible version ranges/lock for release; dependency review/scanner; artifact records package versions; upgrade in separate SDD change. | `T-W15-OPS5`: clean install from release lock and run full suite/artifact smoke tests; dependency scan reviewed with documented decisions. | MM-015 |
| W15-MIGRATE-006 | P0 · Critical · Possible | Deployment migration fails and app writes against partial schema; rollback loses data. | Backup, maintenance/release order, transactional migration, compatibility window, rehearsed restore. | `T-W15-OPS6`: clone production-like DB, migrate, smoke test, simulate failure, restore, verify row counts/checksums. | MM-015 |
| W15-REGRESS-007 | P1 · High · Likely | Integrating AI breaks registration/listings/search/messages or changes response times. | Full suite plus three E2E journeys; performance budgets; feature flags/fallback for optional AI. | `T-W15-E2E7`: seller lists with/without AI; buyer searches/saves/messages; model unavailable variant; all core outcomes identical except suggestions. | MM-015 |

## 18. Week 16 — Deployment, documentation, and demonstration

| ID | Priority | Problem and edge cases | Solution | Test plan | SDD destination |
|---|---|---|---|---|---|
| W16-BUILD-001 | P1 · High · Possible | Host build/start command, port binding, migration, or health check fails. | Document exact build/start/migrate commands; use host port; release health endpoint; review logs; deploy before final week. | `T-W16-OPS1`: deploy from clean revision, run migrations once, health returns exact safe JSON, restart succeeds. | MM-016 deployment spec |
| W16-STORAGE-002 | P1 · High · Possible | Uploaded images disappear after restart because host disk is temporary. | Persistent/object storage or clearly supported persistent volume; placeholder and reconciliation; do not promise persistence otherwise. | `T-W16-OPS2`: upload image, restart/redeploy, verify image and DB reference; simulate missing object and verify placeholder/no 500. | MM-016 |
| W16-DATABASE-003 | P0 · Critical · Possible | Connection unavailable/limited, backup absent, seed overwrites real data, or demo account exposes password. | Managed DB, pool limits, scheduled/manual backup, explicit safe demo seed, unique non-sensitive demo credentials, restore rehearsal. | `T-W16-OPS3`: connection failure gives safe unavailable response; run seed twice; non-demo records untouched; restore backup and verify counts. | MM-016 |
| W16-HTTPS-004 | P0 · Critical · Possible | Cookies travel insecurely, proxy scheme is wrong, or app accepts unsafe host/debug config. | HTTPS host; Secure/HttpOnly/SameSite cookies; trusted proxy handling configured narrowly; allowed hosts if supported; debug off. | `T-W16-SEC4`: inspect production cookie attributes and HTTPS redirect/proxy behaviour; debug traceback never shown. | MM-016 |
| W16-DEMO-005 | P1 · High · Likely | Network fails, AI gives odd result, data is empty, or long typing consumes presentation. | Seeded deterministic demo path; pre-checked examples; local/recorded backup; screenshots/video; explain unexpected AI honestly rather than hide it. | `T-W16-M5`: rehearse timed 8–10 minute demo twice, once with network/model unavailable; backup path still demonstrates architecture/tests/fallback. | MM-016 |
| W16-DOCS-006 | P1 · High · Likely | README/report has machine paths, missing steps, inaccurate metrics, missing dataset attribution, or claims unimplemented features. | Clean-machine setup review; architecture/data card/model card; generated/verified results; limitations and future work; version/tag. | `T-W16-M6`: classmate follows README without verbal help; every reported metric traces to saved evaluation; link/path checker finds no private path. | MM-016 |
| W16-RECOVERY-007 | P1 · High · Possible | Last-minute deployment change breaks app and no known-good version exists. | Tagged release, reversible migration/backup, previous deployment retained, release checklist, change freeze before demo. | `T-W16-OPS7`: deploy candidate, fail smoke test intentionally, roll back to tag and restore service/data within rehearsed target. | MM-016 |

## 19. Required end-to-end journeys

These journeys should be added gradually as their underlying features become approved. They do not all belong in one large test file.

| ID | Journey | Expected result and forbidden result |
|---|---|---|
| E2E-SELL-001 | Register → log in → create listing → correct validation error → edit → mark sold | One owner and one final product state; invalid attempt leaves no partial product; another account cannot modify it. |
| E2E-BUY-002 | Browse → search/filter/sort → paginate → open detail → save → contact seller | Only visible products appear; filters persist; one save/conversation exists; no private seller data appears. |
| E2E-MSG-003 | Buyer messages → seller replies → unrelated user attempts access → product becomes sold | Participants retain documented access/history; attacker denied; state banner/policy correct. |
| E2E-AI-004 | Seller enters listing text → receives category/price suggestions → overrides both → submits | Suggestions are labelled, override wins, final data matches user choice, model input/output failure cannot prevent manual listing. |
| E2E-REC-005 | New user sees fallback → saves/views products → sees eligible personalized results | Cold-start works; later results remain unique/active/not owned; private history is not exposed. |
| E2E-FAIL-006 | Repeat seller/buyer journeys with model/storage/database fault injection | Optional AI degrades safely; storage/DB mutation rolls back; no stack trace, secret, or partial record. |
| E2E-ACCESS-007 | Complete core journeys with keyboard at 320px/200% zoom | Focus remains visible/logical; labels/errors readable; no critical control clipped or dependent on hover/color. |
| E2E-DEPLOY-008 | Clean deploy → migrate → seed demo → smoke journeys → restart → rollback rehearsal | Same release is reproducible; data/images persist; health and rollback function; debug off. |

## 20. Test data strategy

The test suite should use factories rather than one enormous shared seed. Required personas and records:

- Anonymous visitor.
- New user with no activity.
- Seller A with active, sold, and archived products.
- Buyer B with saves, views, and a conversation.
- Unrelated attacker C for every authorization test.
- Products at minimum/maximum field and price boundaries.
- Unicode/emoji and malicious-looking plain-text examples.
- Valid and invalid image fixtures with tiny file sizes.
- Large generated collections for pagination/query-count checks.
- Balanced and deliberately imbalanced ML fixtures.
- Missing/corrupt/wrong-version model artifacts.

Every database test must start from isolated state and clean only its temporary database/files. Production-like tests must use clearly separate credentials and disposable data.

## 21. Semester prioritisation

Trying to implement every enterprise protection would endanger the class project. Use these gates:

### Must be complete before the affected feature is accepted

- All `P0` authorization, privacy, CSRF, data-integrity, file-safety, secret, and deployment protections.
- All `P1` core-journey validation, fallbacks, regression, and AI-baseline checks.
- At least one repeatable test for every `P0` and `P1` issue selected by that feature's specification.

### Implement when feasible, otherwise document clearly

- `P2` concurrency polish, abuse controls, diversity tuning, advanced performance targets, and stale-edit detection.
- Manual accessibility checks that are difficult to automate, but never omit basic keyboard/label/320px coverage.

### Future production work

- `P3` enterprise monitoring, sophisticated moderation, large-scale search, distributed locks, high-availability storage, formal penetration testing, and legal certification.

## 22. Weekly quality gate

No week is complete until:

1. Its feature specification references applicable issue IDs from this plan.
2. Its approved plan maps each selected `P0/P1` issue to named tests.
3. Tests are written and observed Red for the expected missing behaviour.
4. Minimum implementation turns them Green.
5. All earlier regression tests remain Green.
6. Manual accessibility/security/AI checks assigned to the week are recorded.
7. The student can explain one normal case, one edge case, one security control, and one failure fallback.

## 23. Plan review checklist

Before approving this master plan, confirm:

- All 16 roadmap weeks appear.
- Every core feature has invalid, boundary, unauthorized, repeated/concurrent, unavailable-dependency, and recovery coverage where relevant.
- Each `P0/P1` issue contains a repeatable test direction.
- AI sections include baseline, leakage, class/group metrics, artifacts, uncertainty, user override, and fallback.
- Previous MM-001 files and behaviour remain unchanged.
- The plan separates semester requirements from future production work.

`PLAN-QA-000` was approved on 2026-10-25 and is now a required reference for future SDD documents. Its approval does **not** authorize implementation of weeks 2–16 or creation of their pytest tests.

