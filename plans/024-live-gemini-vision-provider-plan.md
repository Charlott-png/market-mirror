# PLAN-024 — Live Gemini vision provider and local secret setup

Status: EXECUTED AND VERIFIED — user approved PLAN-024 on 2026-11-06 (Asia/Shanghai)

Date: 2026-11-06 (Asia/Shanghai)

Approved specification: MM-024, explicitly approved by the user on 2026-11-06.

## 1. Outcome

Connect the completed MM-023 image assistant to Google's real Gemini Developer
API without weakening the existing manual Sell form.

After implementation, a student can put a private Gemini key in `.env`, restart
Market Mirror, select a product photo and receive editable Title and Category
suggestions from `gemini-3.5-flash-lite`.

The implementation will preserve:

- manual listing creation when AI is disabled or fails;
- the existing image cleaning, authentication, CSRF and rate limits;
- protection against overwriting seller-edited fields;
- no automatic listing submission;
- no business-data or analysis-image storage; and
- optional OpenAI provider support from MM-023.

No database migration is needed.

## 2. Architecture

```text
Private .env file
    ├─ VISION_AI_ENABLED=true
    ├─ VISION_AI_PROVIDER=gemini
    ├─ VISION_AI_MODEL=gemini-3.5-flash-lite
    └─ GEMINI_API_KEY=<secret>
             │
             ▼
Flask configuration ── checks non-secret settings only
             │
             ▼
Sell page ── enables checkbox and names Google Gemini
             │
             ▼
Existing /ai/vision-listing endpoint
             │
             ├─ validates login, CSRF, rate limit and image
             ├─ creates metadata-free JPEG, at most 1024 px
             ▼
Provider selector ── GeminiVisionProvider
             │
             ▼
Google Gemini API ── image + fixed instruction + JSON schema
             │
             ▼
Existing strict MM-023 validator
             │
             ▼
Untouched Title/Category fields only
```

The API key remains in the process environment. It does not enter Flask's
configuration dictionary, a template, JavaScript, JSON, a database row or a
log message.

## 3. Planned file changes

| File | Planned responsibility |
| --- | --- |
| `requirements.txt` | Add compatible `google-genai` and `python-dotenv` ranges; retain the OpenAI SDK. |
| `requirements-lock.txt` | Record exact versions installed in the verified private environment. |
| `.env.example` | Replace the recommended vision example with Gemini placeholders and keep optional OpenAI guidance. Never add a real key. |
| `.gitignore` | Retain and test the existing `.env` exclusion. |
| `app/__init__.py` | Load project-root `.env` before reading environment settings, with `override=False`; test configurations stay isolated. |
| `config.py` | Support `gemini` and `openai`, default to Gemini while disabled, validate provider/model compatibility and never return either key. |
| `app/ai/gemini_vision.py` | Add the only module importing Google Gen AI SDK; create one bounded, no-retry, structured image request. |
| `app/ai/vision.py` | Select provider by configuration, detect the appropriate key, expose a safe provider label and reuse the existing output validator. |
| `app/marketplace.py` | Pass safe availability/provider-display information only to the new-listing template. |
| `app/templates/_image_dropzone.html` | Replace hard-coded OpenAI wording with provider-aware Gemini privacy disclosure. |
| `tests/test_gemini_vision.py` | Add configuration, dotenv, adapter, secret-safety and provider-selection contracts before implementation. |
| `tests/test_ai_vision.py` | Update provider-neutral expectations while retaining every MM-023 security and UI contract. |
| `tests/024-browser-checklist.md` | Define fake-provider and optional student-key browser checks. |
| `tests/024-red-verification.md` | Record expected failures before implementation. |
| `tests/024-green-verification.md` | Record focused, regression, complete-suite and honest live-check results. |
| `docs/024-gemini-vision-setup.md` | Give copy-and-paste student instructions, privacy explanation and troubleshooting. |
| `README.md` | Link to the setup guide and distinguish offline AI features from optional live vision. |

