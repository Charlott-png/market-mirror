# Market Mirror: demonstration and practice script

## Before the demonstration

Follow README setup. Run tests, migrations, synthetic training and catalogue
indexing beforehand. Keep the terminal ready to show the test summary and actual
evaluation JSON. Use only invented product/account details. Do not show passphrases,
the local secret file, `.env`, or database credentials on a projector.

Create two accounts through Join using your own demo passphrases: one seller and
one buyer. Use separate browser profiles/private windows so sessions do not replace
each other. A second tab in the same profile normally shares the same login.
The seed accounts have intentionally discarded passwords; they are not demo logins.

## Main story (about 10 minutes)

| Step | Action | What to explain | Expected result |
|---|---|---|---|
| 1 | Open home and Explore | Browser → Flask route → SQLAlchemy → Jinja | Public active catalogue |
| 2 | Seller signs in, opens Sell a product | Authentication identifies user | Protected form with labels |
| 3 | Enter “Wireless keyboard” and a useful electronic-device description | Fields become features, not instructions | Optional AI buttons work |
| 4 | Request category and price | Offline models, confidence, validation baseline | Advice or honest abstention; no silent save |
| 5 | Apply/revise and save `$25.00` | Human control, Decimal, server validation | One owned active listing |
| 6 | Buyer searches/filter by electronics and max $30 | AND filters, active-only query, literal search | Listing appears |
| 7 | Buyer saves and contacts seller | Unique relation and private conversation | Saved page and one thread |
| 8 | Seller replies; buyer reads and marks read | Participant authorization; independent read markers | Two messages, updated unread count |
| 9 | Buyer tries seller's edit URL | Authorization is independent of login | 404, no modification |
| 10 | Seller marks sold | State transition and stale-version protection | Public sold banner; no new contact/save |
| 11 | Buyer opens Saved | Visibility even for old relationships | Unavailable placeholder |
| 12 | Open report and tests | Actual evidence and honest limitations | Synthetic metrics, baseline winner, pending PostgreSQL |

Optional: demonstrate two edit tabs causing a 409 stale-version response, then
show that reloading obtains the current version. Do not call this a crash; it is
the intended protection against lost work.

## Offline backup demonstration

After packages are installed, turn off networking if convenient and run the local
server normally. No API call, external model or CDN is required. If the browser
or demo data is unavailable, use this isolated automated version of the story:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_demo.py -q --basetemp .pytest-tmp/demo
```

It uses real registration, password login and CSRF forms, then performs listing,
search, save, contact, reply, ownership denial and sale. Missing AI artifacts are
intentional in that test: the seller can continue with manual values. The test
does not use or modify your local development accounts.

## Questions to practise answering in your own words

1. Where is the product's owner decided? Why not trust the browser's seller ID?
2. What does a database transaction protect? What happens to an uploaded file?
3. Why use integer cents/Decimal instead of floats? How does PostgreSQL differ?
4. How do CSRF tokens, password hashing, escaping and SQL parameters differ?
5. How do request tokens and version numbers solve different duplicate/edit problems?
6. Which records are public, owner-only, participant-only or consent-dependent?
7. Why are train, validation and test different? Why split duplicate groups?
8. Why did the deployed price baseline win? What does its MAE mean?
9. Why does a perfect synthetic category score not prove real-world accuracy?
10. How does an indexed item disappear from recommendations when archived?
11. What is not verified or not built yet? What would public release require?

## Record your own rehearsal

Add a dated note here after **you** perform the demo: environment, steps completed,
what you explained without help, errors observed, and what you want to revisit.
Do not mark student understanding complete based only on the assistant's tests.
