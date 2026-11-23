# MM-028 Green Verification

Date: 2026-11-07 (Asia/Shanghai)

## SDD sequence

1. MM-028 was approved.
2. PLAN-028 was approved.
3. The new tests were run before implementation: 20 collected, 19 failed and
   1 passed. The failures matched the missing table, helper and page sections.
4. The implementation was added only after that Red result was recorded in
   `tests/028-red-verification.md`.
5. The same tests and wider regression suites then passed.

## Automated results

| Check | Result |
| --- | --- |
| Focused MM-028 tests | 20 passed in 26.09 seconds |
| Related marketplace/AI/UI regression set | 201 passed in 185.63 seconds |
| Complete pytest suite | 560 passed in 548.58 seconds |
| Python byte-code compilation | Passed |
| Installed-package consistency (`pip check`) | No broken requirements found |

A final confirmation run after the documentation updates also passed all 20
focused tests in 37.32 seconds using a project-local temporary directory.

The focused set covers authentication, CSRF, active-status rules, repeat
views, five-row pruning, user isolation, status changes, consent independence,
analytics failure, Explore and Dashboard rendering, AJAX boundaries, related
product constraints, query bounds, concurrency and migration round-trips.

## Development database migration

Before upgrading, the SQLite database was copied to:

`instance/backups/before-demo-images-20261107T130501Z-6d5e8b5505784fd48765d9e8008b71e1.sqlite`

Revision `c28d0de02801` was applied. Product, user, order, image, message,
conversation, cart and saved-product counts were identical before and after.
The new history table started with zero rows and SQLite reported
`integrity_check=ok`. No fake browsing history was inserted into the real
database.

## Browser result

An isolated temporary database and generated fixture image were used. The
following passed in the in-app browser:

- anonymous Explore omitted private history;
- the signed-in empty state appeared;
- three viewed products appeared newest first;
- opening a product again moved it to the front without a duplicate;
- opening a sixth distinct product pruned the oldest;
- related cards were active, same-category, distinct, excluded the current
  item and were limited to three;
- a category with no alternative omitted the section;
- related cards still rendered with the view-recording script removed, while
  history correctly did not change;
- AJAX search updated only its results and left Recently Viewed visible;
- Dashboard kept Recently Viewed separate from Discover more; and
- the browser console reported no JavaScript errors.

The temporary server was stopped. Viewport resizing was unavailable in this
browser session, so 320/360-pixel visual rehearsal remains a manual check;
existing mobile CSS/navigation tests stayed Green.

## Honest limits

Passing tests reduce known risk but do not prove that every browser, database
engine or simultaneous real-world request will behave identically. This local
course project was executed with SQLite. PostgreSQL and a real screen reader
were not part of this verification.
