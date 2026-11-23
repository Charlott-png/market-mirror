# MM-018 Green verification — 2026-11-02

MM-018 and PLAN-018 were approved before the test-first implementation. The 28 focused tests were written and their expected Red failures were recorded before application code changed.

## Automated results

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_seller_profile.py -q --basetemp=.pytest-tmp\mm018-green
# 28 passed in 34.31s
```

The first complete-suite run in the restricted command environment reached `262 passed, 1 error`. The one error occurred while Windows Application Control blocked SciPy's `pyduccfft` DLL during `test_additional_demo_items.py` setup. It was an environment/import error, not an assertion failure and not in MM-018 code. The identical suite was then rerun in the normal local environment; its final result is recorded below.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp\mm018-regression-unrestricted
# 263 passed in 334.24s (0:05:34)
```

The successful rerun confirms that all earlier Market Mirror features and all 28 new MM-018 tests pass together.

## Browser acceptance results

Testing used a loopback-only fixture application with an in-memory database and separate temporary uploads. The fixture server was stopped after testing. The real demo database was used only for read-only navigation and visual confirmation.

| Check | Result |
| --- | --- |
| Three vs. four active listings | PASS — three showed no badge; four showed one badge and the visible activity-only explanation. |
| Full UTC join date | PASS — fixture displayed `29 February 2024` and `<time datetime="2024-02-29">`. |
| Empty seller | PASS — HTTP 200 profile, zero count, no badge and a specific no-active-listings message. |
| Twenty-one-item pagination | PASS — page 1 had 20 cards and page 2 had 1; both used total 21 and retained the badge. |
| No-JavaScript rendering | PASS — the controlled fixture removed all script tags and the complete empty-seller profile remained usable. This was a fixture simulation, not a browser preference change. |
| Narrow layout | PASS — at a real 320 CSS-pixel viewport, the long username, badge and long biography wrapped with no horizontal overflow (`scrollWidth 305`, `innerWidth 320`). |
| Keyboard focus | PASS — Tab focused the first link with a visible solid outline approximately 2.67 pixels wide. |
| Product → seller | PASS — the real Silver laptop page linked to `/sellers/demo-alex`; activating it opened the correct profile with six active cards. |
| Profile → product and MM-017 lightbox | PASS — a profile card opened Silver laptop; its lightbox opened, locked the page, focused Close, then closed, unlocked the page and restored trigger focus. |
| Browser console | PASS — no warning or error entries after the navigation/lightbox smoke check. |
| Desktop evidence | PASS — `docs/evidence/018-seller-profile.png`. |
| Narrow evidence | PASS — `docs/evidence/018-seller-profile-narrow.png`. |

## Explicit limitations

The available browser controls did not expose an actual 200% browser-zoom setting or a dark-mode media-preference emulator, so those two optional environment checks were not claimed as passed. The 320-pixel viewport is a real responsive-width check and is not described as a zoom substitute. Server-side tests still cover the feature's content, privacy and state rules independently of visual appearance.

## Data safety

No real seller, product, status, join date or uploaded image was changed for MM-018 verification. Profile GET requests were also covered by a database before/after snapshot test. No migration or new package was required.
