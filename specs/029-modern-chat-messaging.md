# MM-029 — Modern Conversation Chat Interface

Status: IMPLEMENTED — MM-029 and PLAN-029 approved; verification complete

Date: 2026-11-07 (Asia/Shanghai)

## 1. Purpose

Upgrade Market Mirror's existing private conversation page so it looks and
behaves like a small modern chat application while preserving the messaging
security and data rules already implemented by MM-008.

The upgrade provides:

1. outgoing blue chat bubbles aligned to the right;
2. incoming grey chat bubbles aligned to the left;
3. a small time under every message;
4. automatic checks for new messages every three seconds; and
5. a message composer that stays at the bottom of the chat window.

This is an interface and polling upgrade. It is not end-to-end encryption,
WebSockets, push notifications, file sharing, typing indicators, delivery
receipts or a replacement for the existing message database.

## 2. Existing behavior that must remain

Market Mirror already has:

- private conversations between one buyer and one seller;
- participant checks on every conversation read and write;
- plain-text messages limited to 2,000 characters;
- HTML escaping that prevents message-script execution;
- CSRF-protected POST forms;
- one-use request tokens that prevent duplicate messages;
- a limit of 20 sent messages per user per ten minutes;
- stable ordering by creation time and message ID;
- 50-message pagination;
- independent read markers;
- readable sold-product conversations;
- read-only archived-product conversations; and
- a normal HTML form that works without JavaScript.

MM-029 must not weaken or silently replace any of these rules.

## 3. User stories

### US-029-01 — Recognize my own messages

As a participant, I can immediately distinguish messages I sent because they
are right-aligned in a blue bubble.

### US-029-02 — Recognize the other participant's messages

As a participant, I can see received messages left-aligned in a grey bubble.

### US-029-03 — Understand message timing

As a participant, I can see a compact 12-hour time below each message and can
obtain the complete timestamp from the semantic time element.

### US-029-04 — Receive new messages without reloading

As a participant on the latest conversation page, I see newly stored messages
appear after a background check without refreshing the full page.

### US-029-05 — Keep the composer available

As a participant, I can reach the input and Send button at the bottom of the
chat window while reading recent messages.

## 4. Scope

### Included

- the individual conversation page;
- one read-only authenticated updates endpoint;
- a dedicated conversation JavaScript file;
- conversation-specific CSS;
- server-rendered and JavaScript-created message bubbles;
- timestamps and safe browser-local formatting;
- polling every three seconds on the latest message page;
- duplicate prevention and catch-up handling;
- scroll behavior and status feedback;
- sticky message input and Send button;
- responsive, keyboard, dark-mode and reduced-motion behavior;
- pytest and isolated browser verification; and
- beginner documentation.

### Excluded

- changing the inbox design;
- AJAX message sending;
- WebSockets, Server-Sent Events or third-party realtime services;
- typing indicators, online presence or last-seen status;
- delivered/read checkmarks;
- automatic seller notifications;
- message editing, deletion, reactions, attachments or voice notes;
- end-to-end encryption claims;
- group chats; and
- a database migration.

Any excluded item requires a later approved specification.

## 5. Conversation layout

The page must contain one chat shell with these parts in order:

1. conversation heading and product-status notice;
2. optional older-message navigation;
3. a scrollable message list;
4. a polite connection/new-message status region; and
5. the reply composer, or a read-only archived notice.

The message list uses an ordered list because message sequence matters. Each
message item has a stable `data-message-id` and a class that identifies it as
outgoing or incoming.

The page must still have one logical H1 and must retain a link back to Messages.

## 6. Bubble appearance

### Outgoing messages

- `sender_id == current_user.id` is determined by the server.
- Align to the right.
- Use a blue or brand-blue background.
- Use text with sufficient contrast in both light and dark color schemes.
- Maximum width is approximately 75% on wider screens and may expand on narrow
  screens without causing horizontal scrolling.

### Incoming messages

- Every other permitted participant message aligns to the left.
- Use a grey/neutral surface distinct from the outgoing blue.
- Show the other participant's username in a small label so the message remains
  understandable visually and to assistive technology.

### Shared rules

- Preserve user-entered line breaks.
- Break very long words/URLs instead of widening the page.
- Message text is rendered as plain text, never trusted HTML.
- Bubbles have rounded corners, padding and visible separation.
- Color is not the only distinction: alignment, sender label and accessible
  text also identify the sender.

## 7. Timestamps

Every message has a semantic `<time>` element below its body.

The server supplies:

- an ISO-8601 UTC `datetime` value; and
- a readable fallback such as `10:45 AM UTC`.

