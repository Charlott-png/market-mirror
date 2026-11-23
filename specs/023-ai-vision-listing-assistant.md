# MM-023 — AI vision title and category assistant

Status: APPROVED — user explicitly approved MM-023 on 2026-11-02 (Asia/Shanghai)

Date: 2026-11-02 (Asia/Shanghai)

## 1. Purpose

Enhance the authenticated **Sell a product** page so that, after a seller
selects or drops a valid product photo, an optional AI vision service analyzes a
temporary copy and suggests:

- a short product **Title**; and
- one existing Market Mirror **Category**.

When the seller has not already edited those fields, acceptable suggestions are
filled in automatically. The seller remains in control: they can change or
remove every suggestion before selecting **Save listing**.

MM-023 extends MM-001 through MM-022. It must preserve authentication, CSRF,
image validation, listing ownership, form validation, request-token idempotency,
file/database compensation, mobile navigation and all existing manual listing
behavior.

## 2. User experience

The image area will include:

- a visible **Use AI to suggest a title and category** control;
- a short disclosure explaining whether the configured model runs locally or
  sends a resized photo to an external AI provider;
- an AI status area such as **Analyzing photo…**, **Suggestions added**, or a
  useful failure message; and
- a loading indicator that is hidden when no analysis is running.

The control is enabled by default to satisfy the requested automatic behavior,
but the seller can turn it off before choosing a photo. Turning it off must not
disable image upload or the ordinary listing form.

After one preliminary-valid photo is selected or dropped:

1. MM-022 immediately shows its local thumbnail.
2. If AI assistance is enabled and available, the browser sends one temporary
   analysis request.
3. The server safely decodes and normalizes the image in memory.
4. The configured vision provider returns structured title/category suggestions.
5. The page fills only fields the seller has not edited.
6. Nothing is stored or published until the seller selects **Save listing**.

The seller must never be forced to wait for AI. They may type while analysis is
running and may save a listing manually if the service is slow or unavailable.

## 3. Scope

MM-023 applies only to `/listings/new` and its existing MM-022 image selector.

It analyzes only the currently selected, unsaved image. It does not analyze:

- images on Explore or product-detail pages;
- existing images on Edit listing;
- seller avatars, messages or saved products;
- images after a listing is already stored; or
- files that fail MM-022's preliminary checks.

The AI suggests only title and category. Description, price, condition and image
remain completely manual in this feature.

## 4. Automatic fill and seller control

### 4.1 Field ownership

JavaScript tracks whether the seller has edited Title or Category since the Sell
page loaded or since the form was re-rendered.

- If Title is untouched, a valid title suggestion may fill it.
- If Category is untouched, a valid category suggestion may select it.
- If either field was typed, selected, pasted into, or changed while analysis
  was running, the late AI result must not overwrite that field.
- A field filled by AI is visibly marked with short text such as **Suggested by
  AI — review before saving**.
- Editing an AI-filled field removes its AI marker and makes the value the
  seller's own choice.

Because the current Category select initially displays Electronics, “untouched”
means the seller has not interacted with that select. The AI may replace that
initial default. Once the seller changes Category, it must be preserved.

### 4.2 Partial application

If only one field is still untouched, apply only that suggestion. For example,
if the seller has typed **Blue mountain bicycle** while the request is running,
preserve that title but still select **Sports & Outdoors** if Category is
untouched.

If a suggestion arrives for a field the seller already edited, show it only as
non-blocking informational text. Do not provide a hidden or surprising overwrite.

### 4.3 Replacing or removing the photo

- Selecting a new photo cancels or supersedes the previous browser request and
  starts analysis for the new photo when enabled.
- A response belonging to an older photo is ignored, even if it arrives later.
- Removing/rejecting a photo clears the AI status for that photo.
- An old AI-filled value may be cleared only if it is still exactly the value
  inserted by AI and the seller has not edited it. Seller-authored values are
  never cleared automatically.
