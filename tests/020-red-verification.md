# MM-020 Red verification — 2026-11-02

MM-020 and PLAN-020 were approved before test authoring. No application,
template, JavaScript or CSS implementation was changed before this checkpoint.

## Collection

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_live_search.py --collect-only -q
# 24 tests collected in 2.41s
```

Collection succeeded. This proves the test module and fixtures are valid even
though the feature is absent.

## Red run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_live_search.py -q --basetemp=.pytest-tmp\mm020-red
# 22 failed, 2 passed in 54.13s
```

The failures were expected and feature-specific:

- `/products/search` returned 404 instead of the approved JSON contract;
- Explore lacked the approved live-search form, status, spinner and result hooks;
- invalid AJAX requests could not yet return safe JSON validation;
- no AJAX fragments/canonical URL/pagination behavior existed;
- `market.js` lacked debounce, cancellation, race and recovery behavior; and
- `style.css` lacked the loading-spinner and reduced-motion rules.

The two passing tests were expected baseline guards:

- private **Your listings** did not incorrectly initialize live search; and
- existing seller-profile pagination still targeted its HTML page.

There were no collection, import, fixture, database-setup or unrelated baseline
failures. The Red checkpoint is therefore validated and implementation may begin.