The existing route, JavaScript race protections, CSS, image normalizer and
output validator should need no behavioral rewrite. They will be regression
tested rather than replaced.

## 4. Local `.env` loading

Add `python-dotenv` and load exactly the project-root `.env` before
`environment_settings()` runs:

```python
load_dotenv(project_root / ".env", override=False)
```

Important rules:

- an already-set Windows/hosting environment variable wins over `.env`;
- tests can explicitly disable dotenv loading or isolate environment variables;
- a missing `.env` is normal and does not stop startup;
- `.env.example` is documentation only and contains placeholders;
- `.env` stays ignored by Git; and
- the application never prints whether a particular secret value is valid.

Why this is needed: the existing `Start-Market-Mirror.bat` starts
`scripts/local.ps1`, which then starts Waitress directly. Waitress does not
automatically load Flask `.env` files, so Market Mirror must do it itself.

## 5. Configuration design

Disabled defaults:

```text
VISION_AI_ENABLED=false
VISION_AI_PROVIDER=gemini
VISION_AI_MODEL=gemini-3.5-flash-lite
VISION_AI_TIMEOUT_SECONDS=12
```

Supported combinations:

| Provider | Required environment secret | Model rule |
| --- | --- | --- |
| `gemini` | `GEMINI_API_KEY` | begins with `gemini-` |
| `openai` | `OPENAI_API_KEY` | must not begin with `gemini-` |

Behavior:

| Configuration | Result |
| --- | --- |
| AI disabled | App starts; checkbox disabled; manual form works. |
| Gemini enabled + key + valid model | Checkbox enabled; Gemini adapter is selected. |
| Gemini enabled + missing/blank key | App starts; checkbox disabled; endpoint returns generic 503. |
| OpenAI enabled + key + valid model | Existing OpenAI adapter remains usable. |
| Unsupported provider or mismatched model while enabled | Startup fails with a safe configuration explanation. |

`GEMINI_API_KEY` and `OPENAI_API_KEY` are read lazily from `os.environ` and are
never included in the mapping returned by `environment_settings()`.

## 6. Gemini adapter design

Create `GeminiVisionProvider` with injectable client support for tests.

Production client construction will be equivalent to:

```python
from google import genai
from google.genai import types

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(
        timeout=timeout_seconds * 1000,
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
)
```

The adapter will call `client.models.generate_content` once with:

- configured `gemini-3.5-flash-lite` model;
- `types.Part.from_bytes(clean_jpeg, mime_type="image/jpeg")`;
- one fixed instruction describing the classification task;
- no user-supplied prompt, tools, grounding, search or file upload;
- `response_mime_type="application/json"`;
- `response_json_schema` matching the existing five-field MM-023 provider
  mapping and seven-category enum;
- low randomness, a small output-token limit and no retry; and
- no filename, account details or other form fields.

The response text is parsed as JSON and passed to `validate_vision_result()`.
Even structured output is treated as untrusted because a remote model or SDK
can still fail or return unexpected data.

Provider exceptions are not interpolated into public responses or logs. The
route continues returning its generic manual-fallback message.

## 7. Provider selection

Refactor `app/ai/vision.py` into three small decisions:

1. `provider_key_present(provider)` checks only whether the correct environment
   secret is nonblank.
2. `vision_available()` requires explicit feature enablement, a supported
   provider and its key. The existing injected test analyzer remains available
   without a real key.
3. `build_vision_provider()` returns Gemini or OpenAI adapter using the configured
   model and timeout.

The provider label sent to the template is a fixed allow-listed label:

```text
gemini -> Google Gemini
openai -> OpenAI
```

No environment string is rendered directly as HTML.

## 8. Interface and disclosure

When Gemini is available, the disclosure will explain in plain language:

