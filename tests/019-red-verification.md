# MM-019 Red checkpoint — 2026-11-02

MM-019 and PLAN-019 were approved before these tests were written. No cart application code or migration existed during these runs.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_cart.py tests\test_cart_migration.py --collect-only -q
# 35 tests collected in 2.35s

.\.venv\Scripts\python.exe -m pytest tests\test_cart.py tests\test_cart_migration.py -q --basetemp=.pytest-tmp\mm019-red
# 35 failed in 70.42s (0:01:10)
```

The failures were expected and feature-specific:

- `CartItem` was absent from the model package;
- `/cart`, Add, Remove and Checkout routes did not exist;
- shared cards and navigation had no cart markup/count;
- the Alembic head did not create `cart_items`; and
- pagination/cart validation URLs therefore returned the old 404 behaviour.

There were no collection, syntax, fixture setup or unrelated baseline errors. The browser checklist was also defined before implementation in `tests/019-browser-checklist.md`.
