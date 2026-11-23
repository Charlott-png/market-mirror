# MM-029 Red Verification

Date: 2026-11-07 (Asia/Shanghai)

## SDD authorization

- MM-029 was explicitly approved.
- PLAN-029 was explicitly approved.
- Only test and evidence files were added before this Red run; no chat route,
  template, CSS or JavaScript implementation had been changed.

## Collection

Command:

`python -m pytest tests/test_modern_chat.py tests/test_modern_chat_assets.py --collect-only -q`

Result: **29 tests collected successfully**.

## Validated Red run

Command:

`python -m pytest tests/test_modern_chat.py tests/test_modern_chat_assets.py -q --basetemp=.pytest-mm029-red-final`

Result: **28 failed, 1 passed in 45.05 seconds**.

The single passing test confirms that the existing normal reply already
redirects to the latest thread URL. The failures match the intentionally
missing MM-029 work:

- no semantic chat shell or owned bubble classes;
- no newest-first chat-history blocks;
- no participant-only `/updates` endpoint;
- no cursor validation, bounded JSON, no-store header or read-only polling;
- no composer/read-form chat hooks;
- no chat-specific CSS;
- no page-specific scripts block; and
- no `conversation.js` file.

The final Red run had no fixture errors or warnings. It therefore validates the
contracts rather than an accidental broken test environment.

Implementation is now allowed under the approved SDD sequence. Assertions must
not be weakened merely to obtain Green.