When JavaScript is available, both initial and newly appended timestamps are
formatted in the browser's local timezone using a 12-hour hour-and-minute
display, such as `10:45 AM`. The full localized date and time is placed in the
element's accessible label or title so messages from another date are not
ambiguous.

Invalid or unparsable time data must leave the safe server fallback visible.

## 8. Initial history and pagination

Opening a conversation without `page` shows its newest block of at most 50
messages, displayed oldest-to-newest within that block. The view scrolls to the
bottom after initial load unless the URL targets a specific element.

Older blocks remain reachable through explicit **Older messages** navigation.
An older-history page provides **Return to latest messages** and does not poll,
because mixing newly arriving messages into an older historical block would be
confusing.

Sending a valid reply always redirects to the latest conversation view, where
the sent message is visible. Existing deterministic ordering uses
`(created_at, id)`; message IDs also provide the polling cursor.

## 9. Updates endpoint

Add a read-only endpoint:

`GET /messages/<conversation_id>/updates?after_id=<message_id>`

### Authorization

- Authentication is required.
- The current user must be the buyer or seller in that exact conversation.
- A non-participant receives the same non-revealing 404 behavior as the HTML
  thread page.
- The endpoint must never reveal whether a guessed private conversation exists.

### Input

- `after_id` is required.
- It must be an ASCII, non-negative whole number with a reasonable digit bound.
- Missing, negative, decimal, Unicode-digit, repeated or unreasonably large
  values receive a safe HTTP 400 JSON response.
- The value is only a cursor. It does not need to identify a message in the
  conversation, so its validity cannot leak another conversation's contents.

### Query

Return messages where:

- `conversation_id` equals the authorized conversation;
- `id > after_id`;
- ordering is `created_at ASC, id ASC`; and
- at most 50 messages are included in one response.

Query count and response size must remain bounded. When more than 50 messages
are waiting, return `has_more: true`; the browser immediately requests the next
bounded batch using the newest received ID until caught up. Only one request
may be in flight at a time.

### Successful JSON

```json
{
  "messages": [
    {
      "id": 42,
      "body": "Is this still available?",
      "sender_username": "student-buyer",
      "is_own": true,
      "created_at": "2026-11-07T02:45:00Z",
      "fallback_time": "10:45 AM UTC"
    }
  ],
  "latest_id": 42,
  "has_more": false
}
```

`is_own` is calculated from the authenticated session, never accepted from the
client. The endpoint must not include email, password information, request
tokens, rate-limit keys, read markers, participant IDs or unrelated messages.

All endpoint responses use `Cache-Control: no-store` so private chat data is
not stored by intermediary caches.

### Read-only guarantee

Polling must not create or edit messages, read markers, conversations,
products, events or rate-limit rows. GET remains read-only. The existing
explicit read-marker POST remains the only MM-029-supported read-marker action.

## 10. Polling behavior

Create a dedicated `conversation.js` loaded only where its markup exists.

On the latest conversation page the script:

1. reads the conversation updates URL and highest rendered message ID from
   trusted `data-*` attributes;
2. waits three seconds;
3. requests messages after the highest ID with same-origin credentials and an
   `Accept: application/json` header;
4. validates the response shape and each field;
5. appends only IDs not already in the document;
6. updates the cursor monotonically; and
7. schedules the next check so requests never overlap.

The script uses DOM creation and `textContent`; it must not use `innerHTML` for
message bodies or usernames.

Polling pauses while the document is hidden and resumes with one immediate
check when it becomes visible. Navigation/unload cancels an active request.

## 11. Scroll behavior

- Initial latest-page load scrolls the message pane to the newest message.
- If the user is already near the bottom when messages arrive, append and keep
  the newest message visible.
- If the user has scrolled upward to read history, do not move their position.
  Show a polite **New messages arrived** status instead.
- An empty conversation remains stable and can accept its first polled message.
- The message list, not the whole page, owns its scroll area on desktop.

## 12. Failure and recovery behavior

### Temporary network/server failure

- Existing messages remain visible.
- Show a short non-technical status such as **Waiting to reconnect…**.
- Do not append an error as if it were a chat message.
- Continue checking on later three-second cycles.
- Clear the warning after a successful response.

### Session expiry or denied access

- Stop polling after an authentication/authorization response or unexpected
  login HTML.
- Show **Your session ended. Reload this page to sign in again.**
- Never redirect the entire page automatically while the user may have an
  unsent draft.

### Invalid response

- Reject the complete untrusted batch rather than partly appending it.
- Preserve current messages and show the reconnect status.
- Never display raw exception, server response or stack-trace text.