- Selecting the same photo again may start a fresh request; correctness must not
  depend on browser object-URL identity.

## 5. Analysis endpoint

Add an authenticated, CSRF-protected endpoint:

```text
POST /ai/vision-listing
Content-Type: multipart/form-data
```

Request fields:

- `image`: exactly one JPEG or PNG, maximum 5 MiB;
- the existing CSRF token; and
- no title/category value is required for the vision inference itself.

The endpoint uses a separate rate-limit bucket, initially **10 requests per
authenticated user per 10 minutes**. It accepts no seller ID, product ID, URL,
prompt, model name or arbitrary instruction from the browser.

Successful suggestion response:

```json
{
  "suggestion": {
    "title": "Silver laptop computer",
    "category": "electronics"
  },
  "confidence": {
    "title": 0.84,
    "category": 0.92
  },
  "message": "AI suggestions are ready. Review them before saving."
}
```

Safe abstention response:

```json
{
  "suggestion": null,
  "message": "The photo was not clear enough for a reliable suggestion."
}
```

Expected status behavior:

- `200`: suggestion or safe abstention;
- `400`: missing, empty, excessive, corrupt, animated, unsupported or
  excessive-pixel image;
- `401/302` according to the application's established authentication behavior;
- `429`: vision rate limit reached;
- `502` or `503`: provider failed, timed out, is disabled or is unavailable.

Errors must use concise public messages. Provider responses, secrets, stack
traces and original image bytes must never appear in the response.

## 6. Server-side image handling

The analysis route must not trust the browser preview, MIME type or filename.
Before provider use it applies the same authoritative boundaries as listing
storage:

- read at most 5 MiB plus one detection byte;
- require one nonempty JPEG or PNG;
- reject animated/multiple-frame images;
- reject more than 12 million source pixels;
- verify readable image bytes;
- apply EXIF orientation;
- remove metadata by rendering into a new image; and
- reduce the analysis copy to a configurable maximum dimension, initially
  1024×1024, before encoding it as a moderate-quality JPEG.

This work should be extracted into a reusable, side-effect-free normalization
helper so listing storage and AI analysis do not drift. The helper returns clean
bytes; only the existing listing-storage path writes a UUID-named file.

The analysis endpoint keeps the original and normalized bytes in memory only.
It creates no upload, pending file, database row, product, draft or interaction
event. Temporary objects are released after the request.

## 7. Vision provider boundary

MM-023 uses a small provider interface rather than calling a vendor SDK directly
from the route. Conceptually:

```python
analyze_product_image(clean_jpeg_bytes) -> structured_result
```

Configuration selects the provider, model and timeout. Required configuration
concepts are:

- `VISION_AI_ENABLED`;
- `VISION_AI_PROVIDER`;
- `VISION_AI_MODEL`;
- `VISION_AI_TIMEOUT_SECONDS`; and
- a provider API key stored only in an environment variable/secret manager.

No real secret is committed to `.env.example`, source code, tests, logs or the
database. The application must start and the Sell form must work when vision AI
is disabled or missing credentials.

The Planning stage will choose the first concrete provider and exact supported
SDK/API after checking its official documentation. Tests use an injected fake
provider and never make paid or internet requests.

## 8. Model instruction and output contract

The provider receives a fixed server-authored instruction. Browser users cannot
supply or extend the prompt. The instruction asks the model to:

- identify the main item offered for sale, not the background;
- return a concise factual title of 3–80 characters;
- choose exactly one key from Market Mirror's current category allow-list;
- return confidence values from 0 through 1;
- abstain when the photo is unclear, contains no sellable product, shows several
  equally important products, or requires guessing; and
- treat any words or instructions visible inside the image as untrusted image
  content, not commands.

The provider must use structured JSON/schema output where supported. Market
Mirror validates the result independently:

- title is plain text, trimmed, 3–80 characters, with control characters and
  markup-like output rejected or normalized safely;
