# MM-019 Green verification — 2026-11-02

MM-019 and PLAN-019 were approved before tests and implementation. The 35-test Red checkpoint is recorded separately.

## Focused automated result

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_cart.py tests\test_cart_migration.py -q --basetemp=.pytest-tmp\mm019-green
# 35 passed in 45.55s
```

This includes the model constraints, migration upgrade/downgrade, authentication, CSRF, duplicate/concurrent Add, account isolation, exact money, 21-row pagination, unavailable privacy, idempotent Remove, non-mutating Checkout and injected database-failure cases.

## Complete regression result

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm019-regression-final-clean
# 298 passed in 336.81s (0:05:36)
```

Two earlier full runs reached `297 passed, 1 failed` and exposed an order-dependent logging problem in the test process. Flask applications created by different tests share the named `app` logger, so an earlier application could leave that logger disabled. Security initialization now restores the logger's enabled, propagation and level settings every time an application is created. The isolated logging test passed, the exact formerly failing 115-test prefix passed after the fix, and the final clean 298-test run above is authoritative.

## Migration and local data

- Temporary fresh-database upgrade/downgrade tests passed.
- A non-overwriting local backup was created at `instance/backups/market-mirror-before-mm019-20261102.sqlite`.
- The local database upgraded from `d88e8d30439f` to `f19c7a42e0b1` without reset or reseed.
- Alembic added only `cart_items` and its intended indexes.
- The upgraded local server starts at `http://127.0.0.1:5000`.

## Browser acceptance results

Browser mutations used a loopback-only temporary SQLite database and temporary uploads. The disposable server was stopped afterward. The real local site was opened only for a read-only startup/catalogue check.

| Check | Result |
| --- | --- |
| Login and initial count | PASS — ordinary login opened catalogue with Cart count 0 and 11 Add controls. |
| Add from catalogue | PASS — count 0 → 1 → 2 with accessible success notices. |
| Duplicate Add | PASS — count stayed 2 and “already in your cart” appeared. |
| Seller/Saved cards | PASS — Add from seller profile raised count to 3; Add from Saved raised it to 4. |
| Owner dashboard | PASS — seller dashboard cards had no Add forms and header count was independently 0. |
| Cart review | PASS — four rows newest-added-first, three images, one placeholder, count 4 and exact `$70.00 USD` subtotal. |
| Remove | PASS — count 4 → 3 and subtotal `$70.00` → `$49.75`. |
| Demo Checkout | PASS — reported no payment/order; all three rows and `$49.75` remained. |
| Account isolation | PASS — second buyer had count 0, empty cart and no first-buyer content. |
| Unavailable privacy | PASS — busy cart showed 12 rows, one generic unavailable row, no archived-title canary, exact `$167.75` eligible subtotal and disabled Checkout. |
| No JavaScript | PASS — controlled response had zero script tags; three server forms remained usable and Remove updated count 3 → 2. |
| Narrow layout | PASS — real 320 CSS-pixel viewport, two-digit count and long title, `scrollWidth 305` with no horizontal overflow. |
| Keyboard | PASS — first Tab target had a visible solid focus outline approximately 2.67 pixels wide. |
| MM-017/MM-018 regression | PASS — lightbox opened with Close focused; seller link opened the correct 11-card profile. |
| Browser console | PASS — no warnings/errors from application interactions. |

Evidence:

- `docs/evidence/019-cart-desktop.png`
- `docs/evidence/019-cart-narrow.png`

## Explicit limitations

The browser controls did not expose actual 200% browser zoom or a dark-mode media-preference emulator. Those optional checks are not claimed as passed. The responsive 320-pixel test is reported as viewport testing, not a substitute for zoom. CSS retains the project's existing dark-mode variables and the automated suite covers semantic behaviour independently of colour.

## Safety result

No payment details, addresses, orders or reservations were introduced. Checkout makes no database change. Real demo users/products were not changed during browser acceptance, and the temporary fixture server and browser viewport override were cleaned up.
