# Market Mirror: learn the implementation one phase at a time

You asked to execute the phases, but you do not need to understand every file in
one sitting. Treat this guide like a set of small practical lessons. Work through
one exercise, explain it aloud, then continue. Earlier MM-001/MM-002 material and
the original weekly plans remain available; the project no longer has a deadline.

## First, understand one browser request

When you click **Explore**, your browser asks the server for `/products`. Flask
chooses a Python function for that address. The function asks the database for
active products, and Jinja puts the results into an HTML template. Your browser
draws that HTML using the CSS stylesheet. JavaScript adds optional AI interactions.

The browser is not trusted to enforce important rules. Someone can change a
hidden input or type a different address. The server checks permissions and
values again, and database constraints provide another safety layer.

### Phase 3 — Who is using the website?

**What and why:** accounts, login/logout, a profile, and protected actions. A
listing needs an owner; a private conversation needs identified participants.

**Read:** `app/auth.py`, `app/forms.py`, `app/security.py`, and `app/models/user.py`.

`RegistrationForm` checks shape and length before creating a `User`. For example,
an email must resemble a valid email address. This does **not** prove someone
owns that address. The database catches duplicate usernames/emails, including
two submissions arriving at almost the same time.

We never store the original password. Werkzeug creates a salted scrypt hash:
think of it as a costly one-way fingerprint. Login checks a supplied password
against the fingerprint. It does not decrypt the saved hash.

A signed session cookie remembers the authenticated user ID. A signature makes
unauthorized changes detectable; it does not make cookie contents secret.
`SECRET_KEY` protects that signature. Sessions expire after eight hours. Logout
clears the session. Flask-Login loads the current enabled account for each request.

Authentication asks **who are you?** Authorization asks **may you do this?**
Logging in as Alice does not let Alice edit Bob's listing. CSRF tokens stop another
website from silently submitting a form using your logged-in browser. Rate limits
slow repeated attempts; their database keys are HMAC digests, not raw emails/IPs.

**Try:** create two accounts with fake emails and different strong passphrases.
Sign out, then visit `/dashboard`. You should be sent to login. Enter a wrong
password and confirm the error does not reveal whether an email exists.

**Explain:** Why is a hidden `user_id` input not proof of identity? Why do we
need both a password hash and a session-signing secret?

### Phase 4 — Sellers control their listings

**What and why:** create/edit listings, mark sold/archive/reactivate, attach a
photo. The database should stay correct even when users double-click or two tabs
submit different changes.

**Read:** `app/marketplace.py`, `app/images.py`, `Product` and `ListingSubmission`.

`create_listing` takes the seller ID from the session, not the form. Price text
becomes `Decimal`, never a binary float. SQLite stores integer cents: `$12.50`
becomes `1250`. The `Money` adapter translates this automatically. PostgreSQL
uses a decimal column instead. Do not copy raw SQLite cents into a dollar column.

A **transaction** groups changes into one success or one rollback. Creating a
product and remembering its request token happen together. Resending that token
returns the original listing rather than creating a duplicate. This behaviour
is called **idempotency**.

Each product has a `version`. A form remembers the version it displayed. If
another edit has changed it, the old form gets a 409 conflict instead of silently
overwriting the newer work. This is optimistic concurrency control. Short row
locks protect status-sensitive actions such as saving and contacting a seller.

States are deliberate: active → sold or archived; sold → archived; archived →
active. Archival hides the product without breaking the message history.

An uploaded `.jpg` might not be a photo. Pillow checks actual bytes, dimensions
and animation, applies orientation, strips metadata, and makes a fresh JPEG under
a random filename. The old image is removed only after a replacement commits.
If saving the database fails, the new file is removed instead. A crash between
steps can still leave an orphan; the maintenance command helps identify it.

**Try:** create a lamp listing for `$12.50`. Open its edit page in two tabs.
Save a change in the first tab, then submit the second. Explain the conflict.
Try an invalid price such as `12.345` and a text file renamed `.jpg`.

**Explain:** Why archive instead of delete? Why validate bytes as well as file
extensions? Why cannot a database transaction automatically roll back a file?

### Phase 5 — Help buyers find products

**What and why:** catalogue, search, filters, pagination, product details and
seller profiles. Visitors should see only appropriate public information.

**Read:** `browse`, `paginate`, `detail`, and `seller_profile` in
`app/marketplace.py`; `catalogue.html`, `product.html`, and `macros.html`.

The base catalogue query selects active products. Every filter narrows that
query using AND: electronics **and** good condition **and** price below $50.
SQLAlchemy supplies values as SQL parameters. Users cannot choose an arbitrary
SQL sort expression; `sort` maps to a small allow-list.

Search uses literal substrings. `%` and `_` normally have special SQL meanings,
so we escape them when a user means those characters literally. Jinja escapes
HTML characters so a product description becomes text, not executable script.

Pagination retrieves 20 products at a time. Sorting adds an ID tie-breaker so
equal prices do not move unpredictably between pages. Eager loading fetches
sellers together with products to avoid a separate query for every card.
ASCII case-insensitive matching is supported; sophisticated multilingual search
is not part of this version.

**Try:** combine category and price filters. Search for `%`, then for a phrase
that matches nothing. Visit page 0 and a nonexistent product. Observe the
different invalid-input, empty-result and not-found states.

**Explain:** What is the difference between “no matches” and “bad query”? Why
should emails never appear in a public seller card?

### Phase 6 — Connect buyers and sellers

**What and why:** private conversations, saves, optional interaction events and
personal dashboards. These turn a product catalogue into a useful marketplace.

