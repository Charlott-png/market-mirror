# MM-020 browser acceptance checklist

Status: DEFINED BEFORE IMPLEMENTATION

Date: 2026-11-02 (Asia/Shanghai)

Use a loopback-only Market Mirror app with a temporary SQLite database and
temporary uploads. Do not mutate the real local database during acceptance.

## Fixture requirements

- Seed more than 20 public products so pagination can appear.
- Seed active, sold and archived canary products.
- Seed products for anonymous, buyer and owner card-control checks.
- Provide one test-only slow-query marker so loading and races are observable.
- Provide test-only failed and malformed response markers.
- Keep every delay/failure hook in `tests/preview_live_search.py`; production code
  must never know those markers.

## Required checks

| ID | Browser action | Expected evidence |
| --- | --- | --- |
| B-020-01 | Open Explore and wait without typing. | Initial cards are server-rendered; no automatic `/products/search` request occurs. |
| B-020-02 | Type a query, pause for less than 300 ms, then finish it. | No premature replacement; one result update follows the final 300 ms pause. |
| B-020-03 | Type the controlled slow query. | Old cards stay visible; small spinner and `Searching…` appear; results have `aria-busy=true`. |
| B-020-04 | Let the slow query finish. | Count, grid and pagination update together; spinner hides; busy becomes false; concise result status appears. |
| B-020-05 | Compare navigation state before/after a live update. | No document reload/new navigation entry; header and Search focus/caret remain stable. |
| B-020-06 | Submit category and price/sort normally, then type Search. | The live request keeps every selected valid filter and resets old page to page 1. |
| B-020-07 | Start the slow query, then quickly type a fast different query. | Fast/new result wins; delayed old response never replaces it or clears its state. |
| B-020-08 | Trigger controlled failure and malformed payload, then type a valid query. | Last good cards/URL remain; fallback status appears; later query recovers normally. |
| B-020-09 | Search for a missing phrase. | `0 products`, empty-state panel and no pagination; no stale old cards. |
| B-020-10 | Inspect address bar and use Back once. | URL is canonical `/products?...`, never `/products/search`; typing did not add one history step per letter. |
| B-020-11 | Inspect cards anonymously, as buyer and as owner. | Sign-in link, CSRF Add form and Your listing state respectively; images/seller links remain correct. |
| B-020-12 | Use keyboard for Search, Find products, Clear, cards and pagination. | Logical order and visible focus; live replacement never steals focus. |
| B-020-13 | Use Enter/Find products and a controlled no-script response. | Ordinary full-page GET search remains complete and usable. |
| B-020-14 | Set viewport to 320 CSS pixels and use long query/title/count text. | No horizontal page overflow; spinner/status/grid/pagination wrap cleanly. |
| B-020-15 | Test reduced motion, 200% zoom and real IME composition when controls permit. | Spinner stops rotating under reduced motion; zoom and composition remain usable. Report unavailable controls honestly. |
| B-020-16 | Open product lightbox, seller page and cart controls after live replacement. | MM-017–MM-019 interactions still work. |
| B-020-17 | Inspect console warnings/errors. | No application warning/error from successful, stale, aborted, failed or recovered searches. |

## Cleanup

- Save desktop and 320-pixel evidence under `docs/evidence/020-*`.
- Reset any temporary viewport/media overrides.
- Stop the disposable fixture server.
- Reload the real local Explore page only for a read-only startup smoke check.

