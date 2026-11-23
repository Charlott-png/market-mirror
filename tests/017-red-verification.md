# MM-017 Red checkpoint — 2026-10-29

PLAN-017 was approved before tests were written. Application HTML/CSS/JS remained unchanged during these runs.

Commands (from project root):

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest tests\test_product_image_interactions.py -q --basetemp=.pytest-tmp\mm017-red
```

Collection: 8 tests collected in 1.53s.

Execution: **5 failed, 3 passed in 54.21s**. All five failures reached successful HTTP 200 detail/preview responses, then found zero `product-image-trigger` links where exactly one was required. These are expected missing-feature failures, not setup/import errors.

Failures: active image, sold image, owner archived preview, escaped title, preservation/forms case. Passes: absent filename placeholder, missing-file placeholder, unchanged catalogue cards. Full browser acceptance scenarios were defined in `017-browser-checklist.md` before implementation. HTML assertions do not establish JavaScript/CSS runtime correctness.
