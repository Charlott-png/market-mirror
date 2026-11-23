# Phases 3–10 execution evidence

Date: 2026-10-25. Environment: Windows, CPython 3.12.14, SQLite, exact packages in
`requirements-lock.txt`. Scope: local implementation; no public deployment.

## Authorization and sequence

- User requested execution of Phases 1–10.
- `specs/003-016-remaining-phases-specification.md` was drafted before code.
- User explicitly approved the specification package and continued implementation.
- `plans/003-016-implementation-and-test-plan.md` recorded implementation/tests.
- User selected local-only operation with deployment instructions for later.
- Original specifications, QA analysis/plan, phase roadmap and prior Red/Green
  evidence remain in the repository. The original HTML weekly proposal is retained
  in the workspace root. Current README marks older setup text as historical.

## Observed test stages

| Stage | Observed result | Meaning |
|---|---|---|
| Phase 2 | 89 passed | Historical database milestone; see separate record |
| Initial marketplace tests | 48 failed before feature implementation | Expected Red: missing routes/features |
| Marketplace implementation | 48 passed | Accounts through dashboard Green |
| Expanded regression milestone | 138 passed in 159.56s | Foundation/data/migrations plus marketplace |
| Initial AI/operations tests | 8 failed, 4 errors | Expected Red: missing AI/ops modules/routes/commands |
| AI/operations implementation | 12 passed in 23.58s | First AI/ops Green |
| Hardening baseline | 2 failed, 22 passed in 62.20s | Missing request logging; private/near-copy dataset validation gap |
| Hardening fixes | 24 passed in 31.38s | Both identified gaps corrected |
| Full milestone | 174 passed in 207.87s | Existing full suite at that point |
| Final gap regressions | 2 failed, 1 passed | Missing seller name on cards; uncaught unexpected exception; SQLite restore already passed |
| Clean virtual-environment run | 177 passed in 215.30s | Seller card and safe unexpected-error handling fixed |
| Real two-account offline rehearsal | 1 passed in 25.27s | Actual registration/password login/CSRF; create/search/save/message/sale/denial |
| Additional edge/AI checks | 42 passed in 43.14s | Disk failure, EXIF, outage recovery, production settings, optional event failure, manual MAE comparison included |
| Consolidated clean-environment milestone | 185 passed in 173.49s | Complete suite before the final ranking tie regression |
| Ranking tie regression | 1 failed in 42.55s | Equal similarity was incorrectly broken by recency before ID |
| Ranking correction full suite | 186 passed in 171.97s | Clean environment; correct ID tie-breaker |
| Message correction regressions | 2 failed in 48.96s | Invalid contact/reply discarded safe message text instead of returning a correction form |

The ranking correction now orders scored candidates by descending similarity and
then ID, reserving recency for fallback candidates. It changes no trained artifact.
The message correction returns the escaped message and field errors, allowing
safe resubmission. Neither invalid message creates a row.

Final consolidated result is appended after the last run below. Earlier stage
counts reflect the suite at that time; they are not contradictory totals.

## Non-pytest checks

- `pip check`: no broken requirements (both development and clean environments).
- Separate `.venv-clean` created without system site packages; exact lock installed.
  Initial ensurepip hit the environment's restricted default temporary directory;
  using the dedicated workspace `.pytest-tmp/bootstrap` resolved it. This was an
  environment setup issue, not application Red evidence.
- `db upgrade`: development data moved to head `d88e8d30439f`.
- `db check`: no new upgrade operations detected after model integration.
- Offline `ai train`: generated dataset/splits/card/models/manifests/evaluation.
- Offline `ai index`: indexed eight active products from the twelve-row seed.
- Query benchmark on a 1,000-product fixture: catalogue **2 queries**, dashboard
  **5 queries**, combined request block **0.254 seconds** on this machine. This is
  a single local measurement, not a latency promise or production capacity result.
- Browser smoke checks and screenshot recorded in `docs/verification-matrix.md`.

## Migration incident and recovery

The first generated marketplace migration attempted a SQLite batch rebuild of
`users` while existing products referenced that table. It failed with foreign-key
enforcement enabled. This was not dismissed as a successful migration.

A populated-foundation regression test reproduced the issue. The migration was
changed to native add-column operations, avoiding parent-table reconstruction.
`scripts/recover_incomplete_marketplace_migration.py` checks the known revision,
requires all newly created activity tables to be empty, backs up the database,
and removes only the empty objects from that failed attempt. It preserved the
existing users/products before the corrected upgrade. The recovery backup remains
at `instance/market-mirror-before-migration-recovery.sqlite` (private/ignored).
The script is incident-specific, not a routine setup command; do not run it on
an arbitrary database. Its guard refuses to overwrite the existing backup.

## AI interpretation

The report includes actual synthetic results: category macro-F1 1.0 versus
majority 0.035714; selected price test MAE $11.7738. Median baseline validation
MAE $11.7321 beat Ridge $11.9365, so the model bundle selected medians. These
numbers do not establish real-market prediction accuracy. Dataset fingerprint,
model version, splits and limitations are in `docs/project-report.md` and the
generated JSON files. No real-user recommendation accuracy is claimed.

## Known verification boundaries

No PostgreSQL/Docker tools were available and the user chose local-only operation.
Production PostgreSQL, containers, HTTPS/proxy, full DB/media disaster recovery,
complete accessibility walkthrough and the student's own explanation are not
marked passed. See the verification matrix for precise remaining gates.

## Final consolidated verification

Executed after the ranking and message-form corrections:

```text
.venv-clean\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp/verified-release
188 passed in 188.24s (0:03:08)
```

No warnings were reported. The clean environment has no system-site packages.
`pip check` found no broken requirements. Final schema comparison reported no new
upgrade operations; installed SQLite version is 3.53.1. The development database
SHA-256 was identical before and after the release checks:

`E5C943147332171459A7D900976923C352C6039B9E4C7F778EEB18841CF6DD55`

The preview was served only on loopback and stopped after browser verification.
No public hosting, real-user data import, paid service, Git commit or deployment
was performed. Git ignores the runtime database, local secret, AI artifacts and
both virtual environments. The local screenshot and teaching/report files remain
available without a running server.
