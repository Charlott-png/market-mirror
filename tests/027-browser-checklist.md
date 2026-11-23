# MM-027 isolated browser checklist

Status: TEST CONTRACT — written before implementation

Use only `tests.preview_shop_assistant` with its temporary database, fictional
credentials and fake Gemini generator. Do not spend a real API quota or modify
`instance/market-mirror.sqlite`.

| Step | Action | Expected result |
| --- | --- | --- |
| 1 | Open Home anonymously. | One bottom-right launcher appears; opening shows the greeting, disclosure and Sign in link; fake provider call count remains zero. |
| 2 | Sign in as the fictional shopper and reopen the widget. | Focus moves to the labelled question field; Escape closes and returns focus to the launcher. |
| 3 | Ask “Find me a cheap camera”. | A visible/busy loading state appears, one fake call occurs, and safe cards link to current active camera pages. |
| 4 | Inspect cards. | Current title, price, condition and optional cover come from Market Mirror; model reason is text; no model URL/HTML is used. |
| 5 | Ask a follow-up. | At most three complete exchanges are sent; transcript remains ordered and page does not reload. |
| 6 | Use Clear chat. | Pending request aborts, transcript resets to greeting and browser-memory history becomes empty. |
| 7 | Double-click Send during fake delay. | Only one request/provider call is active; stale response cannot overwrite a newer state. |
| 8 | Trigger no-match, malformed-output, provider-error and rate-limit modes. | Each shows a useful Explore fallback; no raw error, prompt, key or stack trace appears. |
| 9 | Use malicious query/product/model text fixtures. | Text is displayed literally/escaped; no script, foreign URL or forged product ID becomes interactive. |
| 10 | Mark a suggested product sold during fake response. | The returned UI omits it after server recheck and explains that no recommendation remains. |
| 11 | Test at 320px and 360px. | Launcher/panel sit above mobile navigation, controls remain reachable, and no horizontal overflow appears. |
| 12 | Navigate by keyboard and, if supported, inspect 200% zoom/dark/reduced motion. | Focus is visible, announcements are polite, controls remain readable and nonessential animation stops. |
| 13 | Disable JavaScript. | Widget enhancement is hidden; Home/Explore/product browsing still works normally. |
| 14 | Inspect unrelated pages and temporary DB/counters. | One widget per page, no console errors, no business writes, and only expected fake-call/rate records change. |

Record unavailable screen-reader, zoom or browser-emulation checks honestly;
static/pytest contracts do not replace a full human accessibility audit.
