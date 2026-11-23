# PLAN-023 — AI vision title and category assistant

Status: APPROVED — user explicitly approved PLAN-023 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

Approved specification: MM-023, explicitly approved by the user on 2026-11-02.

## 1. Outcome and boundaries

Add an optional automatic vision-assistance path to the existing MM-022 image
selector on `/listings/new`:

- after the selected image has passed the existing browser checks and decoded
  for preview, send one normalized temporary copy to an authenticated same-origin
  endpoint;
- use OpenAI's Responses API with a configurable vision-capable model;
- pre-fill only untouched Title and Category fields;
- never overwrite seller edits or submit/save a listing;
- fail back to the normal manual form without blocking the user; and
- store no analysis image or suggestion as product/business data.

There is no database migration, permanent draft, background queue, image cache,
model training, public deployment or Edit-listing analysis in PLAN-023.

The existing persistent `RateLimit` table will receive the normal security
counter update. This is the sole technical database write caused by an analysis
request. It is required by MM-023's approved rate-limit requirement; no Product,
ListingSubmission, InteractionEvent or other business-data row is created.

## 2. Official API decision

The first concrete provider will be **OpenAI**, isolated behind Market Mirror's
own provider interface.

Provider configuration:

```text
VISION_AI_ENABLED=false              # safe default
VISION_AI_PROVIDER=openai
VISION_AI_MODEL=gpt-6-luna
VISION_AI_TIMEOUT_SECONDS=12
OPENAI_API_KEY=<secret, never committed>
```

API design:

- OpenAI **Responses API**;
- model default: `gpt-6-luna`;
- one metadata-free JPEG supplied as a Base64 data URL;
- `detail: "low"` because this task needs coarse product recognition, not OCR or
  precise spatial coordinates;
- `reasoning.effort: "none"` or the equivalent supported SDK option for this
  constrained extraction task;
- strict Structured Outputs/JSON Schema;
- `store: false` so the response is not intentionally stored as response state;
- no tools, web search, file search, code execution, conversation, previous
  response, remote URL or streaming;
- a small output limit sufficient for one structured object; and
- one request with no automatic retry.

Why `gpt-6-luna`: the official model page describes it as the efficient model
for focused, high-volume tasks and confirms image input, the Responses endpoint
and Structured Outputs. The model is configuration rather than hard-coded
business logic, so an operator can change it after separate evaluation.

Official sources checked for this plan:

- [OpenAI Images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna)

The application will not claim a fixed per-request cost because billing depends
on current pricing and image tokenization. Tests and browser fixtures make no
real API call. A real provider check is optional and requires the user to add
their own key after implementation.

## 3. Planned files and responsibilities

| File | Planned change |
| --- | --- |
| `config.py` | Parse non-secret vision enable/provider/model/timeout settings with safe validation; never return the API key in Flask config. |
| `.env.example` | Document disabled-by-default variables and an `OPENAI_API_KEY=REPLACE...` placeholder only. |
| `requirements.txt` | Add the official OpenAI Python SDK within a compatible major-version range selected at implementation time. |
| `requirements-lock.txt` | Regenerate the exact verified environment lock after dependency installation. |
| `app/images.py` | Extract reusable side-effect-free image validation/normalization; retain the exact storage behavior through `store_image()`. |
| `app/ai/vision.py` | Define result validation, confidence/abstention policy, fixed instruction, provider protocol and orchestration. |
| `app/ai/openai_vision.py` | Implement the OpenAI Responses adapter, strict schema request, timeout/error translation and secret-safe behavior. |
| `app/ai/routes.py` | Add authenticated `POST /ai/vision-listing`, rate limit, in-memory normalization, provider call and public JSON/error mapping. |
| `app/templates/_image_dropzone.html` | Add the enabled control, provider-location disclosure, loading/status/suggestion markers and stable accessible IDs. |
| `app/static/js/market.js` | Extend the guarded MM-022 state machine with analysis lifecycle, dirty-field protection, abort/stale-result handling and safe fills. |
| `app/static/css/style.css` | Style the compact AI option, spinner, field markers and mobile/error states using existing theme variables. |
| `tests/test_ai_vision.py` | Define route, image, provider, output, rate-limit, privacy, failure and static client contracts before implementation. |
| `tests/test_image_dropzone.py` | Add focused MM-022 integration contracts proving preview/drop and existing text AI continue to behave correctly. |
| `tests/023-browser-checklist.md` | Define real-browser success, races, manual-edit preservation, mobile, accessibility and fallback scenarios before implementation. |
| `tests/preview_ai_vision.py` | Run an isolated temporary database plus deterministic fake vision provider; never read the real database/key or use the internet. |
| `tests/023-red-verification.md` | Record collection and expected missing-feature failures. |
| `tests/023-green-verification.md` | Record focused/regression/full-suite and browser evidence honestly. |
| `docs/023-ai-vision-guide.md` | Explain vision input, structured outputs, confidence limits, privacy, async races and provider abstraction at high-school level. |

