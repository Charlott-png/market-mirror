# MM-024 — Live Gemini vision provider and local secret setup

Status: IMPLEMENTED AND VERIFIED — approved and completed on 2026-11-06 (Asia/Shanghai)

Date: 2026-11-06 (Asia/Shanghai)

## 1. Purpose

Make the existing MM-023 image assistant work with a real, student-friendly
cloud vision service while preserving the manual Sell form and all MM-023
privacy, validation, rate-limit and failure protections.

The recommended provider is the **Google Gemini Developer API**, using the
stable **`gemini-3.5-flash-lite`** model. Google currently documents this model
as multimodal (including image input), capable of structured output, and
available with free-tier input and output. Pricing and quotas can change, so the
operator must check Google AI Studio before demonstrations.

API key page: <https://aistudio.google.com/apikey>

Official references:

- <https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite>
- <https://ai.google.dev/gemini-api/docs/pricing>
- <https://ai.google.dev/gemini-api/docs/api-key>
- <https://ai.google.dev/gemini-api/docs/image-understanding>
- <https://ai.google.dev/gemini-api/docs/structured-output>

## 2. Student setup experience

The student will:

1. sign in to Google AI Studio and create an API key at the URL above;
2. create `market-mirror/.env` by copying `.env.example`;
3. put these development values in the private `.env` file:

   ```dotenv
   VISION_AI_ENABLED=true
   VISION_AI_PROVIDER=gemini
   VISION_AI_MODEL=gemini-3.5-flash-lite
   VISION_AI_TIMEOUT_SECONDS=12
   GEMINI_API_KEY=PASTE_THE_REAL_KEY_HERE
   ```

4. keep `.env` out of screenshots, chat messages and source control; and
5. restart Market Mirror with `Start-Market-Mirror.bat` after changing `.env`.

The application will load `.env` automatically for local development without
overwriting environment variables already supplied by the operating system or a
hosting platform. `.env` is already ignored by `.gitignore`. The key must never
be copied into Python, JavaScript, HTML, the database or a committed file.

## 3. Provider and model behavior

Add `GeminiVisionProvider` using Google's official `google-genai` Python SDK.
It will:

- read `GEMINI_API_KEY` from the process environment;
- receive only the already normalized, metadata-free JPEG from MM-023;
- send one fixed product-identification instruction and that JPEG;
- use `gemini-3.5-flash-lite` by default;
- request JSON matching the existing MM-023 title/category/confidence schema;
- disable tools, grounding and unrelated data retrieval;
- set a short request timeout and no application-level automatic retry;
- return parsed provider output to the existing untrusted-output validator; and
- never receive the seller's username, email, filename, description, price or
  any other form fields.

The existing OpenAI adapter remains available as an optional configured
provider so MM-023 is not removed. Gemini becomes the recommended and documented
local default for new setup.

## 4. Availability and checkbox rules

The Sell-page AI checkbox is enabled only when all of these are true:

1. `VISION_AI_ENABLED=true`;
2. `VISION_AI_PROVIDER` is a supported provider;
3. the selected provider's API key is present and nonblank; and
4. the provider/model configuration is valid.

For Gemini, the required secret is `GEMINI_API_KEY`. For the retained OpenAI
provider, it remains `OPENAI_API_KEY`.

A key alone does not silently activate image sharing. The explicit
`VISION_AI_ENABLED=true` setting is also required. This is an intentional
privacy control.

When configuration is incomplete, the checkbox stays disabled and the complete
manual Sell form remains usable. The page must not reveal which secret is
missing or display any part of a key.

## 5. Privacy disclosure

When Gemini is active, the Sell page must explain, in beginner-friendly text,
that:

- after the local preview succeeds, Market Mirror sends a resized,
  metadata-free copy of the selected photo to Google's Gemini API;
- the suggestion is optional and must be reviewed;
- the original upload is not sent by this analysis path; and
- Google's free tier may use submitted content to improve Google products,
  according to Google's current pricing documentation.

The existing per-form checkbox remains checked by default only because the
server operator explicitly enabled the feature. The seller can uncheck it before
selecting a photo or while a request is pending. Unchecking cancels/ignores the
result and never blocks manual listing creation.

## 6. Configuration validation

Supported provider values become `gemini` and `openai`.

Recommended defaults:

```text
VISION_AI_ENABLED=false
VISION_AI_PROVIDER=gemini
VISION_AI_MODEL=gemini-3.5-flash-lite
VISION_AI_TIMEOUT_SECONDS=12
```

Configuration rules:

- timeout remains a whole number from 3 through 30 seconds;
- provider and model names remain short printable strings;
- an enabled unsupported provider fails at startup with a safe explanation;
- Gemini model names must begin with `gemini-`;
- OpenAI model names must not be accepted for the Gemini provider, and vice
  versa;
