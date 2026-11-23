# MM-029 Green Verification

Date: 2026-11-07 (Asia/Shanghai)

## SDD sequence

1. MM-029 was approved.
2. PLAN-029 was approved.
3. Twenty-nine focused tests collected against the unchanged application.
4. The validated Red run produced 28 intended failures and 1 existing passing
   redirect contract, with no fixture errors or warnings.
5. Implementation began only after that Red result was recorded.

## Automated results

| Check | Result |
| --- | --- |
| Focused MM-029 server/client contracts | 29 passed in 38.47 seconds |
| Related messaging/security/mobile/assistant/recent-viewed set | 197 passed; one print-block ordering regression found and corrected |
| Corrected print regression plus MM-029 asset tests | 6 passed in 1.85 seconds |
| Exact transient demo-image subprocess retry | 1 passed in 19.42 seconds |
| Final complete pytest rerun | **589 passed in 1101.17 seconds** |
| Python compilation | Passed |
| Installed-package consistency | `pip check`: no broken requirements |
| Migration drift check | Passed; no MM-029 migration exists |

A final focused confirmation after the stylesheet cache-version update also
passed all 29 tests in 38.10 seconds.

The first complete run had 588 passes and one unrelated demo-image subprocess
test that returned code 1 without stderr. The exact test passed on immediate
retry. A second complete run was executed rather than hiding that event, and
all 589 tests passed.

## Browser result

The isolated fixture used fictional buyer/seller accounts, 55 messages and a
temporary SQLite database. The in-app browser verified:

- newest 50 messages on the default page and five on Older messages;
- computed outgoing style `flex-end`, blue `rgb(11, 101, 194)`, white text;
- computed incoming style `flex-start`, grey `rgb(232, 237, 241)`, dark text;
- browser-local compact timestamps and complete semantic time labels;
- literal `<script>` message text with zero script elements in the transcript;
- initial scroll position at the newest content;
- a fixture incoming message appeared after the next three-second poll;
- the message count moved from 50 to 51 without full-page navigation;
- repeated polling kept one copy and a stable count of 51;
- no-JavaScript mode retained 50 bubbles, 50 UTC fallbacks and the normal
  composer while loading no conversation script; and
- the browser console contained no JavaScript errors.

The temporary server was stopped. Viewport resizing was unavailable, so
320/360-pixel and 200%-zoom visual rehearsal remains manual; mobile CSS and
navigation contracts stayed Green.

## Development data

MM-029 required no migration and automated/browser tests used temporary
databases. The real database remains at revision `c28d0de02801`, contains the
same two message rows recorded before this feature, and reports
`PRAGMA integrity_check=ok`.

## Honest limits

Three-second polling is suitable for this local university demonstration, not
a large public chat service. No real screen reader, live multi-device network,
WebSocket transport, PostgreSQL concurrency run or end-to-end encryption audit
was performed.
