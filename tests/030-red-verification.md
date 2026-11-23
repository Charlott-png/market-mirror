# MM-030 Red verification

Date: 2026-11-08 (Asia/Shanghai)

Specification: MM-030 approved on 2026-11-08.

Plan: PLAN-030 approved on 2026-11-08.

## Test-first checkpoint

The focused MM-030 contracts were added before any stylesheet or application
template implementation change.

Collection command:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_luxury_theme.py --collect-only -q
```

Result: **14 tests collected successfully**.

Red command:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_luxury_theme.py -q
```

Result: **12 failed, 2 passed**.

## Why this is valid Red evidence

The failures were caused by the intentionally absent MM-030 design:

- no Midnight & Gold token set;
- no Cinzel/Montserrat font system or Google Font links;
- no MM-030 stylesheet cache key;
- the header was not sticky;
- the footer was not deep-black/gold;
- product cards lacked the approved glass fallback/enhancement;
- Add to Cart was not a full-width gold bar;
- Explore lacked the scoped page hook and expanded spacing;
- forms/autofill/upload states lacked the new tokens;
- special components still used the previous palette; and
- no forced-colors boundary existed.

The two passing tests proved that the pre-existing form/security/JavaScript
hooks were intact and that the templates did not contain inline handlers or
external scripts. They are preservation contracts and were expected to remain
Green before and after implementation.

No assertion was weakened and no CSS, HTML, JavaScript, Python, database or
asset implementation change occurred before this Red run.
