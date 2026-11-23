# MM-025 Green verification

Date: 2026-11-07 (Asia/Shanghai)

## SDD order

1. MM-025 specification approved.
2. PLAN-025 approved.
3. Fifty-three focused tests collected before implementation; one more focused
   same-token concurrency test was added Red-first during the final audit.
4. Red result recorded: 20 expected failures, 33 preserved tests passing.
5. Models, migration, checkout service, routes and pages implemented.
6. Automated, schema, local-upgrade and isolated browser checks completed.

## Automated results

### Final focused checkout/cart/migration run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py -q --basetemp=.pytest-tmp\mm025-final-focused
```

Final result including the added overlapping same-token case:
**54 passed in 45.74 seconds**.

Covered order constraints, exact Decimal values, signed tokens, stale prices,
forged fields, CSRF, order ownership, double submission, expired-form recovery,
rollback, one-product/two-buyer concurrency, migrations and all MM-019 cart
regressions.

### Targeted older-feature regression run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_marketplace.py tests\test_live_search.py tests\test_seller_profile.py tests\test_mobile_navigation.py tests\test_hardening.py -q --basetemp=.pytest-tmp\mm025-regression
```

Result: **167 passed in 212.89 seconds**.

### Complete project suite

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm025-final-full2
```

Final result after every implementation, schema-alignment and retry-concurrency
change: **446 passed in 510.48 seconds**.

## Migration and real local database

The server process was not running. Before migration, the existing database was
copied to:

```text
instance/backups/market-mirror-before-mm025-20261107-001347.sqlite
```

Backup size: 159,744 bytes. SHA-256:
`3C48A03274E605659EC09055940A825F524385999BD9ADDA89848CF4C4C316D6`.

The additive migration completed:

```text
f19c7a42e0b1 -> a25c0de02501
```

`local.ps1 check` initially identified one model/migration index declaration
mismatch. `ix_order_items_product_id` was declared in the model to match the
already approved migration design. The repeated check then reported:

```text
No new upgrade operations detected.
```

`python -m pip check` also reported **No broken requirements found**.

The real database was never downgraded and no real checkout/order was created
during verification.

## Isolated browser result

The browser used `tests.preview_checkout` on loopback port 5025 with a temporary
SQLite database under `.pytest-tmp`.

Observed results:

- signed in as the fictional fixture buyer;
- cart showed two products from different sellers and exact `$199.95 USD`;
- cart disclosed that checkout records a local order but takes no real payment;
- Checkout redirected to `/orders/1/success`;
- one H1 read **Thank you for your purchase**;
- receipt showed Order #1, both title/seller snapshots, `$120.50 USD`, `$79.45
  USD`, and exact `$199.95 USD` total;
- no-real-payment/no-delivery disclosure was visible;
- narrow mobile layout and fixed bottom navigation remained readable;
- refresh still showed Order #1 rather than creating another order; and
- Cart then showed `0 items in cart` and the empty state.

The temporary server was stopped. No real demo listing was sold.

## Remaining honest limits

- PostgreSQL row locking is designed and statement-level portable but no live
  PostgreSQL server is installed/configured on this computer.
- A payment provider is intentionally absent; this is a local classroom
  transaction.
- Actual email receipt, seller payout, shipping, tax, refunds and cancellations
  remain outside MM-025.
