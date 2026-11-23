# MM-026 verification evidence

Date: 2026-11-07 (Asia/Shanghai)

## SDD sequence

- MM-026 specification approved by the user.
- PLAN-026 approved by the user.
- Tests written before implementation.
- Red checkpoint: 19 failed, 21 passed; preserved in
  `tests/026-red-verification.md`.
- Implementation followed the Red checkpoint.

## Automated verification

- Focused gallery/migration/drop-zone suite: **32 passed in 39.72 seconds**.
- Complete project regression suite: **460 passed in 435.45 seconds**.
- Python dependency consistency: **No broken requirements found**.
- Alembic schema check: **No new upgrade operations detected**.

## Real local database migration

- Server confirmed stopped before backup/migration.
- Preflight revision: `a25c0de02501`.
- Duplicate legacy cover references: 0.
- Product rows before migration: 24.
- Backup:
  `instance/backups/market-mirror-before-mm026-20261107-022208.sqlite`
- Backup size: 196,608 bytes.
- Source and backup SHA-256:
  `3CE71189E75BAD58C88EE8A139148B99B36E3B6478366595C3B958E557BFFB4C`
- Hashes matched before migration.
- Final revision: `b26c0de02601`.
- Backfilled ProductImage rows: 24.
- Legacy non-null covers: 24.
- Cover drift: 0.
- Missing referenced images: 0.
- Twelve unrelated orphan JPEGs were reported read-only and intentionally not
  deleted.

## Browser smoke evidence

The real upgraded loopback application loaded the 18-product public catalogue.
The migrated Silver laptop product loaded its existing image through the
protected media route. Selecting the image opened the full-screen dialog with
its larger image and Close control; activating Close restored the page.

Multi-thumbnail switching, upload groups, atomic replacement and archived
additional-image permissions are covered by the isolated automated contracts.
The student should still perform the manual five-photo picker, narrow-screen
and keyboard checklist in `tests/026-browser-checklist.md` as a learning/demo
rehearsal; those checks are not falsely claimed here as completed.
