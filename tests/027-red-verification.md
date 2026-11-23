# MM-027 Red verification

Date: 2026-11-07 (Asia/Shanghai)

Status: VALID RED CHECKPOINT — captured before application implementation

## Collection

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_shop_assistant.py tests\test_gemini_shop.py --collect-only -q --basetemp=.pytest-tmp\mm027-collect
```

Result: **76 tests collected** successfully.

## Red run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_shop_assistant.py tests\test_gemini_shop.py -q --basetemp=.pytest-tmp\mm027-red-final
```

Result: **76 failed in 15.28 seconds**.

Representative intentional failures:

- assistant configuration keys did not exist;
- `app.ai.shop_assistant` did not exist;
- `app.ai.shop_catalogue` did not exist;
- `app.ai.gemini_shop` did not exist;
- `/ai/shop-assistant` did not exist;
- the base page had no assistant launcher/panel;
- `_shop_assistant.html` did not exist;
- `shop-assistant.js` did not exist; and
- assistant-specific CSS contracts did not exist.

The first Red run also exposed one test-only ambiguity: the Explore page
already had several ordinary `/products` links. Before implementation, the
test was corrected to identify the future assistant fallback by
`id="shop-assistant-explore"`. Collection remained 76 and the final Red run
still failed every contract for missing MM-027 behavior.

This proves the new contracts do not accidentally pass against MM-026. Under
the approved SDD sequence, implementation may now begin.