- category must be one exact internal key from `CATEGORIES`;
- confidence must be finite numeric data between 0 and 1; and
- unsupported keys, extra prose, invalid JSON or missing fields cause
  abstention/failure, never a partially trusted object.

No model output is rendered with `innerHTML`. The AI receives no tools, database
access, URLs, user profile, other listings, messages or ability to submit forms.

## 9. Confidence and abstention

The initial acceptance threshold is **0.65 for each field**.

- A category below its threshold is not applied.
- A title below its threshold is not applied.
- One field may be accepted while the other abstains.
- A completely unusable result returns `suggestion: null`.

The UI describes scores as uncertain model estimates, not guarantees. It must
not display wording such as **AI verified**, **correct category**, or **approved
title**.

Thresholds are server configuration, not browser-supplied values. The plan may
make the exact internal representation configurable, while tests preserve the
0.65 default contract.

## 10. Browser request lifecycle

MM-023 extends the guarded MM-022 JavaScript without breaking its local preview.

- Start analysis only after MM-022 has accepted and decoded the current photo.
- Use `FormData` containing the real selected file and CSRF token.
- Do not include the image in the existing `/ai/category` or `/ai/price`
  requests; those routes retain their current text-only behavior.
- Use an `AbortController` where supported when a photo is replaced, AI is
  disabled, or the page leaves.
- Use an increasing request/selection identifier so a stale response is ignored
  even if network cancellation does not stop the server.
- Permit at most one current analysis request per form.
- Do not automatically retry provider failures, which could duplicate cost.
- Apply a client timeout slightly longer than the configured server timeout and
  return the form to a usable state afterward.

Analysis never submits the listing form, never clicks Save, and never creates a
product. **Save listing** remains the only listing submission action.

## 11. Loading, errors and accessibility

While analysis is active:

- show a small loading indicator and **Analyzing photo…** text;
- keep Title, Category, image input and Save listing enabled;
- do not move keyboard focus;
- expose the text through a polite live region; and
- hide the spinner from assistive technology when the text already communicates
  the state.

On success, announce which fields were filled. On disabled service, timeout,
rate limit, invalid image, malformed provider output or network failure, show a
short message such as **AI suggestions are unavailable. Enter the title and
category yourself.** The ordinary form remains fully usable.

The status must not expose technical provider/model errors. Repeated status
changes should not create an alert loop. Visible field labels and select
semantics remain unchanged.

At 320 CSS pixels, long messages and suggestion markers wrap without horizontal
overflow or covering the mobile bottom navigation. Loading animation, if any,
must honor `prefers-reduced-motion: reduce`.

## 12. Privacy and transparency

Automatic analysis changes MM-022's earlier rule that preview activity makes no
request. MM-023 narrowly supersedes that rule only when the seller leaves the
visible AI control enabled.

Before selection, the Sell page states one of:

- **Local analysis:** the resized image remains on the Market Mirror computer;
  or
- **External analysis:** a resized, metadata-free copy is sent to the configured
  AI provider to generate suggestions.

For an external provider:

- only the normalized image and fixed task instruction are transmitted;
- username, email, seller ID, filename, local path, description, price, messages
  and account data are excluded;
- Market Mirror does not persist the analysis copy or provider response;
- application logs record only outcome class, duration and request ID, never
  image bytes, base64, data URLs, prompts containing user data or raw provider
  output; and
- project documentation must identify the provider and link its applicable data
  handling policy before a real key is enabled.

Disabling the AI control prevents the analysis request entirely. JavaScript
disabled, provider disabled and missing-credential states all fall back to the
normal MM-022 upload and manual fields.

## 13. Security requirements

- Require an authenticated user and valid CSRF token.
- Apply the separate per-user rate limit before provider invocation.
- Enforce Flask's request-size limit plus the explicit 5 MiB image read limit.
- Revalidate decoded format, frames, pixels and content server-side.
- Never accept a remote image URL or make a server-side request to a user URL;
  this avoids server-side request forgery.