## 13. Composer behavior

For non-archived conversations:

- Keep the existing normal POST action, CSRF token and request token.
- Use the existing `MessageForm` validation and 2,000-character limit.
- Display the textarea and Send button in one responsive composer row.
- Give the textarea a visible label or an equivalent accessible name.
- Use a small default textarea height that can grow vertically.
- Make the composer sticky at the bottom of the chat shell, not blindly fixed
  over the entire browser viewport.
- Keep the Send button at least 44 by 44 CSS pixels.
- The composer must not be hidden by the fixed mobile navigation or device safe
  area.
- Pressing Enter retains normal multiline-text behavior; sending requires the
  button or standard form submission. MM-029 adds no surprise keyboard shortcut.

For archived conversations, render no enabled composer and keep the existing
read-only explanation.

Without JavaScript, the composer still submits normally, redirects, validates,
prevents replay and displays the resulting message.

## 14. Read-marker compatibility

The existing **Mark this page as read** form remains CSRF-protected and
participant-only. When new messages are appended, JavaScript may update that
form's hidden `message_id` to the highest displayed message ID, but it must not
submit the form automatically.

One participant's actions must never update the other participant's marker.

## 15. Responsive and visual requirements

- No horizontal page scrolling at 320 CSS pixels.
- Long usernames, Unicode text, long words and 2,000-character messages wrap.
- The chat shell fits beneath the site header and above the mobile bottom bar.
- The sticky composer does not cover the latest bubble, pagination, status
  message or mobile navigation.
- Incoming grey and outgoing blue meet readable contrast in light and dark
  color schemes.
- At 200% zoom, the input and Send button reflow instead of overlapping.
- Print styles show message content in a readable neutral layout and hide the
  composer/polling-only status where appropriate.
- No required behavior depends on hover or animation.

## 16. Accessibility requirements

- The transcript is an ordered list with an accessible name.
- Each message has an accessible sender identity and semantic time.
- The connection/new-message status uses `role="status"` and polite live
  announcements without announcing every three-second successful poll.
- Newly appended messages preserve DOM reading order.
- Focus never jumps when polling appends a message.
- Keyboard users can reach older messages, the read form, textarea and Send.
- Focus outlines remain visible.
- Bubble meaning is not communicated by color alone.
- Reduced-motion users receive no smooth auto-scroll or decorative motion.

## 17. Security and privacy

- Reuse the existing `participant()` authorization boundary.
- Never trust a client-supplied user/sender/participant value.
- Escape server-rendered message text and use `textContent` for appended text.
- Keep CSRF protection on every POST; the GET update endpoint performs no write.
- Keep request-token replay protection and message rate limits unchanged.
- Do not log message bodies, usernames paired with message text, CSRF values,
  request tokens or JSON payloads.
- Error logs use allow-listed event/conversation identifiers only where safe.
- Add `no-store` to private update responses.
- Do not send messages or participant data to Gemini or another service.
- Do not claim encryption beyond ordinary local application/database handling.

## 18. Data and migration impact

No schema change is required. MM-029 reuses:

- `conversations`;
- `messages`;
- `read_markers`;
- existing message timestamps; and
- existing request-token and body constraints.

The development database must not be migrated or seeded for this feature.
Browser fixtures use temporary databases and fictional accounts only.

## 19. Performance and load boundary

A three-second poll means one open latest conversation can make up to 20 read
requests per minute. Therefore:

- polling runs only on an open, visible, latest conversation page;
- only one request is active at a time;
- each response contains no more than 50 messages;
- database queries use the indexed conversation ID and monotonic message ID;
- responses contain only the five approved message fields plus batch metadata;
- no full transcript is returned on every poll; and
- polling stops when the page is left or authorization is lost.

This is suitable for a local university demonstration. Large public deployment
would later use a realtime transport and shared rate/connection controls.

## 20. Compatibility requirements

The following must remain Green:

- product contact creates one conversation and first message;
- participant/non-participant access behavior;
- safe invalid-message correction;
- sold/archived conversation rules;
- request-token replay and concurrent contact protection;
- message rate limiting;
- read-marker isolation;
- inbox, Dashboard unread counts and mobile Messages navigation;
- CSRF tests and security logging rules;
- Shop Assistant and mobile bottom navigation; and
- all earlier project tests.

## 21. Acceptance criteria

