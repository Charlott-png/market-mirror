# MM-002 implementation evidence

Date: 2026-10-25. Original specification and plan approved; execution authorized.

- Original Red baseline: 72 tests, 11 passed, 4 failed, 57 setup errors due to
  the then-missing database implementation (see `002-red-baseline.md`).
- Final Phase 2 run: **89 passed in 18.82 seconds**, no warnings.
- `pip check`: no broken requirements.
- Development `db upgrade`: revision `46b4b94079af` applied.
- `db current`: `46b4b94079af (head)`.
- `db check`: no new upgrade operations detected.
- Seed: three users/twelve products created; second run skipped unchanged.
- Development database SHA-256 before and after the complete pytest run:
  `BF356AD51C61F1492928E7542F35774955D98A9DEC15D948043D361AC5DF8F01`.

The suite checks persistence through a newly constructed application, isolated
database writes, migration upgrade/repeat/downgrade/re-upgrade, seed collision and
rollback, raw SQL constraints, exact cents, UTC timestamps, and all old page tests.

Implementation clarification: logical decimal money uses integer cents on SQLite
and NUMERIC(10,2) on PostgreSQL. This avoids SQLite floating-point storage. Migration
history freezes the physical schema independently of current model code. The
student guide and README explain conversion and transfer implications.

Test-run caveat: the first attempt at additional integrity tests and a later model
run used a nonexistent parent temporary directory. Those setup errors were not
treated as application failures or valid Red evidence. The original validated
72-case Red record remains the implementation baseline. All added regression
cases subsequently passed with a real dedicated temporary directory.

Live PostgreSQL verification and student learning exercises remain separate later
checks. This record is historical; later phases expand the suite and schema.