> After the preview appears, Market Mirror sends a resized, metadata-free copy
> to Google Gemini. Review every suggestion before saving. Google says free-tier
> submitted content may be used to improve its products.

When unavailable, the current manual-fallback wording remains.

The browser checkbox becomes enabled after a restart only when the complete
server configuration is ready. JavaScript never sees the key. Existing behavior
remains:

- unchecking prevents analysis;
- changing photos cancels/ignores older results;
- edited fields win over AI;
- suggestions use `textContent`/field values, never HTML; and
- Save Listing never waits for or triggers the provider.

## 9. Test-first work

No application implementation begins until PLAN-024 is approved. Then tests are
written first.

### 9.1 Configuration and dotenv tests

- missing `.env` does not break startup;
- `.env` values load for a local application;
- a process environment variable overrides the same `.env` value;
- tests do not accidentally read the student's real `.env`;
- `.gitignore` excludes `.env` but not `.env.example`;
- default provider/model are Gemini while feature remains disabled;
- enabled Gemini accepts its valid model and rejects incompatible models;
- enabled OpenAI remains accepted;
- unsupported providers fail safely;
- missing/blank Gemini key makes the feature unavailable; and
- both API key names are absent from Flask configuration and error text.

### 9.2 Adapter tests

Using a fake Google client, assert:

- exactly one `generate_content` call;
- configured model is used;
- input contains only fixed text plus clean JPEG bytes;
- JSON schema includes exactly the expected fields and all category keys;
- response MIME type is JSON;
- output limit is bounded;
- no tools, grounding, URL, file upload or account/form data;
- retry attempts equal one;
- timeout is correctly converted to SDK units;
- valid response JSON reaches the shared validator; and
- empty, malformed, blocked, quota, timeout and network outcomes become safe
  provider failures without leaking raw details.

### 9.3 Route and UI regression tests

- fake Gemini success retains the existing endpoint response;
- disclosure names Google Gemini and describes free-tier data use;
- enabled/keyed configuration makes the checkbox clickable;
- absent key disables it while leaving every manual field and Save available;
- authentication, CSRF, rate limiting and no-business-write rules remain;
- provider receives the cleaned <=1024 JPEG only;
- seller-edited field, stale response, cancellation and partial-result contracts
  remain unchanged;
- OpenAI fake-provider tests remain Green; and
- Edit/Profile/Explore still receive no vision controls.

### 9.4 Secret-safety tests

Canary keys and provider error bodies must be absent from:

- HTML and JSON responses;
- Flask configuration;
- captured logs;
- trace-safe public error messages;
- source-controlled example files; and
- browser JavaScript.

Pytest and browser fixtures make zero real Google or OpenAI calls.

## 10. Red-stage sequence

After plan approval:

1. add `tests/test_gemini_vision.py` and update provider-neutral MM-023 tests;
2. add the MM-024 browser checklist;
3. collect tests to confirm syntax/fixtures load;
4. run the focused tests against unchanged code;
5. verify failures are caused by missing dotenv/Gemini/provider-label behavior;
6. record counts and representative failures in `tests/024-red-verification.md`;
7. do not weaken tests merely because implementation is difficult; and
8. only then begin dependency and application changes.

Planned Red commands:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm024-red
```

## 11. Implementation order

1. Add dependency ranges and install them in the private `.venv`.
2. Refresh exact versions in `requirements-lock.txt`.
3. Add isolated `.env` loading and configuration validation.
4. Add `GeminiVisionProvider` with injected-client unit tests.
5. Add provider selection/availability/label helpers.
6. Update the Sell-page disclosure without changing JavaScript behavior.
7. Update `.env.example`, README and setup guide.
8. Run focused tests until Green.
9. Run adjacent configuration, security, upload, AI and marketplace tests.
10. Run the complete project suite.

If dependency download requires network permission, request it only at step 1.
No real key is required for automated tests.

## 12. Green verification sequence

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gemini_vision.py tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm024-green
.\.venv\Scripts\python.exe -m pytest tests\test_image_dropzone.py tests\test_marketplace.py tests\test_hardening.py tests\test_database_config.py -q --basetemp=.pytest-tmp\mm024-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm024-full
```

