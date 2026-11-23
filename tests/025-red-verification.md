# MM-025 Red verification

Date: 2026-11-06 (Asia/Shanghai)

## Test-first boundary

At this checkpoint only test and test-documentation files were added or changed:

- `tests/test_checkout.py`
- `tests/test_checkout_migration.py`
- `tests/test_cart.py` (obsolete MM-019 checkout expectation only)
- `tests/025-browser-checklist.md`

No model, migration, route, service, template, CSS or local database change had
been made.

## Collection

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py --collect-only -q
```

Result: **53 tests collected** successfully. This proves the new tests were
syntactically valid and discoverable before implementation.

## Red run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_checkout.py tests\test_checkout_migration.py tests\test_cart.py -q --basetemp=.pytest-tmp\mm025-red2
```

Result: **20 failed, 33 passed in 31.80 seconds**.

Expected missing-feature failures were:

- 17 checkout/model cases reported `MM-025 Order model is missing`;
- the schema migration case reported missing `orders` and `order_items` tables;
- the raw migration case reported `no such table: orders`; and
- the updated cart contract reported the missing MM-025 `Order` model.

The MM-019 preservation test for upgrading/downgrading from the current head
already passed because, before the MM-025 revision exists, “upgrade” and
“downgrade to f19c7a42e0b1” are harmless no-ops that preserve the fixture row.
The schema-presence tests ensure this cannot create a false Green result.

There were no collection, fixture, syntax or accidental real-database failures.
This is a valid Red baseline, so SDD now permits application implementation.

## Additional concurrency Red check

During the final implementation audit, a planned edge case was made more
specific: two requests from the same buyer submitting the same signed token at
the same time. Its new focused test was written before the retry adjustment.

Initial result: **1 failed** because the first request returned 303 but the
overlapping request returned 400 after observing the newly empty cart. The
service was then changed to recheck the buyer/nonce after waiting for the
product lock. The exact test subsequently passed, proving both requests reach
the same receipt and only one order exists.