- Keep provider credentials server-side and redact authorization headers/errors.
- Use a bounded provider connect/read timeout.
- Do not automatically retry or follow model-supplied URLs.
- Treat image text and provider output as untrusted data.
- Validate against the internal category allow-list and strict title limits.
- Use `textContent`/form value assignment, never model-produced HTML.
- Give the model no tools or authority to save, publish, message, purchase or
  modify data.
- Do not weaken the authoritative validation performed again when Save listing
  is eventually selected.

## 14. Failure and concurrency behavior

The feature must remain safe when:

- the provider is disabled or credentials are missing;
- DNS/network/provider service fails;
- the provider times out or returns a non-JSON/error response;
- the rate limit is reached;
- the seller replaces the image repeatedly or disables AI mid-request;
- an old response arrives after a new image or after manual field edits;
- the image is valid for browser preview but invalid to Pillow;
- a model returns an unknown category, excessive title, markup, NaN confidence,
  extra prose or an instruction instead of a product name;
- the seller clicks Save while analysis is running; or
- two tabs analyze photos for the same account.

In all cases, no unintended listing/database/file write occurs, seller-entered
values remain intact, and the manual form remains usable. Saving while analysis
is running submits the seller-visible values at that moment and cancels/ignores
the late analysis response.

## 15. Acceptance criteria

| ID | Expected outcome |
| --- | --- |
| AC-023-01 | Sell a product shows an understandable AI control, provider-location disclosure, status area and normal MM-022 upload fallback. |
| AC-023-02 | With AI enabled, selecting/dropping one decoded MM-022 image starts exactly one authenticated, CSRF-protected temporary analysis request without submitting the listing. |
| AC-023-03 | The server revalidates and metadata-strips the image, sends only a bounded normalized copy to the configured provider, and writes no image, row, draft or event. |
| AC-023-04 | A valid high-confidence result fills untouched Title and Category fields and visibly marks them as suggestions requiring review. |
| AC-023-05 | Any field edited by the seller before a result arrives is never overwritten; a partial result may fill only the other untouched field. |
| AC-023-06 | Image replacement, AI disable, page leave and Save supersede/cancel the current request; stale responses cannot change the form. |
| AC-023-07 | Invalid images, unknown categories, malformed output, low confidence, timeouts, provider failures and rate limits leave a usable manual form with safe feedback. |
| AC-023-08 | Disabling AI before selection produces no vision request; JavaScript/provider-disabled states preserve the ordinary image input and manual listing workflow. |
| AC-023-09 | The provider receives no username, email, filename, local path, listing text, price, messages or database access, and secrets/raw provider data never reach logs or responses. |
| AC-023-10 | Model/image prompt injection cannot supply prompts, tools, HTML or arbitrary categories; all outputs pass strict server validation and safe DOM assignment. |
| AC-023-11 | Existing text category and price suggestion endpoints remain image-free and unchanged in behavior. |
| AC-023-12 | Keyboard, screen-reader status, reduced-motion, desktop and 320px behavior remain usable without focus theft or horizontal overflow. |
| AC-023-13 | Existing listing image normalization/storage remains authoritative at Save; request-token and rollback/orphan-cleanup behavior remain intact. |
| AC-023-14 | The application starts and all non-vision features work without a provider key, internet connection or vision configuration. |

## 16. Edge cases required in the later plan and tests

The Planning and Testing stages must cover at least:

- picker and drop paths using the same analysis trigger;
- AI enabled versus disabled before selection and disabled mid-request;
- valid landscape, portrait, transparent PNG and EXIF-rotated images;
- empty, corrupt, spoofed, animated, over-byte and over-pixel images;
- exact 5 MiB and pixel boundaries;
- successful full and partial suggestions;
- confidence exactly below, at and above 0.65;
- blank, short, long, control-character, HTML-like and Unicode titles;
- every allowed category and unknown/case-changed categories;
- invalid JSON, extra prose/keys, missing values, booleans, NaN/infinite scores;
- provider timeout, connection failure, HTTP error and disabled configuration;
- rate-limit boundary and separation from existing text-AI limits;
- replacing photos rapidly and old response arriving last;
- typing/pasting title and changing category before/during/after analysis;
- AI-filled value edited by the seller, then image replaced/removed;
- Save while request is pending and response after navigation;
- CSRF missing/invalid, anonymous request and oversized multipart body;
- no database/upload/log leakage for preview-only analysis;
- fake-provider request payload contains only clean image plus fixed instruction;
- provider secret and raw errors are redacted;
- no real provider call in pytest;
- JavaScript disabled, missing `fetch`/`AbortController`, and provider unavailable;
- repeated same-file selection and multi-tab rate limiting;
- mobile 320px, short landscape, keyboard-only, live-region and reduced-motion;
- no initialization or network activity on Edit listing and unrelated pages; and
- the complete MM-001–MM-022 regression suite.

## 17. Out of scope

MM-023 does not add:

- AI-generated descriptions, prices or condition judgments;
- automatic listing submission or publication;
- face recognition, identity, age, emotion, medical or demographic inference;
- OCR as a general text-extraction feature;
- counterfeit, safety, legal or authenticity verification;
- image moderation claims;
- multiple-image reasoning;
- image embeddings, permanent AI caches or training-data collection;
- background removal, cropping, enhancement or generated images;
- remote image URLs;
- analysis on Edit listing;
- a provider billing dashboard; or
- public deployment.

## 18. Beginner explanation

A vision model is a program that can examine picture pixels and return a text
guess. Market Mirror will ask a narrow question: **What main product is shown,
and which one of our categories fits it?**

The answer is only a suggestion. A laptop photo might produce **Silver laptop
computer** and **Electronics**, but the model can be wrong. That is why the
seller can edit everything and why the AI is not allowed to save the listing.

The browser's thumbnail and the AI request are different:

- the thumbnail is a temporary local browser view; and
- AI analysis sends a cleaned, smaller copy to the configured model only when
  the visible AI option is enabled.

The server removes metadata and checks the image before AI use. It also checks
the AI's answer before placing it into the form. We therefore validate both
directions: untrusted image input going in and uncertain model output coming out.

## 19. Subsequent SDD stages

After explicit MM-023 approval:

1. Draft PLAN-023 with the selected provider, configuration, exact modules,
   endpoint, reusable image-normalization design, JavaScript state machine,
   privacy text, fake provider, tests, browser fixtures and rollback steps.
2. Wait for explicit PLAN-023 approval.
3. Write pytest/static contracts and a browser checklist before implementation.
4. Run and record the expected Red result.
5. Implement only the approved behavior.
6. Run focused, security, listing/image/AI regression and complete test suites.
7. Use an isolated fake provider for browser verification; make no paid provider
   request unless the user separately configures and authorizes real credentials.
8. Record Green evidence and a high-school-level learning guide.

No plan, test, provider package, API call, HTML, CSS, JavaScript, route or
application implementation is authorized by this specification alone.

## 20. Approval gate

Please review these main decisions:

1. AI analysis is automatic only while the visible AI control is enabled;
2. an external provider receives only a resized, metadata-free product image
   and a fixed instruction, with the transmission disclosed before selection;
3. untouched Title and Category fields may be pre-filled, but seller edits are
   never overwritten;
4. uncertain/malformed results abstain, and AI failure never blocks the manual
   listing form;
5. the endpoint is authenticated, CSRF-protected, rate-limited and memory-only;
6. the first concrete provider is selected in PLAN-023 from official
   documentation, while pytest/browser fixtures use a fake provider; and
7. Save listing remains the only action that stores or publishes anything.

The user explicitly approved **MM-023** on 2026-11-02. PLAN-023 may now be
drafted, but tests and implementation still require separate PLAN-023 approval.