**Read:** `app/engagement.py`, `app/models/activity.py`, and dashboard/message
templates. Read `record_event` separately from the essential transaction.

A conversation connects a product, its seller and one buyer. A unique
`(product_id, buyer_id)` pair prevents duplicate threads. Each message records
its sender and a request token. Only those two participants can read or reply.
Unread markers track how far each person has explicitly marked a thread read;
simply visiting a GET page does not change the database.

A saved product is a relationship: one user plus one product. Repeating “save”
should leave one relationship. A sold/archived saved item becomes an unavailable
placeholder, avoiding leaks of hidden product details.

Saved items are useful without tracking. Personalization is a separate checkbox,
off by default. If enabled, view/save/contact events can inform recommendations.
Events exclude free text and anonymous visitors, are deduplicated for 30 minutes,
and expire after 90 days when the purge command runs. Opting out deletes them.
Optional event failure must not undo a successful message or save.

**Try:** use the two accounts to save a product, send a message and reply. Mark
the product sold: an existing thread can still be used, but a new buyer cannot
start contact. Archive it: replies stop. Compare each account's dashboard.

**Explain:** Why is a conversation unique per buyer/product? Why is “mark read”
a POST? How is saving different from consenting to behavioural tracking?

### Phase 7 — Prepare data before learning from it

**What and why:** a reproducible teaching dataset, validation, partitions and
baselines. A model score is meaningless if its test examples leaked into training.

**Read:** `app/ai/data.py`; generated `instance/ai/data-card.json`, `splits.json`
and `quarantine.json` after running `scripts/local.ps1 train`.

The generator makes 168 synthetic examples in seven categories. Their prices
are invented. Each product type forms a duplicate group. We quarantine malformed
rows, unknown/private fields, conflicting groups, and suspected copies. The
documented near-copy heuristic is not a universal plagiarism detector; a real
dataset still needs human duplicate review and permission checks.

Groups are assigned with random seed 42 to training, validation and test sets.
Whole groups stay together. Training learns patterns; validation helps choose
a method; the final test set estimates performance of the frozen choice. The
SHA-256 fingerprint identifies the exact cleaned dataset. A **baseline** is a
simple method a complicated model must justify outperforming.

**Try:** train twice and compare dataset fingerprints and split memberships.
Read the limitation field. In a copied test fixture, add an invalid price and
observe quarantine. Do not use private conversations as training data.

**Explain:** Why is training accuracy insufficient? Why can repeated photos or
descriptions across train/test make a result misleading?

### Phase 8 — Add assistance, not automatic decisions

**Read:** `app/ai/training.py`, `inference.py`, `recommendations.py`, `routes.py`,
and `app/static/js/market.js`.

**Category:** TF-IDF converts words into numerical features, giving more weight
to informative terms. Logistic regression learns which features are associated
with each category. A score below 0.60, unfamiliar vocabulary, or unavailable
artifact gives no suggestion. A model score is not a promise of correctness.

**Price:** Ridge regression predicts a number from text, category and condition.
It is compared with training-set medians. The cheaper validation error wins.
In the executed evaluation, medians won, so the application uses them. MAE is
mean absolute error: if errors are $2, $5 and $8, MAE is $5. A “more advanced”
model is not automatically better. The UI labels estimates as synthetic advice.

**Recommendations:** an explicit offline command indexes active public listing
text with TF-IDF. Cosine similarity compares feature directions. At request time
we re-check visibility and exclude the current item and your own listings. An
opted-in profile weights view/save/contact as 1/3/4, respectively. Otherwise a
diverse recent-products fallback works. Two-per-seller preference avoids filling
the list with one seller when alternatives exist. Request work considers the
latest 500 candidates/events, a documented classroom-scale limit.

Training never occurs in a request. Artifacts are local, versioned and checked
for corruption. Joblib files can execute Python when loaded: a checksum is not
proof of a trustworthy author. Train your own; never accept uploaded models.

**Try:** type “Wireless keyboard” and a useful electronics description. Request
a category and price. Notice that the field changes only after **Apply suggestion**.
Change it manually and save. Try nonsense words and explain abstention.

**Explain:** Why is a median sometimes better? Why are the synthetic metrics
not evidence of real market quality? What happens after an indexed item is sold?

### Phase 9 — Run and maintain it safely

**Read:** `scripts/local.ps1`, `config.py`, `wsgi.py`, `app/operations.py` and
the operations runbook. Docker files are future preparation, not proof of deployment.

A development server helps a programmer; a WSGI server such as Waitress handles
the application as a running service. Locally we bind only to `127.0.0.1`, meaning
this computer. HTTPS, DNS, reverse-proxy trust and PostgreSQL are separate future
release decisions. A lock file pins exact dependency versions for repeatability.

`/health` says the process can answer. `/ready` also checks the database. A
request ID helps correlate safe logs without logging names, searches or messages.
A backup is useful only after you verify a restore into a separate location.
Regular purge/reconciliation is a human operation here, not an invisible scheduler.

**Try:** run the read-only image report and schema check. Review the backup
instructions. Do not practise destructive database downgrade on your real data.

**Explain:** Why does a live process not guarantee a healthy database? What
would be lost if you backed up the database but forgot the photos?

### Phase 10 — Demonstrate understanding

Follow `demo-guide.md`. Tell the story of one product from creation to sale.
For each action, name the route, permission check and database change. Then
explain one automated test that protects it. Show the actual evaluation report,
including where the simpler baseline won and where evidence is still missing.

**Your checkpoint:** explain the system without reading this guide word for word.
If a concept is unclear, pause there and ask for a smaller example. Technical
completion does not automatically mean you have mastered the implementation.
