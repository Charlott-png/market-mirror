# Implementation and test plan: MM-003–016

Authorized by the approved specification package and the request to execute all
phases. Work proceeds in dependency order. Tests precede the corresponding code.
No deployment or learning outcome is marked complete without actual evidence.

## Phase 3: accounts

Add Flask-Login, Flask-WTF, and email-validator. Add auth/profile forms and routes,
session expiry, CSRF, safe redirects, and database-backed fixed-window rate limits.
Rate windows are defined by server epoch time; tests inject the clock. HMAC keys
hide identities in rate records. Expired windows are cleaned by a maintenance CLI.
Require SECRET_KEY for normal operation; tests receive a separate fixed test key.
Keep all submitted passwords out of HTML/errors/logging.

Tests: successful/invalid/duplicate registration; login and logout; expiry;
unknown-email/wrong-password equivalence; unsafe redirects; CSRF; identity spoofing;
login/registration limits and expiry; biography limits. Add schema migration before
persisting throttle records. Save Red/Green evidence.

## Phase 4: listings and images

Add product integer version, creation-request table, listing forms/services,
ownership-scoped queries, explicit transition map, stale-edit handling, and
idempotent creation in one transaction. Introduce an image helper using Pillow,
unique filenames, decoded limits, metadata stripping, and compensation on failure.
Media is served by an authorized route, not the static directory. Add read-only
reconciliation and an explicit opt-in orphan cleanup command.

Tests: title/description/price boundaries; unauthorized editing/preview/state;
all status transitions; stale versions; duplicate form tokens; valid and corrupt
images, content masquerading, oversize content, paths, archived-media access,
replacement and rollback cleanup. Use test-owned upload roots.

## Phase 5: discovery

Add query-parameter validation, a reusable active-products query, bounded pages,
literal substring search, allow-listed sorts, detail/profile views, and card
templates. Public view models/templates expose only permitted fields.

Tests: literal wildcards, empty/script/Unicode terms, duplicate parameters,
invalid filters/pages, combined filters, equal-sort-value pagination, visibility
matrix, private-field canaries, seller empty states, bounded query counts.

## Phase 6: marketplace interactions

Add conversations, messages, read markers, saved products, consent fields,
minimal events, and private dashboard. Save/contact mutations are transactional;
event recording runs afterward with independent rollback so analytics failures
cannot undo a successful user action. Serialize competing SQLite writes with
short transactions and use uniqueness plus rollback/re-query for races.
Read markers change by POST, never by GET. Opt-out deletes events immediately.

Tests: two-user journey; third-party access denial; sender spoofing; self-contact;
sold/archived reply policy; duplicate request tokens/conversations/saves; read
marker isolation; escaped content; limits; consent and retention; event failure;
dashboard identity/counts/empty states. Include file-backed concurrent clients.

## Phase 7: data and evaluation

Create deterministic, explicitly synthetic fixture generation, CSV validation,
provenance/data card, duplicate grouping, group-disjoint stratified partitions,
and category/price baselines. Each class requires sufficient independent groups.
Record input hashes, exact memberships, cleaning/quarantine, versions, and metrics.
Use generated files only in ignored instance/ai or test-owned directories.

Tests: malformed rows, inconsistent duplicate groups, label/price limits, missing
provenance, reproducible splits, group isolation, per-class coverage, known metric
examples, no target features. Do not claim synthetic accuracy represents market data.

## Phase 8: AI

Implement offline scikit-learn pipelines: TF-IDF/logistic category classifier,
Ridge price regression with baseline selection, and TF-IDF recommendations.
Bundle model/schema/data/version manifests with integrity checks. Load only trusted
local artifacts. Expose authenticated CSRF-protected suggestion endpoints and
explicit apply controls on listing forms. Add cold-start/missing-artifact fallbacks,
visibility rechecks, consent-aware personalized ranking, and truthful explanations.

Tests: known predictions, schema mismatch/corrupt/missing artifacts, OOV/empty
inputs, finite bounded prices, identical held-out baseline rows, no training inside
requests, no private recommendation leakage, deterministic diversity/ties, opt-out.
Generate a real synthetic evaluation report; use observed metrics only.

## Phase 9: production preparation

Add production WSGI entry point, PostgreSQL driver/configuration, readiness, safe
request logging/security headers, environment example, dependency lock, operational
runbook, privacy/retention and operator anonymization workflow. Provide a local
container deployment definition using persistent database/media volumes where
Docker is available. No cloud account or paid resources are created automatically.

Tests: missing production settings, secure cookies, no debug/secret leakage,
readiness failure/recovery, retention/anonymization, environment separation.
Run PostgreSQL integration and backup/restore rehearsal if a PostgreSQL service is
available. Otherwise retain explicit pending status and exact operator commands;
SQLite tests and offline SQL compilation do not count as PostgreSQL execution.

## Phase 10: teaching, report, and demo

Produce architecture/ER diagrams, requirements-to-test matrix, feature guides,
measured evidence, demo script and offline fallback, model/data cards, and report.
Rehearse the two-account story through integration tests and browser where available.
Verify the setup in a clean virtual environment. Keep deployment and student
understanding marked pending when their real acceptance steps have not occurred.

## Shared verification and source control

Run relevant tests while changing a feature, then the complete suite at milestone
boundaries. Compare database/migration metadata and review generated migrations.
Keep databases, media, secrets, model artifacts, caches and virtual environments
ignored. Preserve historical specs/plans/evidence; append new results. Do not create
commits until a usable local Git identity exists or the user requests one.
