# MM-028 Red Verification

Date: 2026-11-07 (Asia/Shanghai)

Approved inputs: MM-028 and PLAN-028.

## Collection

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_recently_viewed.py tests\test_mm028_migration.py --collect-only -q --basetemp=.pytest-mm028-collect
```

Result: **20 tests collected** successfully before implementation.

## Red run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_recently_viewed.py tests\test_mm028_migration.py -q --basetemp=.pytest-mm028-red
```

Result: **19 failed, 1 passed** in 36.11 seconds.

Representative intended failures:

- `RecentProductView` could not be imported;
- `recent_product_views` did not exist after migration upgrade;
- Explore and Dashboard lacked the Recently Viewed section/empty state;
- an authenticated user with personalization disabled received no view marker;
- product detail had no server-rendered `related-products` section;
- product detail still used the old `recommendations` widget contract; and
- the view POST JavaScript lacked the explicit same-origin credentials token.

The single passing case was the already-existing behavior where a category
with zero eligible alternatives did not contain the new section. It does not
implement the core feature.

Failures came from missing MM-028 behavior rather than broken fixtures or test
collection. This is the required Red checkpoint before implementation.

