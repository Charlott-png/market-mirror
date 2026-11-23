# MM-029 Learning Guide: Modern Chat Messaging

## What changed

Market Mirror still stores messages in the same secure database tables, but the
conversation page now presents them like a modern chat app:

- your messages are blue and aligned right;
- the other person's messages are grey and aligned left;
- each message shows a compact time;
- the newest page checks for messages every three seconds; and
- the input remains at the bottom of the chat area.

## Why the server decides bubble ownership

The browser could lie about a user ID. Market Mirror therefore compares each
message's `sender_id` with the signed-in user's ID on the server. The browser
receives only `is_own: true` or `false` for a permitted conversation. This is
both a security rule and the fact that chooses the bubble side.

## What polling means

Polling is like asking, “Are there new messages?” on a schedule. Every three
seconds JavaScript sends a small GET request. This is simpler than WebSockets
for a local class project, although it is not truly instant and makes more HTTP
requests than a realtime connection.

The request sends an `after_id` cursor. A cursor is a bookmark: if the browser
already knows message 42, it asks only for IDs after 42. The server returns no
more than 50 at once, so a long gap cannot create an enormous response.

## Preventing duplicates

JavaScript keeps a Set of message IDs already on the page. A Set contains each
value once. Even if a response overlaps something already displayed, that ID
is ignored. The cursor only moves forward.

The scheduler uses `setTimeout` after a request finishes instead of starting a
new request every three seconds regardless of the previous one. This prevents
overlapping requests on a slow connection.

## Safe message text

Messages may contain characters that look like HTML. Server-rendered Jinja text
is escaped. JavaScript-created bubbles use `textContent`, which tells the
browser, “This is text, not executable markup.” It never inserts a message with
`innerHTML`.

## Timestamps and timezones

The database stores UTC, a shared world time standard. The HTML contains a UTC
fallback such as `10:45 AM UTC`. When JavaScript is available, the browser uses
`Intl.DateTimeFormat` to show the same moment in the viewer's local timezone.
The semantic `<time>` value retains the exact machine-readable moment.

## Why polling GET does not mark messages read

GET should retrieve information without changing it. Automatically changing a
read marker on every poll would make background tabs claim messages were read.
Market Mirror keeps the explicit, CSRF-protected Mark displayed messages as
read button. JavaScript may update its newest ID but never submits it.

## Sticky is not the same as covering the screen

The composer uses sticky positioning inside the chat shell. It belongs to the
chat layout and stays after the scrollable transcript. A globally fixed form
could cover messages or the mobile bottom navigation. Responsive CSS moves the
input and Send button into one column on very narrow screens.

## Failure behavior

If a poll fails, the transcript stays visible and the page says **Waiting to
reconnect…**. A later successful check clears the warning. If the login session
ends, polling stops and the page asks for a reload; it does not redirect and
erase an unsent draft.

## Files to explain

- `app/engagement.py`: authorizes the participant, selects bounded history and
  returns safe update JSON.
- `app/templates/conversation.html`: server-rendered chat structure and normal
  form fallback.
- `app/static/css/style.css`: bubble alignment, colors, scrolling and composer.
- `app/static/js/conversation.js`: local time, polling, validation, safe DOM
  creation, duplicate prevention and scroll behavior.
- `tests/test_modern_chat.py`: server, privacy, pagination and read-only tests.
- `tests/test_modern_chat_assets.py`: browser-code safety contracts.

## Practice questions

1. Why should the client not send `is_own` as a trusted value?
2. If the current cursor is 50 and the response repeats ID 49, what should
   happen?
3. Why is `textContent` safer for a message than `innerHTML`?
4. Why does an older history page not poll for new messages?
5. When would WebSockets be a better choice than three-second polling?

## Short class explanation

“The server checks that the signed-in user belongs to the conversation and
returns only messages after a numeric cursor. Responses are limited to 50 and
never change the database. JavaScript waits three seconds between completed
requests, validates the whole response, ignores known IDs and builds bubbles
with safe text nodes. The normal CSRF-protected form still works without
JavaScript.”

