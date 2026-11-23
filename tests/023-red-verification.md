# MM-023 Red verification

Date: 2026-11-02 (Asia/Shanghai)

The approved pytest contracts and browser checklist were written before feature
implementation.

## Collection

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ai_vision.py --collect-only -q
# 31 tests collected in 2.94s
```

## Expected failing run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm023-red
# 30 failed, 1 passed in 47.90s
```

Expected missing-feature failures reached the unchanged application and found:

- no `/ai/vision-listing` route (404 rather than the specified responses);
- no vision disclosure, option, status, spinner or field markers;
- no `app.ai.vision` validation/orchestration module;
- no `app.ai.openai_vision` adapter;
- no vision configuration keys;
- no async race/dirty-field/privacy JavaScript behavior; and
- no vision-specific CSS.

The one passing negative-scope test confirmed Edit listing, Profile and Explore
did not already contain accidental vision controls. Collection succeeded without
the OpenAI SDK, API key or internet. The failures therefore represent the absent
MM-023 behavior rather than broken test setup.

