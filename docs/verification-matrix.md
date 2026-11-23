# Requirements, evidence and remaining verification

This matrix is an index, not a claim that a finite suite covers every possible
failure. Earlier QA analysis and risk/test plans remain authoritative historical
context. The approved later package defines the implemented local release.

Final consolidated clean-environment run: **188 passed in 188.24 seconds**, no
warnings. `pip check` passed; schema comparison found no drift; the development
database checksum was unchanged. Details are in `tests/003-016-verification.md`.

## Automated traceability

All paths below are relative to the project root. Parameterized tests expand into
multiple cases. Tests construct disposable databases/files; only explicit setup
commands change development data.

| Requirements | Implementation | Executed evidence | Qualification |
|---|---|---|---|
| MM-001 foundation | Factory, routes, base/errors/CSS | `test_foundation.py` | Original response contracts retained |
| MM-002 data/schema | Models, types, migrations, seed | `test_user_model.py`, `test_product_model.py`, `test_database_config.py`, `test_database_regression.py`, `test_database_integrity.py`, `test_migrations.py`, `test_seed_command.py` | SQLite executed; PostgreSQL not executed |
| AC-003-01/02 | Registration validation/hash/unique transaction | `test_marketplace.py::test_register_login_logout_profile`, `test_invalid_registration_has_no_partial_user`, `test_duplicate_registration_and_generic_login` | Duplicate scenario covered; not every possible uniqueness race |
| AC-003-03/04 | Session/CSRF/redirect/throttle | `test_expired_session_and_login_limit`, `test_login_redirect_is_local`, `test_csrf_real_form_token_required`; `test_hardening.py::test_tampered_cookie_cannot_authenticate`, `test_real_csrf_protects_all_mutations`; `test_demo.py` | Real login + CSRF rehearsal included |
| AC-003-05 | Own profile and opt-out | Registration/profile journey and consent test | Broader immutability forgery matrix remains an extension |
| AC-004-01/02/04 | Owned creation/edit and request tokens | Creation identity, bad prices, edit/preview denial; `test_two_simultaneous_requests_are_idempotent[create]` | File-backed concurrent SQLite clients |
| AC-004-03 | Versioned transitions | `test_complete_status_matrix` (9 pairs), stale edit test | PostgreSQL concurrent status behaviour unverified |
| AC-004-05 | Own-listing scope/pages | Dashboard privacy, catalogue query/pagination test | Full 20-item own-page boundary matrix not separately exhaustive |
| AC-005-01/02 | Byte/pixel/type checks and fresh JPEG | Image normalization/spoof tests; `test_rejected_image_limits` (4 cases), `test_photo_orientation_and_metadata_are_normalized` | Original names ignored; generated UUID prevents path use |
| AC-005-03 | File compensation and reconciliation | `test_listing_image_commit_failure_keeps_old_image`, `test_image_disk_failure_does_not_leave_new_file` (open/replace), operations image report | Crash-time `.pending` review is manual; stop writers before orphan deletion |
| AC-005-04/05 | Placeholder/alt text and controlled media route | Image access tests; browser 320px product/detail check | Full screen-reader/media-cache audit pending |
| AC-006-01/02 | Literal parameterized search/filter validation | Search/wildcard tests and invalid-query parameterization; browser search | Full multilingual case folding excluded |
| AC-006-03/04 | Stable pages, eager seller lookup | `test_query_counts_and_pagination_are_bounded` | 1,000-row SQLite fixture, not a production load test |
| AC-007-01/02/03/04 | Active/sold details, hidden archive, public seller | Public privacy test, image placeholders, seller-card privacy regression, browser detail | Many-page seller-specific boundaries not exhaustively automated |
| AC-008-01/02/03 | Private participant queries and unique conversations | Message journey/forged sender, self-contact, concurrent contact and replay | Broader cross-product concurrent token collisions remain a stress-test extension |
| AC-008-04/05 | Message limits/status/read markers | CSRF all mutations, archived/sold policy, escaped text, invalid-message preservation/field errors and isolated read markers | Full message-throttle/equal-time/read-pagination matrix not exhaustive |
| AC-009-01/02 | Idempotent saves/unavailable placeholders | Save replay and concurrent saves; real two-account demo | Uses current visibility, not stale UI state |
| AC-009-03/04 | Explicit consent and event separation | Event opt-in/dedup/opt-out; optional-event failure test; retention test | Large-scale competing opt-out/event stress rehearsal pending |
| AC-010-01/02/03/04 | Private dashboard queries | Empty/identity dashboard test, real demo, 1,000-row query-count check | Full keyboard-only/200%-zoom task journey pending |
| AC-011-01/02/03/04 | Validation/group partition/baselines | AI dirty data/splits, unexpected/private fields, near duplicates, held-out vocabulary and feature allow-list tests | Real-data permission/duplicate review not applicable to synthetic fixture; needed before real data |
| AC-012-01/02/03/04 | Classifier/threshold/fallback/explicit apply | AI known/OOV/missing/corrupt model, auth/CSRF, saved report | UI apply path present; full authenticated browser automation not performed |
| AC-013-01/02/03/04 | Candidate/baseline selection and bounded estimate | Prediction boundary/invalid-choice/no-silent-update tests, manual MAE calculation check | Synthetic-only; more injected extreme-model cases can extend coverage |
| AC-014-01/02/03/04 | Offline index and live visibility/consent | Fallback/determinism tests, known-similar/stale-index/opt-out fixture, explicit equal-score ID-tie regression, browser suggestions | No real-user ranking metrics; seller-cap and scale stress tests can be extended |
| AC-015-01/02/03/04/05 | Settings, Waitress, readiness, logs, maintenance | Missing-prod-setting, secure configuration, readiness outage/recovery, safe-canary logs, purge/anonymize, local backup roundtrip | Docker/PostgreSQL/HTTPS/full-media restore not executed; public hosting excluded |
| AC-016-01/02/03 | Lock/install, demo, docs/metrics | Separate clean virtual environment; `test_demo.py`; report/evidence files | Browser smoke checks only; full human demo rehearsal pending |
| AC-016-04 | Student understanding | Practice questions and exercises supplied | Requires the student's participation; not signed off |
| AC-026-01/02 | Zero-to-five uploads and bounded image validation | Three/six/corrupt image tests; prior pixel/frame/metadata tests; 25 MiB group contract | Exact browser multipart overhead is bounded by the 26 MiB request cap |
| AC-026-03/04/05 | Ordered rows, cover compatibility and atomic create/edit | Model constraints, migration backfill/downgrade, partial-file compensation and replacement tests | Crash during post-commit old-file cleanup is reported by maintenance |
| AC-026-06/07 | Ordered local previews and cover-only AI | Drop-zone markup/JS contracts and existing vision race/privacy suite | Manual drag gesture depends on browser controls; picker rehearsal remains student work |
| AC-026-08/09/10 | Thumbnail switching, selected lightbox and media privacy | Gallery rendering/static JS tests, additional-file archived-owner test, real migrated single-image lightbox smoke | Manual five-thumbnail keyboard/narrow/zoom rehearsal remains open |
| AC-026-11/12/13/14 | Cover-only cards, regressions and maintenance | Focused 32-pass run, full 460-pass run, schema check and real zero-drift maintenance result | Screen-reader and 200% zoom are not falsely claimed as automated |
| AC-027-01/02/03 | Floating widget, availability states and bounded questions | Template/static contracts, anonymous/signed-in loopback journey and request boundary tests | Browser viewport resizing was unavailable; mobile CSS is statically verified |
| AC-027-04/05/06 | Active-only bounded context and strict Gemini JSON | ≤60 candidate/privacy tests; fake-client schema/tools/timeout tests; parameterized result validator | Automated tests never contact Google or measure live-model answer quality |
| AC-027-07/08 | Current trusted product links and useful/no-match answers | Cheap-camera endpoint/browser story; server-owned fields/URLs; mid-response sold race | Recommendation relevance is deterministic in fixture, not a real-model benchmark |
| AC-027-09/10/11 | Auth/CSRF/rate/failure/injection controls | Real-CSRF, 15/10-minute throttle, provider canaries, malicious query/product/output and safe-DOM tests | Wider distributed quota enforcement is outside local SQLite scope |
| AC-027-12/13/14 | Privacy, accessibility and complete verification | No-persistence snapshots, disclosure/focus/Escape browser checks, 76 focused + 170 related + 536 full tests, pip check | Real screen reader, 200% zoom, dark-mode browser and live-key smoke remain manual |
| AC-028-01–06/10 | Private bounded history, endpoint safety and Explore/Dashboard integration | Focused auth/CSRF/status/order/prune/isolation/concurrency tests; AJAX and isolated browser flow | SQLite executed; PostgreSQL concurrency remains unverified |
| AC-028-07–09 | Server-rendered same-category alternatives and existing Discover more isolation | Parameterized 0–3+ candidate tests, no-JavaScript browser check, Dashboard and AI regression tests | Randomness is constraint-tested, not a ranking-quality claim |
| AC-028-11/12 | Migration, accessibility contracts and complete verification | Upgrade/downgrade tests; backed-up local upgrade; 20 focused + 201 related + 560 full tests; pip check | Browser viewport resizing, screen reader and 200% zoom remain manual |
| AC-029-01–03/11–14 | Owned chat bubbles, semantic/local time, newest history blocks, sticky fallback composer and accessibility | 29 focused contracts; isolated buyer browser; no-script fallback; existing mobile/CSRF/replay/archive tests | Viewport resize, screen reader and 200% zoom remain manual |
| AC-029-04–08/12/16 | Participant-only bounded no-store updates, read-only GET, safe text-node append and explicit read markers | Auth/cursor/privacy/50+1/read-only/query-bound tests; live isolated three-second append and dedup | Local SQLite/Waitress executed; public load and PostgreSQL not measured |
| AC-029-09/10/15 | Scroll/status recovery contracts and complete compatibility | Client static contracts; browser near-bottom append/no console errors; 589-test clean full rerun; pip check | Automated fixture does not simulate unreliable real internet or multi-device timing |
| AC-030-01–09 | Midnight/Gold tokens, typography, sticky chrome, glass cards, gold actions, Explore spacing and themed page families | 14 focused contracts; exact contrast calculations; desktop Home/Explore/product/lightbox browser review | Google Fonts offline blocking and a formal visual-design expert review remain manual |
| AC-030-10–15 | Chat/AI preservation, responsive and preference boundaries, presentation-only compatibility | 325 related + 603 full tests; final 46-test mobile rerun; 320px no-overflow metrics; zero browser console errors | Real screen reader, 200% browser zoom, forced-colors emulation and printed paper remain manual |