No model/database migration, product schema, media route, seller profile, cart,
message or deployment file change is planned beyond dependency/configuration
documentation.

## 4. Configuration design

`environment_settings()` will parse:

- `VISION_AI_ENABLED`: only explicit true-like values enable provider use;
- `VISION_AI_PROVIDER`: `openai` initially; unsupported configured values fail
  startup only when enabled;
- `VISION_AI_MODEL`: defaults to `gpt-6-luna`, bounded to a short non-control
  string and never accepted from HTTP input;
- `VISION_AI_TIMEOUT_SECONDS`: numeric, bounded to 3–30 seconds, default 12; and
- `VISION_AI_EXTERNAL`: derived server-side from provider choice, not trusted
  from the browser.

`OPENAI_API_KEY` remains in the process environment and is read lazily by the
provider adapter. It is not copied into `application.config`, HTML, JSON, logs,
exceptions or tests.

Behavior matrix:

| Enabled | Provider/key state | Sell page behavior |
| --- | --- | --- |
| false | anything | AI control is visibly unavailable/off; ordinary MM-022 form works and makes no analysis request. |
| true | supported + key | AI control is checked by default and external-provider disclosure is visible. |
| true | key missing | Application still starts; AI control is disabled with a setup-safe unavailable message; endpoint returns 503 without SDK call. |
| true | unsupported provider | Fail configuration validation clearly at startup rather than silently using another provider. |

Test configuration injects a fake analyzer callable/factory through a dedicated
config key such as `VISION_AI_ANALYZER_FACTORY`. Production never accepts that
value from environment variables or HTTP requests.

## 5. Reusable image-normalization design

Refactor `app/images.py` without weakening current validation.

Conceptual helper:

```python
def normalized_image_bytes(upload, *, max_dimension, quality):
    """Validate one upload and return a new metadata-free JPEG in memory."""
```

It preserves:

- read ceiling of 5 MiB plus one detection byte;
- JPEG/PNG only;
- exactly one frame;
- 12-million-source-pixel maximum;
- decompression-bomb warning/error handling;
- `verify()` followed by a fresh decode;
- EXIF transpose;
- RGBA conversion and white flattening for transparency;
- a fresh RGB output with no source metadata; and
- safe public `ValueError` messages.

`store_image()` calls the helper with the existing 1600-pixel maximum and JPEG
quality 85, then performs the current pending-file/atomic-replace workflow.
The vision route calls it with a 1024-pixel maximum and quality 80 and never
writes the returned bytes.

Tests will compare pre-refactor and post-refactor behavior for valid JPEG/PNG,
transparent/EXIF images and every rejection/cleanup path. Listing storage must
continue to generate the same UUID filename pattern and safe file semantics.

## 6. Provider-neutral vision orchestration

`app/ai/vision.py` owns code that should not know OpenAI SDK response classes:

- internal `VisionSuggestion` data structure;
- provider protocol `analyze(clean_jpeg: bytes) -> mapping`;
- exact allowed category keys copied from `CATEGORIES` at request construction;
- output normalization and validation;
- 0.65 default thresholds;
- partial acceptance/abstention; and
- stable public response dictionaries.

