# MM-018 Red checkpoint — 2026-10-29

PLAN-018 was approved before writing tests. No application changes were made before these runs.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_seller_profile.py --collect-only -q
# 28 tests collected in 2.49s
.\.venv\Scripts\python.exe -m pytest tests\test_seller_profile.py -q --basetemp=.pytest-tmp\mm018-red
# 20 failed, 8 passed in 57.56s
```

Expected failures: missing dedicated profile/header/count/biography elements; no four-listing badge; old month-only date without semantic time element; generic empty state; duplicate page parameters incorrectly accepted. Responses otherwise rendered successfully. No test collection, import or fixture setup errors occurred.

Existing invalid-page checks (seven cases) and catalogue/owner-page preservation checks passed. Tests that fail earlier on missing markup will exercise their remaining assertions after implementation. Browser scenarios were defined beforehand in `018-browser-checklist.md`.
