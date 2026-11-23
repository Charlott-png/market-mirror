# MM-021 Red verification

Date: 2026-11-02 (Asia/Shanghai)

The approved tests and browser checklist were created before application code.

## Collection

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_mobile_navigation.py --collect-only -q
```

Result: **32 tests collected successfully**.

## Expected failing run

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_mobile_navigation.py -q --basetemp=.pytest-tmp\mm021-red-2
```

Result: **27 failed, 5 passed**.

The failures were the intended missing-feature failures:

- `app.navigation` and its endpoint-group helper did not exist;
- the base template did not have separately named desktop/mobile navigation;
- pages had no mobile active state;
- Profile had no mobile Account shortcuts or Cart count;
- responsive bottom-navigation CSS and print rules did not exist.

The five passing checks covered existing protected-route behavior, reachability,
and secure logout behavior that MM-021 must preserve. This is a valid Red stage:
the new feature contracts failed before implementation for the expected reasons.