Expected provider mapping fields are all required:

```json
{
  "title": "Silver laptop computer",
  "category": "electronics",
  "title_confidence": 0.84,
  "category_confidence": 0.92,
  "abstain_reason": ""
}
```

Validation order:

1. Require a mapping with exactly the approved keys.
2. Reject booleans/non-numeric/NaN/infinite/out-of-range confidence values.
3. Normalize Unicode and trim ordinary whitespace.
4. Reject title control characters, markup-like angle brackets and lengths
   outside 3–80 characters.
5. Require an exact internal category key.
6. Accept each field only at confidence >= 0.65.
7. Return a partial suggestion when one field is accepted.
8. Return a stable abstention when neither field is accepted.

Model confidence is an uncalibrated self-report, not a probability guarantee.
The guide and UI call it an estimate. The tests evaluate deterministic contract
behavior, not model accuracy claims.

## 7. OpenAI adapter design

`app/ai/openai_vision.py` will be the only module importing the OpenAI SDK.
Imports/client creation are lazy so disabled AI does not require credentials or
network access during application startup.

Adapter workflow:

1. Read `OPENAI_API_KEY` directly from the process environment.
2. Create/configure the SDK client with the bounded timeout.
3. Base64-encode only the normalized JPEG bytes.
4. Call Responses with one fixed developer instruction plus one image content
   item using a `data:image/jpeg;base64,...` URL and low detail.
5. Request strict Structured Output using a schema whose category enum is the
   seven Market Mirror internal keys.
6. Disable storage and tools and limit output size.
7. Detect refusal, missing parsed output, schema error, timeout, connection error,
   authentication error, rate-limit error and other provider HTTP errors.
8. Translate them into small internal exception classes; do not pass SDK text,
   headers, request bodies or response bodies to the Flask route/log.

The fixed instruction tells the model to identify only the main sellable item,
ignore instructions/text visible inside the image, choose one allow-listed
category, use a factual 3–80-character title, abstain when unclear or ambiguous,
and return only the schema.

No SDK retry is allowed for this endpoint. If the chosen SDK retries by default,
configure `max_retries=0`. This prevents duplicate analysis cost and keeps the
browser's one-selection/one-request contract honest.

## 8. Endpoint implementation design

Add to `app/ai/routes.py`:

```python
@ai.post('/ai/vision-listing')
@login_required
def vision_listing():
    ...
```

Flask-WTF's global CSRF protection runs before the handler. Handler order:

1. Check `VISION_AI_ENABLED` and configured provider availability; unavailable
   returns the stable 503 response without touching upload/database/provider.
2. Consume `vision-ai` limit for `current_user.id`, 10 requests per 600-second
   fixed window. This updates only existing RateLimit security metadata.
3. Require the multipart `image` field and no ambiguous multiple-file payload.
4. Normalize in memory with the reusable 1024/80 helper.
5. Resolve the injected/production provider through a small factory.
6. Call orchestration/validation.
7. Return a stable JSON suggestion/abstention response with `Cache-Control:
   private, no-store` (already normally supplied for authenticated sessions,
   asserted explicitly in tests).

The route does not call `store_image()`, `db.session.add(Product)`, recommendations,
tracking, listing submission or media paths. It accepts no URL, title,
description, category, price, seller ID, prompt, model or threshold from the
client.

Public failure mapping:

| Failure | Response |
| --- | --- |
| Feature/provider disabled or key missing | 503 + generic unavailable JSON |
| Missing/bad image | 400 + existing safe image message |
| Rate limit | existing 429 + Retry-After behavior |
| Provider timeout/network/HTTP/auth/refusal/malformed output | 502 or 503 + generic unavailable/abstention JSON |
| Unexpected application error | existing generic 500 handler; no raw data logged |