## Browser evidence

Observed with the in-app browser against the actual loopback Waitress server:

- Home and catalogue rendered successfully.
- Search form for “Python” returned one visible matching book.
- Product detail displayed price, status, seller and recommendation section.
- Catalogue, product detail and login rendered at a 320-pixel viewport.
- Tab navigation moved from email to password and displayed a visible focus ring.
- After the seller-card correction, catalogue accessibility state contained the
  correct public seller links, without private email fields.
- The isolated MM-027 fake-provider fixture showed the anonymous fallback,
  signed-in focus flow, trusted cheap-camera cards/detail navigation, exactly
  one provider call with active IDs only, and Escape focus return.
- The isolated MM-028 fixture showed private empty and populated history,
  newest-first repeat/cap behavior, current-product exclusion, a no-alternative
  category, no-JavaScript related cards, AJAX preservation and separate
  Dashboard Discover more; the console had no JavaScript errors.
- The isolated MM-029 fixture showed computed left/right grey/blue bubbles,
  localized semantic times, safe literal script-like text, newest/older blocks,
  one three-second incoming append with no duplicate, no-script fallback and no
  browser console errors.
- MM-030 browser review showed the redesigned Home, Explore, product detail,
  lightbox and AI Assistant at desktop and narrow sizes. At 320px the document
  had no horizontal overflow, desktop navigation was hidden, mobile navigation
  was a five-item grid and the header remained sticky. A duplicate-navigation
  cascade issue found in the first screenshot was corrected and reverified.
  Console error count was zero.

