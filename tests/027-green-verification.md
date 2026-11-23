# MM-027 Green verification

Date: 2026-11-07 (Asia/Shanghai)

Status: IMPLEMENTED AND VERIFIED LOCALLY

## SDD sequence

- MM-027 specification approved.
- PLAN-027 approved.
- 76 contracts collected before implementation.
- Final pre-implementation run: **76 failed in 15.28 seconds**.
- Red details: `tests/027-red-verification.md`.
- Implementation began only after that checkpoint.

## Focused Green

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_shop_assistant.py tests\test_gemini_shop.py -q --basetemp=.pytest-tmp\mm027-green-1
```

Result: **76 passed in 26.55 seconds**.

## Related regressions

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ai.py tests\test_ai_vision.py tests\test_gemini_vision.py tests\test_live_search.py tests\test_mobile_navigation.py tests\test_cart.py tests\test_checkout.py -q --basetemp=.pytest-tmp\mm027-regression
```

Result: **170 passed in 103.25 seconds**.

## Complete suite and dependencies

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm027-full
.\.venv\Scripts\python.exe -m pip check
```

Results:

- **536 passed in 539.92 seconds**;
- **No broken requirements found**.

After the browser-discovered launcher-label improvement and final Explore link,
the focused suite passed again (**76 passed in 27.50 seconds**) and the complete
exact-final-file suite passed again: **536 passed in 429.79 seconds**.

`scripts/local.ps1 check` then reported **No new upgrade operations detected**.
The finished Waitress server started successfully on `127.0.0.1:5000`.

## Isolated browser evidence

`tests.preview_shop_assistant` created a new temporary SQLite database under
`.pytest-tmp`, fictional users/products and a deterministic fake generator on
loopback port 5027. It never read the real database or contacted Google.

Observed in the in-app browser:

- anonymous Home contained one labelled launcher;
- opening showed the greeting, privacy/AI disclosure and Sign in fallback;
- login returned to Home and opening focused the labelled question field;
- “Find me a cheap camera” produced Budget student camera ($39.90, Good) and
  Mirrorless travel camera ($149.00, Like New);
- selecting the first recommendation opened `/products/1`, whose database
  title, price, status, description and seller matched;
- fixture state recorded exactly one fake call with candidate IDs `[1,2,3]`,
  proving sold/archived IDs 4 and 5 were excluded;
- Escape closed the panel and returned focus to the launcher; and
- an initial accessibility observation improved the launcher name from a noun
  to the action **Open AI Shop Assistant**.

The available browser surface did not expose viewport resizing, 200% zoom,
dark-mode or a real screen reader. Those remain explicit student/manual items
in `tests/027-browser-checklist.md`; static responsive/reduced-motion contracts
passed. No such checks are falsely claimed.

## Data/provider boundary

- No automated or browser test used a real Gemini key or API quota.
- No schema migration was needed.
- The isolated fixture was stopped after verification.
- No real product, account, cart, message, order or assistant transcript was
  changed.
- Real-key smoke testing remains optional and is explained in
  `docs/027-ai-shop-assistant-guide.md`.
