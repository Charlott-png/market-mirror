# Understanding the AI Shop Assistant

MM-027 adds a floating helper to the bottom-right of Market Mirror. A signed-in
shopper can ask a normal question such as **“Find me a cheap camera.”** The
assistant can recommend up to three active products and link to their real
Market Mirror pages.

The feature is optional. Home, Explore, filters, cart and checkout still work
when Gemini is disabled, the key is missing or the Internet is unavailable.

## The most important idea: Gemini is not the database

Gemini does not automatically know which Market Mirror products exist today.
For each question, the server retrieves a small, fresh list of active products:

```text
Shopper question
      │
      ▼
Market Mirror selects up to 60 active products
      │
      ▼
Gemini suggests product IDs and short reasons
      │
      ▼
Market Mirror checks those IDs again and builds real links
```

This is a small example of **retrieval-augmented generation**, often called
RAG. “Retrieval” means looking up current facts. “Generation” means asking the
AI to produce a useful answer using those facts.

## What information is sent?

Gemini receives only a bounded question, recent browser-memory conversation
and public facts for active products:

- product ID;
- title;
- category;
- condition;
- price; and
- the first 300 description characters.

It does not receive seller email, username, account ID, cart, saves, orders,
messages, image bytes, filenames, sold listings or archived listings.

If more than 60 products are active, Market Mirror first includes literal
query matches, then fills remaining places with cheap and recent products. The
AI never receives an unlimited database dump.

## Why Gemini returns IDs instead of links

An AI can make mistakes or “hallucinate”—confidently produce something that is
not true. Letting it create clickable URLs would be risky.

Instead, Gemini returns a strict shape like:

```json
{
  "summary": "I found two cameras.",
  "recommendations": [
    {"product_id": 14, "reason": "This fits the budget."}
  ],
  "follow_up": "Would you prefer a particular condition?"
}
```

Market Mirror accepts only zero to three distinct IDs from the exact candidate
list it sent. It rejects extra fields, unsafe text, duplicate IDs and unknown
IDs. It then creates the title, current price, image and `/products/14` link
from its own database.

This is a **trust boundary**: AI output is treated like untrusted form input,
not like application code.

## Why products are checked twice

A camera could be active when Gemini starts answering and sold a moment later.
After Gemini responds, Market Mirror queries every suggested ID again and keeps
only products that are still active.

That changing-in-between problem is called a **race condition**. Rechecking
does not reserve an item, but it prevents the widget from presenting a stale
listing as an active recommendation.

## Conversation memory

The widget keeps at most three complete question/answer exchanges in a normal
JavaScript array. This helps a follow-up such as “show me a cheaper one.”

The history is not written to:

- the database;
- cookies;
- local storage;
- session storage; or
- a chat-history file.

Refreshing the page clears it. Clear chat also aborts a pending request and
removes the in-memory messages.

## Cost and abuse protection

Only signed-in users can call Gemini. Each account may make 15 assistant
requests in a 10-minute window. One request may be active in a widget at a
time, and the server performs no automatic retry.

These limits are checked on the server. Disabling a button in JavaScript alone
would not be enough because someone can send HTTP requests without using the
page.

## Enabling your real Gemini key

The assistant is disabled by default. In the ignored `.env` file, keep the same
private Gemini key used by the image assistant and add:

```text
SHOP_ASSISTANT_ENABLED=true
SHOP_ASSISTANT_MODEL=gemini-3.5-flash-lite
SHOP_ASSISTANT_TIMEOUT_SECONDS=12
```

Then restart Market Mirror. Never put the real key in source code, Git,
screenshots, reports or chat messages. The browser never receives the key.

The widget explains that the question and limited active catalogue go to
Google Gemini. Do not enter personal, payment or private information. Provider
free-tier and data-use terms can change, so review them before a live demo.

## Failure behavior

If Gemini is disabled, unavailable, too slow or returns invalid data, the
widget gives a short explanation and an ordinary Explore link. It never shows
a provider response body, secret key, stack trace or internal prompt.

This is **graceful degradation**: an optional smart feature may stop, while the
main marketplace stays useful.

## Run the focused tests

From the `market-mirror` folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_shop_assistant.py tests\test_gemini_shop.py -q --basetemp=.pytest-tmp\mm027-student
```

Expected result: `76 passed`.

The tests use fake Gemini objects and spend no real quota.

## Practice questions

1. Why does the server send only active product facts? Because private, sold or
   archived data is unnecessary for public shopping recommendations.
2. What happens if Gemini returns product ID 999 but 999 was not a candidate?
   The whole provider result is rejected.
3. What happens if a recommended product becomes sold during the request? It is
   removed during the second database check.
4. Why is the rate limit stored on the server? Browser controls can be bypassed.
5. Does Clear chat delete a database row? No—there is no chat-history row; it
   clears browser memory.
6. Why does ordinary Explore remain important? AI can be wrong or unavailable,
   while filters give the shopper direct control.

## Current limits

MM-027 is not a general support bot. It cannot search the wider web, contact a
seller, change a listing, add to cart, reserve an item, check out, negotiate,
read private account data or promise that a product is safe or authentic.