`docs/evidence/local-catalogue.png` records the local catalogue, not a design mockup.
Placeholder images accurately indicate that the seed products have no photos.
The temporary preview server is stopped after verification; launch your own using
the README command. A screenshot does not establish end-to-end keyboard access,
screen-reader correctness, 200% zoom, or every mobile interaction.

## Remaining release/learning gates

1. **Student-led demo:** perform the two-account story and answer the concept
   questions. Record findings in `demo-guide.md`; ask for help where needed.
2. **Full accessibility walkthrough:** complete registration, listing/upload,
   search, save and messaging using keyboard only, at 320px and 200% zoom. Include
   long unbroken titles/usernames, focus order, validation announcements and a
   screen reader. Browser smoke checks above are partial evidence, not this sign-off.
3. **PostgreSQL and containers:** execute migrations, precision/FKs/uniqueness,
   concurrency, restart persistence and backup/restore in a disposable PostgreSQL
   deployment. Configuration and SQLite tests do not prove this.
4. **Operational rehearsal:** full DB + media snapshot restore; locked/missing
   media permissions, disk exhaustion, proxy trust, HTTPS secure-cookie behaviour,
   log rotation and verified privacy requests. Existing tests cover specific local
   pieces, not a full production failure exercise.
5. **Real-world AI:** obtain permissioned representative data, manually review
   duplicates/provenance, freeze evaluation design and compare baselines. Use
   time-separated legitimate interaction data before reporting ranking metrics.

These are explicit unverified/deferred checks, not concealed passing results.
Public rollout is outside the current local-only request. No live user data is
needed to continue learning or to demonstrate the local classroom release.
