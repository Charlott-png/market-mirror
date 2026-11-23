# MM-020 beginner guide — AJAX live search

## What changed?

Before MM-020, Explore worked like a traditional form:

1. type a search;
2. press **Find products**;
3. the browser requests a completely new page; and
4. Flask redraws the header, form, products and footer.

That method is still available. MM-020 adds a faster option: when you pause after
typing, the browser asks Flask for only the updated product area. The rest of the
page stays where it is.

This technique is often called **AJAX**. The old name originally referred to XML,
but modern applications commonly exchange JSON instead. Market Mirror's JSON
contains small pieces of HTML that Flask has already rendered safely.

## The request journey

```text
Search input
   │  input event
   ▼
300 ms debounce timer
   │  latest form values
   ▼
GET /products/search
   │  shared validation + database query
   ▼
JSON with count, grid HTML, pagination HTML and canonical query
   │
   ▼
Replace only the result containers
```

The important point is that JavaScript does **not** search the database. Flask and
SQLAlchemy still decide which products are public and which products match.

## Why wait 300 milliseconds?

Imagine typing `laptop`. Without a delay, the browser might request:

```text
l
la
lap
lapt
lapto
laptop
```

Most of those responses would be wasted. **Debouncing** resets a short timer after
each keystroke. Only when typing pauses for 300 milliseconds does the request
begin. This makes the interface responsive without asking the server to do
unnecessary work.

## What is a race condition?

Internet requests do not always finish in the order they started:

```text
Request 1: "slow"  ─────────────────────► finishes second
Request 2: "lamp"       ───────► finishes first
```

If Request 1 were allowed to update the page last, the screen would show results
for `slow` even though the box says `lamp`. That is a **race condition**.

Market Mirror uses two protections:

- `AbortController` asks the previous request to stop; and
- `requestSequence` gives each request a number, so an old response is ignored
  even if it could not be stopped in time.

This is called the **latest-request-wins** rule.

## Why keep the ordinary form?

The page is built using **progressive enhancement**:

1. begin with complete HTML that works by itself;
2. add JavaScript as a convenience; and
3. never make the convenience the only way to perform the task.

If JavaScript is disabled or a live request fails, the user can still press
**Find products**. Flask then returns the complete results page exactly as before.
This is more reliable and easier to demonstrate than an application that becomes
blank when one script fails.

## Why return server-rendered cards?

Market Mirror already has one trusted Jinja card macro. It knows how to show:

- a real image or placeholder;
- title, category, condition and price;
- the correct seller link; and
- Add to Cart, Sign in, or Your listing for the current visitor.

The live endpoint renders that same macro. JavaScript does not rebuild cards by
combining product strings. This prevents the normal page and AJAX page from
slowly becoming different, and it keeps Jinja's HTML escaping in one place.

## The spinner and accessibility

When a request starts, the page:

- reveals a small spinner;
- shows **Searching…**;
- marks the result section `aria-busy="true"`; and
- keeps the old results visible.

The status uses a polite live region. A screen reader can announce the update
without interrupting every keystroke. The spinner itself is decorative, and its
rotation is disabled when the operating system requests reduced motion.

Search focus and the typing caret stay in the same input because only the result
containers are replaced.

## Security rules

AJAX does not weaken the normal marketplace rules:

- only active products are queried;
- SQLAlchemy parameters are used instead of building SQL strings;
- `%` and `_` are treated as literal search characters;
- filters and sorts come from allow-lists;
- product text is escaped by Jinja;
- errors do not reveal SQL, paths or private products; and
- the response uses `Cache-Control: no-store` because cards can contain a
  session-specific CSRF token and account-specific controls.

The endpoint is GET-only and does not save, add to cart, message, record a view or
change a listing.

## Main files to explain in a demonstration

- `app/marketplace.py`: shared validation/query and JSON endpoint.
- `app/templates/catalogue.html`: complete fallback form and live-search targets.
- `app/templates/_product_grid.html`: shared server-rendered cards.
- `app/templates/_catalogue_pagination.html`: canonical HTML pagination links.
- `app/static/js/market.js`: debounce, request sequence, update and recovery.
- `app/static/css/style.css`: spinner, feedback layout and reduced motion.
- `tests/test_live_search.py`: executable server and markup requirements.

## A short classroom explanation

You can explain MM-020 like this:

> The normal search form still works. JavaScript listens for typing and waits 300
> milliseconds so it does not send too many requests. Flask validates the same
> filters as the normal page and returns Jinja-rendered cards in JSON. A request
> number prevents slow old results from replacing newer ones. While waiting, the
> interface shows an accessible loading state. If anything fails, the last good
> results stay visible and the normal form remains available.

