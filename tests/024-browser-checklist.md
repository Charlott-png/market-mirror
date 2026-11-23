# MM-024 browser acceptance checklist

Automated browser checks use the existing isolated `tests.preview_ai_vision`
fixture with a deterministic fake provider. They never read `.env`, use a real
key, call Google/OpenAI or touch the real catalogue.

| # | Browser action | Expected result |
| --- | --- | --- |
| 1 | Open the fake-Gemini Sell page. | Checked, enabled AI option; Google Gemini disclosure; manual fields and Save remain visible. |
| 2 | Select the generated laptop fixture. | Local thumbnail appears first; one analysis request starts; no listing submission occurs. |
| 3 | Receive the high-confidence fake response. | Title and Electronics fill only if untouched; both AI markers appear; status asks for review. |
| 4 | Type Title while a response is delayed. | Typed value remains; untouched Category may fill; focus does not move. |
| 5 | Change Category while delayed. | Chosen category remains; untouched Title may fill. |
| 6 | Select photo A then B and finish A last. | Only B may update fields. |
| 7 | Uncheck before/mid request. | No new call or late application; manual form remains complete. |
| 8 | Exercise provider error, malformed result and 429 fixture. | Generic fallback appears; spinner stops; no secret/raw error appears. |
| 9 | Resize to 320px and enable reduced motion. | Disclosure and markers wrap; no horizontal overflow; textual loading remains. |
| 10 | Visit Edit, Explore and Profile. | No vision controls or provider request. |
| 11 | Start the real local app without `.env`/key. | Checkbox disabled; manual upload/listing flow works. |

## Optional student-owned real check

Only after implementation and after the student privately creates `.env`:

1. restart with `Start-Market-Mirror.bat`;
2. sign in and open Sell a product;
3. confirm the disclosure says the cleaned copy goes to Google Gemini and that
   free-tier submitted content may be used to improve Google products;
4. use a generated, non-personal product photo;
5. confirm a real title/category suggestion appears and remains editable;
6. do not select Save Listing unless intentionally creating the listing; and
7. never reveal, paste, screenshot or log the key.

Quota, authentication, unsupported-region or network failure must leave the
manual form usable. This optional check does not enable billing.
