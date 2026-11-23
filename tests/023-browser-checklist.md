# MM-023 browser acceptance checklist

Use only `tests.preview_ai_vision` with its temporary database, generated images
and deterministic fake provider. Never use a real API key, paid request, user's
photo or real Market Mirror listing for stateful/failure scenarios.

| # | Browser action | Expected result |
| --- | --- | --- |
| 1 | Open Sell with fake vision enabled. | Checked AI option, external-provider disclosure, hidden spinner/markers and ordinary MM-022 picker are visible; zero provider calls. |
| 2 | Pick or fixture-drop a valid laptop image. | Local preview appears first, one analysis starts, spinner/text appear, no listing submit occurs. |
| 3 | Return full high-confidence result. | Untouched Title becomes the fake title, Category changes to Electronics, both markers show, status asks for review, call count is one. |
| 4 | Type Title while a delayed response is pending. | Typed title remains; untouched Category may be filled; focus stays where the user placed it. |
| 5 | Change Category while delayed response is pending. | Chosen category remains; untouched Title may be filled. |
| 6 | Edit an AI-filled field, then replace the photo. | Seller edit loses the AI marker and is never erased; untouched AI field may reset/re-analyze. |
| 7 | Select photo A then B; release B response before A. | Only B result appears; late A result causes no visible change. |
| 8 | Uncheck AI before selection. | Preview still works; call count stays zero; manual fields and Save work. |
| 9 | Uncheck during a slow request, then resolve it. | Loading stops and result is ignored. Rechecking analyzes the current valid file once. |
| 10 | Exercise partial, below-threshold and abstention responses. | Only accepted untouched fields fill; otherwise manual form remains and status is clear. |
| 11 | Exercise malformed, timeout, provider error, 429 and disabled responses. | Spinner stops, no fields are corrupted, generic manual fallback appears, no secret/raw message is visible. |
| 12 | Choose empty, text, corrupt, multiple and over-limit files. | MM-022 errors appear and provider call count does not increase. |
| 13 | Click Save while fake provider is delayed. | Navigation/submission proceeds immediately with visible field values; late response cannot alter the new page. |
| 14 | Use Suggest category and Suggest price after selecting an image. | Existing text AI remains usable; fixture confirms its requests contain no image bytes. |
| 15 | Resize to 320px portrait and short landscape. | Disclosure, status and markers wrap; no horizontal overflow; Save/mobile nav remain usable. |
| 16 | Keyboard through AI control, picker, Title, Category and Save. | Native focus is visible/logical; analysis does not move focus; status uses polite live region. |
| 17 | Enable reduced-motion fixture and no-script fixture. | Spinner has no required rotation under reduced motion; no-script keeps ordinary manual upload/form. |
| 18 | Visit Edit listing, Profile, Explore and a product page. | No vision UI/request; no new console errors or regressions. |
| 19 | Inspect sanitized fixture instrumentation. | Provider receives one metadata-free <=1024 JPEG and fixed task only; no filename/account/form values. |
| 20 | Stop fixture and open real local Sell page with provider disabled. | Manual MM-022 flow remains available; no real network/provider request occurs. |

