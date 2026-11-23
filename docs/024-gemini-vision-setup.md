# MM-024 — Set up real Gemini image suggestions

## What this feature does

On **Sell a product**, Market Mirror can send a cleaned copy of the selected
product photo to Google Gemini. Gemini guesses a short Title and one Market
Mirror Category. You can change or delete both guesses before saving.

The model never saves the listing for you. If Gemini is unavailable, the normal
form still works.

## Why this provider

Market Mirror uses Google's stable `gemini-3.5-flash-lite` model by default. It
can read images, return structured JSON and currently has free-tier access.
Google controls eligibility, limits and pricing, so check the current AI Studio
dashboard before a demonstration.

Important privacy point: Google's current pricing documentation says free-tier
submitted content may be used to improve Google products. Use ordinary product
photos, not personal, private or sensitive images.

Official pages:

- Create/manage a key: <https://aistudio.google.com/apikey>
- Model information: <https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite>
- Current pricing: <https://ai.google.dev/gemini-api/docs/pricing>
- API key safety: <https://ai.google.dev/gemini-api/docs/api-key>

## Step 1 — Create your free-tier API key

1. Open <https://aistudio.google.com/apikey>.
2. Sign in to the Google account you want to use for this class project.
3. Accept Google's terms if you agree with them.
4. Select **Create API key** and choose/create a project if asked.
5. Copy the key privately.

Do not paste the key into this chat, a report, a screenshot, Python, JavaScript
or Git. An API key works like a password for the project and its quota.

MM-024 does not require you to enable billing. If Google asks you to upgrade,
stop and continue using Market Mirror's manual form unless you personally decide
otherwise.

## Step 2 — Create the private `.env` file

Open PowerShell and paste:

```powershell
Set-Location 'C:\Users\Amaal\OneDrive\Desktop\Ai folder\market-mirror'
Copy-Item -LiteralPath '.env.example' -Destination '.env' -ErrorAction Stop
notepad '.env'
```

If `.env` already exists, PowerShell stops instead of overwriting your private
settings. In that case, run only:

```powershell
notepad 'C:\Users\Amaal\OneDrive\Desktop\Ai folder\market-mirror\.env'
```

In Notepad, find the vision section and make it exactly like this, replacing
only the last placeholder with your real key:

```dotenv
VISION_AI_ENABLED=true
VISION_AI_PROVIDER=gemini
VISION_AI_MODEL=gemini-3.5-flash-lite
VISION_AI_TIMEOUT_SECONDS=12
GEMINI_API_KEY=PASTE_YOUR_REAL_KEY_HERE
```

Save and close Notepad. `.gitignore` excludes `.env`, but this folder is inside
OneDrive. Git ignore does not stop OneDrive synchronization, so review who can
access the synchronized folder.

## Step 3 — Restart Market Mirror

Close the old server window, then double-click:

```text
Start-Market-Mirror.bat
```

Environment files are read when the server starts. Editing `.env` while the
server is already running will not update that running process.

## Step 4 — Try a safe product photo

1. Sign in.
2. Open **Sell**.
3. Confirm **Let AI suggest the title and category** is enabled and checked.
4. Read the Google Gemini privacy disclosure.
5. Select a non-personal product image, such as a laptop, bicycle or book.
6. Wait for the preview and suggestion.
7. Review and edit Title and Category.
8. Complete Description, Price and Condition yourself.
9. Select **Save listing** only if you really want to create the listing.

The local preview appears before the cloud request. Market Mirror sends Gemini
a new JPEG that is at most 1024 pixels on its longest side. The new JPEG has no
original filename or EXIF metadata. Market Mirror does not send your username,
email, description, price or other listings.

## How the code works

### `.env` and environment variables

`.env` is a private settings file. `python-dotenv` reads it when Market Mirror
starts. `override=False` means a real Windows or hosting environment setting
wins if both places define the same name.

The key is never copied into Flask's configuration object. The Gemini adapter
reads it directly from the process environment just before creating Google's
SDK client.

### SDK

An SDK is a provider-made Python package that handles web requests and
authentication. Market Mirror uses Google's official `google-genai` SDK.

The adapter makes one request and disables automatic retry. This prevents one
photo selection from quietly producing several quota-consuming attempts.

### Structured output

Market Mirror supplies a JSON schema—like a form the model must fill in. It asks
for a title, one of seven category codes, two confidence estimates and an
optional uncertainty explanation.

The server still checks every value. AI output is treated as untrusted input,
just like text submitted by an unknown visitor.

### Why edited fields are protected

JavaScript records whether you touched Title or Category. A late model response
cannot replace a field you edited. It also gives each photo selection a sequence
number so an older request cannot win after you select a newer photo.

## Troubleshooting

### The checkbox says unavailable

Check all five `.env` lines, save the file and restart the server. Common causes:

- `VISION_AI_ENABLED` is still `false`;
- the provider is not exactly `gemini`;
- the model is misspelled;
- the key placeholder was not replaced; or
- the server was not restarted.

Do not print or send the key while troubleshooting.

### “AI image suggestions are unavailable” after selecting a photo

The manual form is still safe to use. Possible causes include:

- no Internet connection;
- invalid/revoked key;
- Google account/project permission problem;
- free-tier quota exhausted;
- Gemini unavailable in the current region; or
- a temporary Google service failure.

Open <https://aistudio.google.com/apikey> to check the key/project and use the AI
Studio usage dashboard to check current quota. Market Mirror intentionally
returns one generic message so provider responses cannot leak secrets.

### The suggestion is wrong

AI vision makes guesses, not facts. Edit the fields before saving. Ambiguous
photos, several objects, small objects or unusual angles are harder. A plain
photo with one main product usually gives a clearer result.

### Stop all cloud analysis immediately

Change this line in `.env`:

```dotenv
VISION_AI_ENABLED=false
```

Restart the server. The manual Sell form continues to work.

## A classroom explanation

“The browser uploads the photo to my Flask endpoint, not directly to Google.
Flask checks and rebuilds it as a smaller metadata-free JPEG. A provider adapter
sends only that JPEG and a fixed instruction to Gemini. Gemini returns structured
JSON, which my own validator checks again. JavaScript fills only fields the
seller has not edited. The secret key stays on the server.”