No provider exception object is interpolated into logs. Safe log events contain
only `vision_analysis_success`, `vision_analysis_abstained` or
`vision_analysis_failed type=<internal-class>`, request ID and duration already
handled by request logging.

## 9. Template and disclosure design

Extend `_image_dropzone.html` with stable elements inside the field:

```text
label/switch or checkbox #vision-ai-enabled
p #vision-ai-disclosure
span #vision-ai-spinner [hidden] [aria-hidden=true]
p #vision-ai-status [aria-live=polite]
```

When externally configured, disclosure wording is equivalent to:

> When enabled, selecting a photo sends a resized, metadata-free copy to the
> configured OpenAI vision service for title and category suggestions.

When disabled/unconfigured, render an unchecked disabled control plus:

> AI photo suggestions are unavailable. You can enter the title and category
> yourself.

Do not render provider key, model ID, detailed error, billing information or
user data. The existing file input's `aria-describedby` gains the disclosure and
vision status IDs without losing MM-022 instruction/help/status/error IDs.

Add separate small markers near Title and Category, such as
`#title-ai-marker`/`#category-ai-marker`, through the listing form only. They
start hidden and say **Suggested by AI — review before saving** when applied.
Other forms and Edit listing receive no marker or vision behavior.

## 10. JavaScript state-machine design

Keep one guarded enhancement on the new-listing page and integrate with MM-022's
accepted/decoded file lifecycle rather than adding a competing `change` handler.

State:

```text
selectionSequence       increments whenever image state changes
analysisController      current AbortController or null
analysisSequence        request identity
titleTouched/categoryTouched
applyingAi              prevents programmatic fill from looking manual
aiAppliedTitle/Category exact last values inserted by AI
formLeaving             set on Save/submit/pagehide
```

### 10.1 Dirty-field tracking

- Title: `input` and `change` events mark touched unless `applyingAi`.
- Category: `change` marks touched unless `applyingAi`.
- Initial Electronics is considered untouched until user interaction.
- Pasting/typing/changing while a request is active wins over the model.
- Programmatic AI fill uses normal `.value` assignment under the guard and does
  not pretend to be seller input.

### 10.2 Starting analysis

After the MM-022 thumbnail `load` event confirms the current selection:

1. Check enabled control, endpoint configuration, `fetch`, `FormData` and CSRF.
2. Abort/supersede any prior analysis.
3. Increment/capture selection and request identities.
4. Construct a fresh `FormData`; append only `image` and CSRF token. Never use
   `new FormData(listingForm)`, which would transmit title/description/price.
5. Show the loading state without disabling the form.
6. POST to `/ai/vision-listing` with same-origin credentials.
7. Parse only successful JSON and validate its broad shape again before UI use.

If `AbortController` is missing, identity checks still prevent stale application;
the request may continue but its result is ignored. If `fetch`/FormData/CSRF is
missing, skip analysis and retain the manual form.

### 10.3 Applying a result

Before every field application, re-check:

- page/form is still present and not submitting;
- analysis/selection identity is current;
- the selected file is still the analyzed file;
- AI control remains enabled; and
- the individual field remains untouched.

Apply valid title/category independently. Set safe text markers with
`textContent`; never insert provider text as HTML. Announce **AI filled Title and
Category**, **AI filled Title**, **AI selected Category**, or a safe abstention.

If a field is touched, preserve it and optionally report the unused suggestion
as plain informational text without an Apply button in this first version.

### 10.4 Cancellation and cleanup

- New valid/invalid/rejected photo: abort current request, increment identity,
  clear status/markers for the old photo.
- AI control unchecked: abort and prevent future analysis.
- AI control rechecked: analyze the currently valid selected file once.
- Clear an old AI value only when current `.value` still exactly equals the
  recorded AI value and the field has not been touched.
- Form `submit` and `pagehide`: set leaving, abort/ignore late work, do not delay
  submission.
- Failure/timeout/429: stop spinner, keep fields/image/form, show manual fallback.

Existing `/ai/category` and `/ai/price` code continues deleting `image` from its
own FormData. Tests assert those requests remain image-free.