Also verify:

- importing and starting the app without keys performs no external request;
- the real local app shows the disabled manual fallback before a key is added;
- a deterministic fake-provider browser fixture fills Title/Category correctly;
- 320-pixel layout has no horizontal overflow; and
- no unexpected browser-console errors appear.

## 13. Optional real-provider check

Automated tests will not use the student's key. After all tests pass, the
student can create their private `.env` and restart the server.

The one real check will use a generated, non-personal product image. Before the
request, verify the disclosure and checked control. After it finishes, verify:

- Title and Category are filled and marked for review;
- no listing exists until Save Listing is deliberately selected;
- the provider receives no filename/account/form fields by design;
- the page remains usable if Google returns quota, region or authentication
  errors; and
- the secret is never displayed or copied into the chat.

Creating the Google account/key and accepting Google's terms remains a user
action. The implementation will never enable billing.

## 14. Student documentation

`docs/024-gemini-vision-setup.md` will explain:

- **API key:** a private password that identifies the project to Google;
- **environment variable:** a setting available to the program but not written
  into source code;
- **`.env`:** a private local file that supplies environment variables;
- **SDK:** a package that handles safe HTTP communication with the API;
- **multimodal model:** a model that can read both text instructions and image
  pixels;
- **structured output:** requiring a predictable JSON shape;
- **free tier:** limited service that can change and is not a permanent price
  guarantee;
- **provider privacy:** the free tier may use submitted content for product
  improvement, so avoid personal/sensitive photos; and
- **server-side secret:** the browser calls Market Mirror, while only the Flask
  server knows the provider key.

The guide will include exact key URL, `.env` text, restart steps and common
errors such as missing key, unsupported region, quota exceeded and network
failure.

## 15. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Key committed or displayed | `.gitignore`, placeholder-only examples, no key in config/templates/logs/tests. |
| Free tier changes | Link current pricing/usage dashboard; no permanent free claim. |
| Free-tier content use surprises seller | Visible provider-specific disclosure before analysis. |
| SDK retries and duplicates usage | `HttpRetryOptions(attempts=1)` and existing local rate limit. |
| Wrong provider/model combination | Startup validation with explicit safe error. |
| Gemini returns unsafe/malformed text | Structured schema plus existing strict server validator. |
| Seller work is overwritten | Existing MM-023 dirty-field and stale-response protections. |
| Google is unavailable | Generic failure and complete manual fallback. |
| Test accidentally spends quota | Injected fake client; no real key/network in pytest or fixture. |
| `.env` overrides production settings | `override=False`; hosting environment wins. |
| Personal photo sent to free tier | Clear disclosure and documentation to use non-sensitive product photos only. |

## 16. Rollback

Immediate operational rollback requires only:

```dotenv
VISION_AI_ENABLED=false
```

Then restart the server. The manual Sell form continues working.

Code rollback can remove the Gemini adapter and its dependencies while retaining
MM-023's OpenAI adapter. No database or uploaded-file restoration is necessary
because MM-024 creates no schema or business-data changes.

## 17. Approval gate

This plan commits to:

1. Google Gemini Developer API with stable `gemini-3.5-flash-lite` as the
   recommended disabled-by-default provider;
2. local `.env` loading that never overrides an existing environment variable;
3. secrets staying server-side and outside Flask configuration/source control;
4. official `google-genai` SDK, one structured image request and no retry/tools;
5. preserving optional OpenAI support and every MM-023 manual/race/security rule;
6. tests written and proven Red before implementation;
7. no real provider call, billing action or key handling during automated work;
   and
8. an optional real check only after the student privately configures their key.

No tests, dependencies or implementation will be added until the user explicitly
approves PLAN-024.
