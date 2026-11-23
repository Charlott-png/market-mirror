# MM-024 Green verification

Date: 2026-11-06 (Asia/Shanghai)

## Dependency verification

The official Google SDK and local environment loader were installed only in the
project's private virtual environment and pinned in `requirements-lock.txt`:

```text
google-genai==1.75.0
python-dotenv==1.2.4
```

Dependency consistency check:

```powershell
.\.venv\Scripts\python.exe -m pip check
# No broken requirements found.
```

## Focused automated verification

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm024-green-2
# 52 passed in 33.81s
```

Covered behavior includes:

- local `.env` loading without overriding process variables;
- Gemini disabled-by-default configuration;
- supported Gemini/OpenAI provider and model combinations;
- absence/blank-key fallback;
- key exclusion from Flask configuration, browser code, responses and logs;
- Gemini SDK timeout and single-attempt behavior;
- one cleaned JPEG plus fixed instruction and structured category schema;
- malformed/failing provider handling;
- provider-aware disclosure and complete manual fallback; and
- every existing MM-023 endpoint, privacy, validation, race and scope contract.

## Adjacent regression verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py tests\test_marketplace.py tests\test_hardening.py tests\test_database_config.py -q --basetemp=.pytest-tmp\mm024-regression
# 105 passed in 148.24s
```

This checks existing upload/drop-zone behavior, listing transactions, security
headers/logging and environment/database isolation.

## Browser-discovered regression and correction

The first isolated browser check showed that Title filled correctly, but the
Category select's ordinary default `electronics` value was incorrectly treated
as a seller edit. As required by SDD, a focused regression test was added first:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ai_vision.py::test_default_category_is_untouched_until_the_seller_changes_it -q --basetemp=.pytest-tmp\mm024-browser-red
# 1 failed in 3.08s
```

The JavaScript initialization was then corrected: a category becomes “touched”
only after its real `change` event. The complete focused vision set passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm024-browser-green
# 53 passed in 35.40s
```

## Complete project verification

The final complete run, including the browser-discovered regression contract:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm024-final
# 425 passed in 474.23s (0:07:54)
```

## Isolated browser verification

The loopback-only fake-Gemini fixture used a temporary SQLite database and
generated laptop illustration. It never read `.env`, contacted Google/OpenAI,
used provider quota or touched the real catalogue.

Observed results:

- Sell page displayed a checked, enabled AI option;
- disclosure named Google Gemini, metadata removal and free-tier product
  improvement use;
- selecting the generated laptop displayed the local thumbnail first;
- fake response filled Title with `Silver laptop computer`;
- Category changed from the untouched Electronics default to Sports & Outdoors;
- both fields displayed AI review markers;
- status said the suggestions were ready for review;
- URL remained `/listings/new`, proving no automatic listing submission; and
- browser console contained no warnings or errors.

The fixture server was stopped after verification.

## Deliberately not performed

No real Google API request was made because the student's private key does not
belong in source, tests, logs or chat. The optional real-provider check is ready
after the student privately creates `.env` using
`docs/024-gemini-vision-setup.md`. MM-024 does not enable billing or guarantee
future free-tier eligibility.
