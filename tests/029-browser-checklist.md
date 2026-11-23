# MM-029 Browser Checklist

Status: EXECUTED on 2026-11-07 against the isolated Waitress fixture.

Run only `python -m tests.preview_modern_chat`. The fixture creates a temporary
database under `.pytest-tmp` and never reads the real marketplace database.

| Step | Expected result |
| --- | --- |
| Sign in as the fixture buyer | Conversation opens without exposing another account. |
| Inspect recent transcript | Buyer bubbles are right/blue; seller bubbles left/grey. |
| Inspect time text | Every bubble has a compact local time and full semantic timestamp. |
| Inspect HTML-like message | `<script>` text is visible literally and never executes. |
| Open Older messages | Five old messages appear; polling is disabled; Return to latest is present. |
| Return to latest | Newest 50 appear in chronological order and view begins near the bottom. |
| Open fixture controls in a second tab and simulate incoming | New grey bubble appears within the next three-second cycle without full-page navigation. |
| Simulate once, wait through repeated polls | The new ID appears exactly once. |
| Stay near bottom | Transcript follows the new bubble. |
| Scroll upward, then simulate | Scroll position remains and New messages arrived is announced. |
| Add `?fixture_no_script=1` | Server bubbles/times/history/form remain; auto-refresh is absent. |
| Archived policy (automated) | History readable and composer absent. |
| Keyboard | History links, read action, textarea and Send have logical focus and visible outline. |
| 320/360 px and 200% zoom where supported | Bubbles/composer wrap and mobile navigation covers no control. |
| Console | No JavaScript errors. |

Do not send a message through the normal composer during verification. The
fixture control inserts only temporary fictional data.

## Recorded result

Bubble alignment/colors, local timestamps, literal HTML-like text, 50/5 latest
and older blocks, three-second append, duplicate prevention, near-bottom
follow, no-JavaScript fallback and console checks passed. The browser viewport
could not be programmatically resized in this session, so narrow-width/zoom
coverage remains the existing automated CSS/mobile contracts plus a short
student presentation rehearsal.