| ID | Requirement |
| --- | --- |
| AC-029-01 | Server-rendered outgoing messages are right-aligned blue bubbles and incoming messages are left-aligned grey bubbles, using server-calculated ownership. |
| AC-029-02 | Every message has a semantic timestamp with a 12-hour fallback and safe browser-local formatting. |
| AC-029-03 | The latest conversation view contains the newest block of up to 50 messages in chronological display order and offers bounded access to older history. |
| AC-029-04 | An authenticated participant can request only that conversation's messages after a valid cursor; anonymous/unrelated users receive no private data. |
| AC-029-05 | The update endpoint returns at most 50 ordered, allow-listed message objects with no-store caching and never mutates database state. |
| AC-029-06 | The latest page polls every three seconds without overlapping requests, pauses while hidden and stops after lost authorization. |
| AC-029-07 | New messages append once in stable order; overlapping/replayed batches do not create duplicate DOM bubbles. |
| AC-029-08 | Appended bodies and usernames use safe text nodes; HTML/script-like message content remains harmless. |
| AC-029-09 | Near-bottom readers follow new messages; readers scrolled upward keep their position and receive a polite notification. |
| AC-029-10 | Temporary failures preserve the transcript, show a safe reconnect state and recover after a later successful poll. |
| AC-029-11 | The non-archived sticky composer retains normal POST, CSRF, replay, validation and rate-limit behavior; archived conversations have no enabled composer. |
| AC-029-12 | The explicit read-marker form remains participant-only and is never auto-submitted by polling. |
| AC-029-13 | The chat works without JavaScript for reading, timestamps, pagination and normal form sending; only automatic refresh/local-time conversion are absent. |
| AC-029-14 | At 320 pixels, 200% zoom, keyboard use, dark mode and reduced motion, content remains readable and controls do not overlap the mobile bar. |
| AC-029-15 | Inbox, Dashboard counts, existing messaging rules and the complete regression suite remain Green. |
| AC-029-16 | No migration or real-message mutation occurs during automated/browser verification, which uses temporary data only. |

## 22. Required tests after approval

The later PLAN-029 must map each acceptance criterion to tests. At minimum it
must define:

### Unit/static tests

- outgoing/incoming class decision;
- timestamp markup and fallback;
- transcript/composer/status accessibility hooks;
- stylesheet alignment, color, sizing, overflow, sticky and mobile-safe rules;
- JavaScript three-second interval, no overlap, visibility pause, deduplication,
  text-node rendering, timestamp conversion, scroll and safe error states.

### Integration tests

- participant success and anonymous/unrelated denial;
- valid/invalid `after_id` boundary matrix;
- exact JSON allow-list and no-store header;
- order, maximum 50 and `has_more` catch-up;
- zero/one/many new messages;
- messages with equal timestamps;
- cross-conversation and cross-user privacy;
- database snapshots proving polling GET is read-only;
- latest-block and older-history behavior;
- sold and archived conversation behavior;
- normal POST sending with CSRF/replay/rate limits;
- read-marker isolation and no automatic mutation; and
- query-count boundary.

### Browser checks

- buyer and seller bubble sides/colors;
- readable timestamps;
- a new message appears within the next polling cycle without page reload;
- no duplicate after repeated/overlapping responses;
- scroll-follow versus scrolled-up notification;
- reconnect and recovery state;
- no-JavaScript send/read fallback;
- archived read-only layout;
- keyboard focus order;
- 320/360-pixel mobile navigation clearance;
- 200% zoom, dark mode and reduced motion where tools support them; and
- browser console contains no JavaScript errors.

## 23. Beginner concepts to explain

The final learning guide must explain at high-school level:

- how CSS alignment makes outgoing and incoming bubbles different;
- why the server, not JavaScript, decides who sent a message;
- what a timestamp and timezone are;
- what polling is and why three seconds is not truly instant;
- how a cursor asks only for messages newer than a known ID;
- why duplicate IDs must be ignored;
- why `textContent` is safer than inserting HTML;
- why GET polling must not alter read markers;
- how sticky positioning differs from covering the whole viewport;
- why normal HTML form fallback matters; and
- when WebSockets would be more suitable than polling.

## 24. SDD checkpoint

This document is the Specification stage only. It makes no application, CSS,
JavaScript, route, test or database change.

After explicit approval of **MM-029**:

1. create PLAN-029 with an implementation and test plan;
2. wait for explicit PLAN-029 approval;
3. write pytest contracts and demonstrate the intended Red failures;
4. implement only after the tests are defined and validated; and
5. run focused, related-regression, full-suite and isolated browser checks.

## 25. Approval record

MM-029 and PLAN-029 were explicitly approved by the user on 2026-11-07.
The tests were written and validated Red before implementation. Focused,
regression, full-suite and isolated browser verification then passed. See
`tests/029-green-verification.md`.

