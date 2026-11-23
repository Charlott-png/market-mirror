# MM-024 Red verification

Date: 2026-11-06 (Asia/Shanghai)

## Test collection

Before application implementation, the MM-024 and existing MM-023 modules
collected successfully:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py --collect-only -q
# 52 tests collected in 1.88s
```

This proves the new test files, fixtures and imports are syntactically valid.

## Red execution

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm024-red
# 16 failed, 36 passed in 19.14s
```

Expected missing-feature failures were observed for:

- absent `load_local_environment()` and `.env` support;
- old OpenAI provider/model defaults;
- configuration rejecting Gemini or accepting a mismatched OpenAI/Gemini model;
- Gemini key not making the feature available;
- disabled checkbox and non-Gemini disclosure;
- absent `app.ai.gemini_vision` adapter;
- absent provider factory/selection helper; and
- absent Gemini placeholders in `.env.example`.

The 36 passing contracts confirm that the unchanged MM-023 result validator,
image cleaning, endpoint authentication/CSRF, rate limiting, no-business-write
behavior, OpenAI adapter, JavaScript race guards, CSS and unrelated-page scope
remain intact before MM-024 implementation.

No Google/OpenAI request was made, no API key was read, and no package or
application implementation was changed during the Red stage.