## 11. CSS and responsive design

Add narrowly scoped styles:

- `.vision-ai-option`: compact bordered/surface panel inside image field;
- checkbox/control retains native keyboard semantics and visible focus;
- `.vision-ai-spinner`: small theme-colored indicator with accompanying text;
- `.ai-field-marker`: muted, wrapping annotation below/near the field;
- success/error/loading states use text in addition to color;
- `[hidden]` always removes spinner/markers; and
- widths/min-width/overflow-wrap prevent 320px overflow.

If rotation animation is used, `@media (prefers-reduced-motion: reduce)` removes
it while leaving the textual loading state. No dependency or icon font is added.

## 12. Test-first files and coverage

Tests are written and validated Red before any feature implementation.

### 12.1 `tests/test_ai_vision.py`

Server/config/provider contracts:

- disabled default and application startup without key/SDK call;
- enabled fake-provider success;
- anonymous redirect/auth requirement and CSRF rejection;
- endpoint method/content type and stable no-store JSON;
- only `image` accepted; extra browser fields ignored/not forwarded;
- 10-per-600-second atomic persistent rate limit and separation from text `ai`;
- the single expected RateLimit technical row and no other table mutation;
- no upload/pending/orphan files after success/failure;
- JPEG/PNG/transparent/EXIF normalization to clean <=1024 JPEG;
- empty/corrupt/spoofed/animated/over-byte/over-pixel rejection;
- provider receives clean JPEG bytes and no filename/account/form data;
- strict full/partial/abstention output validation;
- confidence below/at/above 0.65;
- allowed/unknown/case-changed category keys;
- title boundaries, Unicode, markup/control rejection;
- NaN/infinity/boolean/missing/extra/wrong-type output;
- provider disabled/key missing/timeout/network/auth/rate/refusal/malformed cases;
- public/log redaction of secrets, Base64, filename and raw provider output;
- no retries and exactly one fake-provider call per accepted request; and
- Edit/unrelated routes never invoke provider.

### 12.2 Existing-image regression contracts

Extend or add focused tests proving:

- extracted normalizer preserves all current `store_image()` rules;
- listing creation/update/rollback and UUID storage remain unchanged;
- MM-022 local preview still works before/without provider;
- AI category and price endpoints still exclude image bytes;
- product image lightbox/media permissions remain unchanged; and
- full application startup works with vision disabled.

### 12.3 Static client contracts

Assert stable structural behavior, not minified formatting:

- guarded new-listing-only initialization;
- fresh FormData with only image/CSRF;
- `fetch('/ai/vision-listing')` and no automatic `.submit()`;
- AbortController plus monotonically increasing identity fallback;
- title `input` and category `change` dirty tracking;
- per-field untouched checks and guarded AI application;
- old AI exact-value cleanup rule;
- safe `textContent`, no `innerHTML`;
- submit/pagehide abort/ignore; and
- existing text AI `data.delete('image')` remains.

## 13. Planned test execution sequence

1. Obtain explicit PLAN-023 approval.
2. Add only pytest contracts and `tests/023-browser-checklist.md`.
3. Collect tests to prove they load against the unchanged application.
4. Run focused tests and record expected Red failures: missing config, endpoint,
   provider, markup, JS and CSS.
5. Implement reusable image normalization and keep existing image tests Green.
6. Implement provider-neutral validation and route with fake provider.
7. Implement OpenAI adapter without making a real call.
8. Implement template/CSS/JavaScript behavior.
9. Run focused MM-023 tests until Green without weakening contracts.
10. Run image/listing/AI/security/MM-022/mobile regressions.
11. Run the complete project suite.
12. Run isolated fake-provider browser checks on a separate local port.
13. Stop fixture, reset browser state, restart real port 5000 and perform only a
    read-only startup/manual-fallback check unless the user has separately added
    a real API key and requested a paid live check.
14. Record Green evidence and the beginner guide.