- neither API key is copied into Flask's configuration dictionary; and
- no error, response or log may contain an API key or raw provider response.

## 7. Request and response contract

The browser continues to call the existing authenticated and CSRF-protected
`POST /ai/vision-listing` endpoint. No new public endpoint is required.

Successful JSON remains:

```json
{
  "suggestion": {
    "title": "Silver laptop computer",
    "category": "electronics"
  },
  "confidence": {
    "title": 0.91,
    "category": 0.94
  },
  "message": "AI suggestions are ready. Review them before saving."
}
```

The existing seven internal categories, confidence threshold, partial-result
behavior and strict output validation remain unchanged. Provider timeouts,
quota errors, safety blocks, malformed JSON and network failures return the
existing generic unavailable response. They never prevent manual entry.

## 8. Cost and abuse controls

- Keep the existing per-user limit of 10 vision analyses per 10 minutes.
- Send one image per request, resized so its longest side is at most 1024 pixels.
- Request a small structured response only.
- Do not use Google Search grounding, Maps, code execution, file storage or any
  paid tool.
- Do not automatically retry failed requests.
- Do not enable billing as part of this feature.
- The student should monitor the Google AI Studio usage dashboard because free
  quotas and eligibility are controlled by Google and can change.

## 9. Dependency and documentation changes

Add and lock:

- `google-genai` for Gemini API access; and
- `python-dotenv` for local `.env` loading.

Update:

- `.env.example` with safe Gemini placeholders;
- the local setup guide with copy-and-paste steps;
- the MM-023 disclosure so it names the configured provider rather than always
  saying OpenAI; and
- a troubleshooting section for missing key, quota exceeded, unsupported
  region, network failure and model access errors.

No real key will be created, requested in chat, committed, printed or placed in
test fixtures by the implementation.

## 10. Test requirements

Tests must be written and observed failing before implementation. They must
cover:

### Configuration and secrets

- `.env` is loaded for local startup without overriding an existing environment
  variable;
- `.env` remains ignored by Git;
- Gemini is unavailable when disabled or when `GEMINI_API_KEY` is absent/blank;
- Gemini becomes available when enabled, validly configured and keyed;
- the key is absent from application configuration, responses and logs;
- unsupported provider/model combinations fail safely; and
- OpenAI configuration remains supported.

### Gemini adapter

- the official client receives the configured model, cleaned JPEG and fixed
  instruction;
- structured output contains exactly the established MM-023 fields and allowed
  category enum;
- no username, email, filename or unrelated form value is transmitted;
- no tools, grounding or file-upload storage is enabled;
- valid JSON is returned to the shared validator;
- malformed, empty, blocked, timed-out, quota and network responses fail safely;
  and
- test doubles make zero real Google network calls.

### Endpoint and interface

- a successful fake Gemini analysis fills untouched Title and Category fields;
- user-edited fields, cancellation, stale-response and partial-result rules from
  MM-023 still pass;
- disclosure names Google Gemini and explains free-tier data use;
- missing configuration leaves the checkbox disabled and manual form complete;
- authentication, CSRF, image cleaning, no-business-write, rate-limit and
  no-storage tests continue to pass; and
- Edit Listing and unrelated pages receive no vision interface.

### Manual live verification

After automated tests pass, the student may add their own key locally and use a
non-personal generated product image to verify one real response. This check
must never expose the key, use a personal photo, create a paid subscription or
modify the real catalogue unless the student intentionally saves the listing.

## 11. Acceptance criteria

MM-024 is complete when:

1. the documented `.env` values plus a valid Gemini key make the checkbox
   enabled after restart;
2. selecting a valid product photo produces a real Gemini title/category
   suggestion through the existing endpoint;
3. manual entry works with no key, invalid key, quota exhaustion or provider
   failure;
4. AI output cannot overwrite seller-edited fields or save a listing;
5. secrets never reach client code, logs, Flask configuration or source control;
6. the Google/free-tier privacy disclosure is visible before analysis;
7. all new tests and the complete existing project suite pass; and
8. setup and troubleshooting instructions are understandable to a high-school
   student.

## 12. Out of scope

- Creating a Google account or API key on the student's behalf.
- Enabling billing, purchasing credits or guaranteeing future free-tier access.
- Sending personal, sensitive or copyrighted private images to a provider.
- Client-side Gemini calls that would expose the secret key.
- Automatic checkout, listing submission or database writes from model output.
- Removing the existing OpenAI adapter.
- Public deployment or multi-user production secret management.

## 13. SDD approval gate

No implementation, dependency installation or production test will begin until
the user explicitly approves MM-024. After approval, the next artifact will be
PLAN-024, which must also be approved before tests and implementation begin.