Planned commands (exact basetemp names may receive a unique suffix if present):

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ai_vision.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_ai_vision.py -q --basetemp=.pytest-tmp\mm023-red
.\.venv\Scripts\python.exe -m pytest tests\test_ai_vision.py tests\test_image_dropzone.py -q --basetemp=.pytest-tmp\mm023-green
.\.venv\Scripts\python.exe -m pytest tests\test_marketplace.py tests\test_hardening.py tests\test_ai.py tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm023-regression
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm023-full
```

Dependency installation/lock refresh occurs only after approval and may require
network permission. No package is installed merely to draft this plan.

## 14. Browser fixture and acceptance plan

`tests/preview_ai_vision.py` will create:

- a temporary SQLite database and upload/AI directories;
- one temporary authenticated seller;
- the real Sell page and MM-022 controls;
- generated landscape, portrait, transparent, ambiguous and corrupt fixtures;
- a deterministic fake provider whose queued responses can be success, partial,
  abstain, slow, old-last, malformed, timeout or failure; and
- fixture-only instrumentation for provider call count and sanitized request
  facts, never image contents.

Browser checklist:

1. AI-enabled disclosure appears before selection; ordinary form stays usable.
2. Picker and production drop event each create preview then exactly one analysis.
3. Success fills untouched Title/Category, marks both and never submits.
4. Typing Title during a delayed response preserves it while untouched Category
   may update.
5. Changing Category preserves it while untouched Title may update.
6. Editing an AI-filled field removes that marker and replacement image does not
   erase the seller's edit.
7. Rapid image replacement followed by old-last response applies only newest.
8. Uncheck before selection makes zero calls; uncheck mid-request prevents apply;
   recheck analyzes current valid image once.
9. Partial/low-confidence/abstention/malformed/timeout/429/503 responses produce
   safe status and fully usable manual form.
10. Save during slow analysis immediately submits visible values; late response
    cannot touch the navigated page.
11. Invalid MM-022 selections make no provider call.
12. Existing Suggest category/Suggest price still work without image transmission.
13. 320px and short landscape: disclosure/status/markers wrap, no overflow, Save
    and fixed bottom navigation remain usable.
14. Keyboard reaches native AI control, file input and fields; focus never moves
    on response; polite live status is present.
15. Reduced-motion/no-script/vision-disabled responses retain manual behavior.
16. Edit listing and unrelated pages have no vision elements/calls/errors.
17. Console has no unexpected warnings/errors and fixture call counts match.

No browser test uses the user's real database, real image, API key or paid model.

## 15. Privacy and data-flow verification

The plan will verify this exact flow:

```text
Selected file
    ├─ local object URL → browser thumbnail (MM-022)
    └─ multipart image + CSRF → Market Mirror /ai/vision-listing
                                  ├─ Pillow validation
                                  ├─ metadata removal + resize
                                  └─ normalized JPEG + fixed instruction
                                       → configured provider
                                           → strict suggestion JSON
                                               → untouched form fields only
```

Tests prove the provider input excludes:

- original filename and local path;
- username, email and seller ID;
- title, description, price, condition and current category;
- CSRF/session cookies;
- database rows, messages and other listings; and
- original EXIF/metadata.

The API key travels only in the SDK's provider authorization request. It never
travels to the browser or Market Mirror JSON. `store: false` avoids intentional
Responses state storage, but documentation will not claim zero provider
retention; the final guide will direct the operator to the provider's current
data policy before enabling a real key.

## 16. Regression and performance limits

- Maximum browser-to-Market-Mirror body remains governed by existing 6 MiB
  `MAX_CONTENT_LENGTH` and explicit 5 MiB image limit.
- Provider receives at most one <=1024×1024 quality-80 JPEG per request.
- Endpoint timeout is bounded; there is no retry/queue/background task.
- One analysis per accepted selection; no request on initial page load.
- No DB migration or new permanent table/index.
- No changes to product save transaction or media authorization.
- Full suite must pass with no key and no internet.

Provider quality is evaluated manually with a small documented classroom set
(for example laptop, bicycle, book, clothing, household item, ambiguous group),
but no accuracy percentage will be claimed from that tiny sample. Incorrect
suggestions are expected model limitations and remain editable.

## 17. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| AI overwrites seller work | Dirty flags, per-field checks, sequence identity and exact-value cleanup only. |
| Old response wins race | Abort plus monotonic selection/request identities checked before every apply. |
| Image leaks private metadata | Decode, EXIF-orient, render fresh RGB JPEG and exclude filename/account/form data. |
| Image prompt injection | Fixed instruction, no browser prompt, no tools, strict schema/allow-list and safe DOM assignment. |
| Provider output invents category/HTML | Exact enum, title validation, threshold and `textContent`/value only. |
| Paid calls duplicate | One request per selection, no retry, rate limit and replacement abort/ignore. |
| Provider/key absent | Disabled by default; lazy adapter; complete manual fallback. |
| Large/decompression image exhausts memory | Existing byte/pixel/frame/decompression protections before provider. |
| Provider error exposes secret/raw body | Internal exception mapping, generic public JSON and type-only safe logs. |
| Save waits on AI | Fields and Save remain enabled; submit aborts/ignores analysis immediately. |
| Refactor weakens image storage | Characterization tests before helper extraction and existing image regressions. |
| Tests spend money/use internet | Injected fake provider; network adapter mocked; no live call in pytest/browser fixture. |
| “Confidence” appears authoritative | Label as uncalibrated estimate and keep seller review mandatory. |
| Rate limit conflicts with “no writes” wording | Explicitly allow only existing RateLimit security metadata; snapshot every business table unchanged. |

## 18. Rollback and recovery

No schema/data migration is involved. Rollback order:

1. set `VISION_AI_ENABLED=false` for immediate operational disable;
2. remove the vision endpoint/provider modules;
3. remove vision template/CSS/JS elements while retaining MM-022;
4. keep or revert the image-normalization refactor only after existing image
   tests prove equivalent behavior;
5. remove OpenAI dependency/config documentation if no other feature uses it;
6. run MM-022, image/listing/AI/security and full suites; and
7. verify ordinary Sell/upload/save manually.

Because disabled-by-default manual behavior remains complete, provider downtime
does not require code rollback.

## 19. Beginner concepts to document

The final guide will explain:

- **vision model:** software that turns image pixels into an uncertain text guess;
- **API/provider:** another service Market Mirror calls through a narrow boundary;
- **Base64 data URL:** a text transport wrapper for the cleaned JPEG, not a public URL;
- **structured output/schema:** a strict shape the model response must follow;
- **allow-list:** only known Market Mirror category keys are accepted;
- **confidence threshold:** a heuristic cutoff, not proof the model is correct;
- **asynchronous request:** work finishes later while the form stays usable;
- **race condition:** an older request finishing after a newer selection;
- **AbortController and sequence number:** cancellation plus a second stale-result
  safety check;
- **dirty field:** a field the seller has edited and AI may not overwrite;
- **metadata removal:** rebuilding the picture without hidden EXIF details; and
- **dependency injection/fake provider:** tests replace the paid service with a
  predictable classroom double.

## 20. Approval gate

This plan commits to:

1. OpenAI Responses API as the first provider, defaulting to configurable
   `gpt-6-luna`, low image detail, strict structured output, no tools/retries and
   `store: false`;
2. vision disabled by default and no real key/call required for development,
   pytest, browser verification or normal app startup;
3. one memory-only normalized image request after a decoded MM-022 selection;
4. untouched-field-only automatic fill with strong stale-response/manual-edit
   protection;
5. no business-data/file writes, with the existing RateLimit security row as the
   one documented technical write;
6. a reusable image normalizer whose equivalence is tested before route/provider
   integration;
7. tests and browser checklist written and proven Red before implementation; and
8. no paid live API check unless the user later supplies/configures a key and
   specifically requests it.

The user explicitly approved **PLAN-023** on 2026-11-02. The Testing stage may
now begin; tests must be written and validated Red before implementation.
