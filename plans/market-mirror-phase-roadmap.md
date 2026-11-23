# Market Mirror: Phase-Based Development Roadmap

## Execution update — 2026-10-25

The user subsequently authorized execution of Phases 1–10, approved the combined
MM-003–016 specification package, and selected **local-only operation with
deployment instructions**. This update supersedes the historical “specs only”
instruction and status table below without deleting their context.

| Phase | Current delivery state |
|---|---|
| 1 | Existing foundation retained and regression-tested |
| 2 | Database/models/migrations/seed implemented and tested |
| 3 | Accounts, sessions and profile implemented |
| 4 | Owned listings, lifecycle/version checks and safe image upload implemented |
| 5 | Browse/search/filter/details/seller views implemented |
| 6 | Private messages, saves, consent/events and dashboard implemented |
| 7 | Synthetic data validation, grouped partitions and baselines implemented |
| 8 | Category/price/recommendation assistance and fallbacks implemented locally |
| 9 | Local Waitress operation, maintenance and future deployment files/instructions delivered; PostgreSQL/HTTPS/public deployment unverified and not performed |
| 10 | Learning guide, architecture/report, traceability and demo supplied; automated demo executed; student-led demonstration remains open |

Delivery is not a blanket acceptance of every risk/edge-case criterion. Consult
`docs/verification-matrix.md` for executed evidence and remaining checks, and
`tests/003-016-verification.md` for Red/Green milestones. Start with the current
README instructions; no fixed 16-week schedule applies.

## Original roadmap snapshot (retained)

| Field | Value |
|---|---|
| Project | Market Mirror |
| Document type | High-level development roadmap |
| Schedule | No fixed number of weeks |
| Audience | Beginner student building a university-quality project |
| Updated | 2026-10-25 |
| Existing foundation | MM-001 complete |
| Current feature | MM-002 specified and tested; implementation not started |

## 1. Purpose of this roadmap

Market Mirror will now be built according to **completed phases**, not according
to a 16-week deadline. A phase may take one study session or several weeks. The
important rule is that the previous phase must be understandable and stable
before the next phase depends on it.

The final application will allow people to:

- Create and use accounts.
- List products for sale.
- Browse, search, filter, and save products.
- Contact sellers safely.
- Manage their own listings and messages.
- Receive understandable AI category, price, and product suggestions.

The project will remain a marketplace for connecting buyers and sellers. Online
payments, delivery tracking, auctions, and a full moderation department are not
part of the planned core unless they are added through a later specification.

## 2. How we will work

For now, the normal deliverable is a readable specification. Code, tests, or an
implementation plan will be created only when they are explicitly requested.
When a feature is built, the recommended sequence is:

1. **Read the specification:** Understand exactly what the feature should and
   should not do.
2. **Approve or revise it:** Resolve unclear rules before writing code.
3. **Plan:** Divide the feature into small implementation and test tasks.
4. **Test first:** Describe expected behaviour with pytest.
5. **Implement:** Write only enough application code to meet the specification.
6. **Verify:** Run old and new tests so a new feature does not break an old one.
7. **Explain and demonstrate:** Be able to describe the feature without relying
   on memorized code.

This sequence is useful because a specification is like a building blueprint:
it is cheaper to correct a sentence in the blueprint than to rebuild finished
software.

## 3. Technology direction

| Area | Planned technology | Beginner explanation |
|---|---|---|
| Server | Python and Flask | Receives browser requests and decides what response to send |
| Pages | Jinja templates, HTML, and CSS | Produces the pages visitors see |
| Database access | Flask-SQLAlchemy | Connects Python objects to database rows |
| Schema changes | Flask-Migrate/Alembic | Records safe, repeatable database structure changes |
| Local database | SQLite | A simple database stored in one local file |
| Production database | PostgreSQL | A stronger multi-user database for deployment |
| Forms and security | Flask-WTF, Werkzeug, Flask-Login | Validates forms, hashes passwords, and manages login sessions |
| Automated tests | pytest | Checks that the program behaves as specified |
| First AI models | scikit-learn | Provides understandable classical machine-learning tools |
| Deployment | To be selected in MM-015 | Makes the application available outside the development computer |

The project should not introduce a JavaScript framework unless a later feature
truly needs one. Server-rendered Flask pages are easier to learn, test, and
explain for this project.

## 4. Roadmap overview

| Phase | Specifications | Outcome | Current state |
|---|---|---|---|
| 1. Working foundation | MM-001 | Flask project, reusable pages, health check, and documentation | Complete |
| 2. Reliable data | MM-002 | Users and products can be stored safely | Spec and tests ready; implementation pending |
| 3. Identity and access | MM-003 | Registration, login, logout, and protected actions | Not specified |
| 4. Seller tools | MM-004 and MM-005 | Sellers manage listings and safe product images | Not specified |
| 5. Marketplace discovery | MM-006 and MM-007 | Visitors browse, search, filter, and inspect products and sellers | Not specified |
| 6. Buyer–seller engagement | MM-008, MM-009, and MM-010 | Messaging, saved products, and personal dashboards | Not specified |
| 7. AI-ready data and evaluation | MM-011 | Clean datasets, baselines, and honest measurements | Not specified |
| 8. AI features | MM-012, MM-013, and MM-014 | Category, price, and recommendation suggestions | Not specified |
| 9. Hardening and deployment | MM-015 | Secure, observable, deployable application | Not specified |
| 10. Final demonstration | MM-016 | Rehearsed demo, report, limitations, and evidence | Not specified |

---

## Phase 1: Working foundation — MM-001

### Goal

Prove that the smallest Market Mirror web application runs correctly before it
depends on accounts, products, or a database.

### Main deliverables

- Flask application factory.
- Home page and shared page layout.
- Health endpoint.
- Custom 404 page.
- Basic responsive CSS.
- Dependency files and beginner-friendly README.
- Foundation test suite.

### Concepts to understand

- A browser sends an HTTP request; Flask returns an HTTP response.
- A route connects a URL such as `/health` to Python code.
- Templates separate page structure from Python logic.
- A virtual environment keeps this project's packages separate.
- HTTP status codes describe results such as success (`200`) and missing (`404`).

### Important risks and checks

- The app must be constructible in test mode without starting a real server.
- Debug mode must not be permanently enabled.
- Pages must remain readable on a narrow screen.
- The health endpoint must not reveal secrets or local file paths.

### Completion gate

This phase is complete. Its tests must continue to pass during every later phase.

### Student demonstration

Start the server, open the home page, visit `/health`, request a nonexistent
page, and explain which Flask route or error handler produces each response.

---

## Phase 2: Reliable data — MM-002

### Goal

Give Market Mirror persistent storage. Persistent means that data remains after
the Flask server stops and starts again.

### Main deliverables

- Development, test, and future production database configuration.
- Shared SQLAlchemy and migration extensions.
- `User` table with normalized unique identity fields.
- `Product` table with exact decimal prices and approved states.
- One-to-many relationship: one seller can own many products.
- Foreign-key protection so a product cannot refer to a missing seller.
- Initial migration.
- Repeatable, non-destructive demonstration-data command.
- Database setup and migration documentation.

### Small build steps

1. Configure SQLite without changing the existing application routes.
2. Initialize SQLAlchemy and Flask-Migrate in the application factory.
3. Create and validate the `User` model.
4. Create and validate the `Product` model.
5. Connect users and products through `seller_id`.
6. Generate and inspect the initial migration.
7. Add safe fictional seed data.
8. Run all MM-001 and MM-002 tests.

### Concepts to understand

- A model class describes a table; an object represents one row.
- A primary key uniquely identifies a row.
- A foreign key protects a relationship between tables.
- A transaction makes a group of database changes succeed or fail together.
- Money uses decimal values because normal floating-point numbers can be
  slightly inaccurate.
- A migration is version history for the database structure.

### Important risks and checks

- Usernames and emails must remain unique after trimming and lowercasing.
- Password hashes must never appear in model representations or output.
- A price must have no more than two decimal places and remain inside its range.
- Every product must have a real seller.
- SQLite foreign-key enforcement must actually be enabled.
- Seed data must not duplicate or erase existing records when run twice.
- Tests must never modify the developer's normal database.

### Completion gate

- A fresh database can be created entirely from migrations.
- The seed command can safely run twice.
- Restarting the application preserves records.
- Every MM-001 and MM-002 test passes.
- The student can explain the two tables and their relationship.

### Student demonstration

Show the empty migration-created database, run the seed command, query one user
and their products, restart the application, and show that the rows still exist.

---

## Phase 3: Identity and access — MM-003

### Goal

Allow users to create accounts and prove who they are, while preventing one user
from acting as another user.

### Planned features

- Registration form.
- Secure password hashing and password verification.
- Login and logout.
- Session-based current user.
- Protected pages that redirect anonymous visitors to login.
- Basic profile display and carefully limited profile editing.
- CSRF protection on every form that changes data.
- Generic authentication errors that do not reveal whether an email exists.
- Safe redirect handling after login.

### Small build steps

1. Specify identity, session, and profile rules.
2. Add form validation without changing the database on invalid input.
3. Hash passwords before storage.
4. Add Flask-Login session support.
5. Protect a small test-only account page first.
6. Add profile viewing and approved editable fields.
7. Add throttling or a documented classroom-safe login-attempt policy.

### Concepts to understand

- Authentication asks, “Who are you?”
- Authorization asks, “Are you allowed to do this?”
- Hashing transforms a password in a one-way manner; encryption is different.
- A browser cookie can identify a server-side login session.
- CSRF protection prevents another website from secretly submitting a form as
  the logged-in user.

### Important risks and checks

- Plain passwords must never be stored or logged.
- Duplicate emails and usernames must produce useful but safe messages.
- A forged or expired session must not authenticate a user.
- Logout must invalidate access to protected pages.
- A `next` URL must not redirect the user to a malicious external website.
- Two simultaneous registrations cannot bypass database uniqueness.

### Completion gate

- A valid user can register, log in, visit a protected page, and log out.
- Invalid and duplicate data creates no partial account.
- Anonymous and unrelated users cannot access protected account data.
- All earlier tests still pass.

### Student demonstration

Register one account, explain why its password is unreadable in the database,
show the login session, log out, and demonstrate that a protected URL is blocked.

---

## Phase 4: Seller tools — MM-004 and MM-005

### Goal

Allow authenticated sellers to create and manage their own product listings,
including safe images.

### MM-004: Product management

- Create, edit, archive, mark sold, and optionally delete a listing.
- Validate title, description, price, category, condition, and status.
- Derive the seller from the logged-in session rather than a submitted user ID.
- Enforce ownership on every read and write operation.
- Define an explicit state machine for `active`, `sold`, and `archived`.
- Use POST/Redirect/GET to reduce accidental repeat submissions.

### MM-005: Images

- Accept only approved image formats and sizes.
- Verify actual image content instead of trusting the filename.
- Generate random server-side filenames.
- Correct image orientation and create display-sized versions.
- Provide an accessible placeholder and useful alternative text.
- Define cleanup rules when an image is replaced or a database operation fails.

### Concepts to understand

- CRUD means create, read, update, and delete.
- Ownership checks are authorization checks.
- Server-side validation is required even when the browser validates a form.
- File content, extension, and MIME type are different pieces of information.
- A database row and an image file must remain consistent when an operation fails.

### Important risks and checks

- Changing a hidden `seller_id` field must never transfer ownership.
- User A must never edit, archive, or delete User B's listing.
- A failed form must preserve safe values but commit no partial change.
- Repeated submission must not create duplicate listings.
- Path traversal names such as `../file.jpg` must never escape the upload folder.
- Corrupt, huge, disguised, or executable uploads must be rejected.
- Failed image or database writes must not leave orphaned files.

### Completion gate

- A seller can manage the full lifecycle of their own listing.
- Another account receives the approved denial or not-found response.
- Listing and image failures leave both the database and filesystem consistent.
- Pages work without an image and at 320-pixel width.

### Student demonstration

Create a listing, edit it, upload an image, show ownership protection using a
second account, mark the listing sold, and explain each validation layer.

---

## Phase 5: Marketplace discovery — MM-006 and MM-007

### Goal

Help visitors find relevant active products and inspect the product and seller
before making contact.

### MM-006: Browse and search

- Browse active listings with stable pagination.
- Search titles and descriptions.
- Filter by category, condition, and price range.
- Sort with fixed allow-listed choices such as newest and price.
- Preserve selected query options in pagination links.
- Show useful empty states.

### MM-007: Product details and public sellers

- Product detail page with safe seller information.
- Public seller profile showing only public fields and active listings.
- Clear handling for sold, archived, missing, or unavailable products.
- Optional privacy-aware view events for later recommendations.

### Concepts to understand

- A query asks the database for selected rows.
- Filtering narrows results; sorting changes their order.
- Pagination loads a limited number of rows at a time.
- An index helps the database find certain rows efficiently.
- Escaping displays user text as text instead of executable HTML.

### Important risks and checks

- Search-like SQL and script text must not cause injection or XSS.
- Public queries must never leak archived or private data.
- Unknown filters and page values must not crash the server.
- Sorting must use fixed column mappings, not raw user-provided SQL.
- Equal prices or timestamps require an ID tie-breaker for stable pages.
- Seller email and password hash must never appear in public HTML.
- Large result sets must not load every product at once.

### Completion gate

- Search, filters, sorting, and pagination work together predictably.
- Only approved visible products appear publicly.
- Direct URLs cannot reveal hidden products or private seller data.
- Empty and invalid queries produce intentional results rather than server errors.

### Student demonstration

Search a mixed sample catalogue, combine two filters, change the sort order,
move between pages, and explain the database query in plain language.

---

## Phase 6: Buyer–seller engagement — MM-008, MM-009, and MM-010

### Goal

Turn a catalogue into a useful marketplace by allowing users to communicate,
remember interesting products, and manage their activity.

### MM-008: Messaging

- Start one conversation about a product.
- Allow only the buyer and seller to read or send messages.
- Store plain-text, length-limited, escaped messages.
- Order messages deterministically and paginate long conversations.
- Define what happens when the related product becomes sold or unavailable.
- Prevent users from contacting themselves through their own listing.

### MM-009: Saved products and interaction events

- Save and unsave visible products.
- Enforce one saved relationship per user and product.
- Handle repeated clicks safely.
- Decide how unavailable saved products are represented.
- Record only minimal, server-trusted interaction events needed by later AI.

### MM-010: Personal dashboard and cleanup

- Show the current user's listings by status.
- Show saved products and conversation summaries.
- Provide meaningful first-user empty states.
- Keep every private query scoped to the current user.
- Refactor repeated query and authorization logic behind regression tests.

### Concepts to understand

- A many-to-many relationship connects many users to many saved products.
- An idempotent operation has the same final result when safely repeated.
- Private resources need authorization on every request, not just hidden links.
- Analytics events should be minimal because behaviour data affects privacy.

### Important risks and checks

- Guessing a conversation ID must never reveal another conversation.
- Forged sender, buyer, seller, or user IDs must be ignored.
- Script text in a message must display harmlessly.
- Concurrent save requests must create only one saved relationship.
- GET requests must not change save or message state.
- Dashboard totals and records must belong only to the logged-in user.
- Long conversations and large dashboards require pagination.

### Completion gate

- Two different accounts can communicate about a product privately.
- Save and unsave remain correct under repeat requests.
- Each account's dashboard contains only its own private data.
- The essential non-AI marketplace is now demonstrable from end to end.

### Student demonstration

Use a seller and buyer account: publish and find a product, save it, begin a
conversation, reply as the seller, and compare the two private dashboards.

---

## Phase 7: AI-ready data and honest evaluation — MM-011

### Goal

Prepare trustworthy data and measurement rules before building AI features.
This phase prevents an impressive-looking model score from hiding bad science.

### Main deliverables

- Dataset schema and data dictionary.
- Data-source and licence record.
- Reproducible validation and cleaning script.
- Class, missing-value, duplicate, price, and outlier report.
- Training, validation, and test split policy.
- Duplicate-group protection against data leakage.
- Simple non-AI baselines.
- Saved evaluation reports with reproducible random seeds.

### Concepts to understand

- Features are information given to a model; a label is what it learns to predict.
- Training data teaches; validation data guides choices; test data is the final exam.
- Data leakage lets a model indirectly see answers it should not know.
- A baseline is a simple method that a useful model should beat.
- Accuracy alone can hide failure on smaller categories.

### Important risks and checks

- Personal or copyrighted data cannot be used without a defensible source policy.
- Duplicate listings must not appear on both sides of a train/test split.
- Preprocessing must learn only from training data.
- Synthetic data must be clearly labelled as synthetic.
- Rare categories need per-class metrics, not only overall accuracy.
- Model results must record dataset version, configuration, and random seed.

### Completion gate

- Another student can recreate the same cleaned data and split.
- Baseline results are saved and understandable.
- The source, licence, limitations, and cleaning decisions are documented.
- The student can explain why the test set stays untouched during development.

### Student demonstration

Show one raw-data problem, run the validation process, explain the split, and
compare a hand-checkable baseline with its saved metric report.

---

## Phase 8: AI features — MM-012, MM-013, and MM-014

### Goal

Add useful suggestions that assist users without pretending the models are
always correct. AI output remains advice; the user keeps control.

### MM-012: Automatic category suggestion

- Use title and description text as input.
- Begin with TF-IDF text features and an understandable classifier.
- Return a category, confidence information, and model version.
- Use a low-confidence fallback instead of forcing an uncertain category.
- Let the seller confirm or change the suggestion.
- Record accepted and corrected suggestions for later evaluation.

### MM-013: Price suggestion

- Use category, condition, and carefully selected text/numeric features.
- Compare against a simple category-median baseline.
- Return a range or clearly labelled estimate, never a guaranteed sale price.
- Reject unsupported or impossible inputs safely.
- Report MAE and category-level errors so large mistakes remain visible.
- Record model version and the seller's chosen final price separately.

### MM-014: Product recommendations

- Start with content-based similarity between visible active products.
- Use saved/view/contact behaviour only after privacy rules are approved.
- Provide a cold-start fallback such as recent/popular diverse products.
- Exclude the current item, hidden items, and items the user should not see.
- Avoid duplicate or overly repetitive recommendations.
- Show a short reason such as “Similar category and description.”

### Concepts to understand

- Training fits a model; inference uses the fitted model for a new example.
- Classification chooses a label; regression estimates a number.
- TF-IDF represents important words as numbers.
- Similarity compares item representations.
- Confidence is not the same thing as certainty.
- A model artifact must match the code and data schema that created it.

### Important risks and checks

- A missing or corrupt model must not crash normal marketplace features.
- Unknown words, empty text, new categories, and extreme prices need fallbacks.
- AI training must never occur inside a normal web request.
- Suggestions must never silently overwrite the seller's choices.
- Evaluation data must remain separate from training data.
- Recommendations must apply the same visibility rules as public search.
- Popularity feedback loops should not make every user see only the same items.

### Completion gate

- Each model beats its agreed baseline on the frozen evaluation data, or its
  failure is honestly reported and the baseline is retained.
- Web requests use versioned saved models and safe fallbacks.
- Every suggestion is clearly labelled, reversible, and explainable.
- Core marketplace actions still work when all model files are unavailable.

### Student demonstration

Enter one normal and one unusual listing, show each suggestion and fallback,
correct a category manually, explain the evaluation metrics, and disable the
model file to demonstrate graceful failure.

---

## Phase 9: Hardening and deployment — MM-015

### Goal

Prepare Market Mirror to run safely outside the development computer and make
failures understandable instead of silent.

### Main deliverables

- Production configuration through environment variables.
- PostgreSQL deployment and migration procedure.
- Persistent image-storage decision.
- Secure cookies, secret management, HTTPS, and production error settings.
- Request-size limits, authorization audit, CSRF audit, and safe headers.
- Structured logs that exclude secrets and message contents.
- Health/readiness checks that do not leak details.
- Backup and restore instructions.
- Privacy, data-retention, and account-deletion policy.
- Deployment rollback and incident checklist.

### Concepts to understand

- Development and production are different environments.
- A secret belongs in protected configuration, not source code.
- Observability means using safe logs and checks to understand system health.
- A backup is only trustworthy after a restore has been tested.
- A database migration must be compatible with the deployed application version.

### Important risks and checks

- Production must not use a default or committed secret key.
- Debug pages must never be public.
- Local disk may be temporary on a hosting provider.
- SQLite behaviour may differ from PostgreSQL behaviour.
- Logs must not include passwords, tokens, private messages, or personal data.
- A failed deployment must have a documented rollback path.
- The application needs a clear response when database or storage is unavailable.

### Completion gate

- A clean deployment can be created entirely from documentation.
- Database migrations and static/upload storage survive a restart.
- Production smoke tests pass over HTTPS.
- A backup can be restored into a safe test environment.
- Security and privacy checklists have recorded evidence.

### Student demonstration

Show the deployed application, configuration separation, one safe log entry, the
migration version, and the documented recovery process without revealing secrets.

---

## Phase 10: Final demonstration and evaluation — MM-016

### Goal

Turn the completed software into a clear university presentation that proves
understanding, not merely that the code happens to run.

### Main deliverables

- Final architecture diagram.
- Database relationship diagram.
- Feature-to-specification and feature-to-test traceability table.
- AI data cards, model cards, metrics, and limitation statements.
- Repeatable demonstration data.
- Primary and backup demonstration script.
- Final regression, accessibility, security, and deployment evidence.
- Written report with decisions, trade-offs, problems, and future work.
- Clean installation instructions for the assessor.

### Demonstration story

1. Open the public marketplace and search for a product.
2. Register or log in as a seller.
3. Create a product and discuss validation and image safety.
4. Review and optionally correct category and price suggestions.
5. Log in as a buyer, search, save, and contact the seller.
6. Return as the seller and reply through the dashboard.
7. Show recommendations and explain their reason and limitations.
8. Show automated tests, architecture, database relationships, and AI metrics.
9. Demonstrate one safe failure or fallback instead of showing only ideal input.

### Questions the student should be ready to answer

- Why was Flask chosen?
- What is the difference between authentication and authorization?
- Why is money stored as a decimal?
- How do foreign keys protect product ownership?
- How are file uploads verified?
- How are SQL injection, XSS, and CSRF reduced?
- Why are training and test data separated?
- What baseline does each AI model need to beat?
- What happens when an AI model is wrong or missing?
- What would need to change before using real users and real personal data?

### Completion gate

- The project can be set up from its documentation.
- The complete automated suite passes in a clean environment.
- The main demo and backup demo have both been rehearsed.
- Every claim in the report has code, test, metric, or documented evidence.
- Known limitations are stated honestly with sensible future improvements.

---

## 5. Major milestone gates

| Milestone | Reached after | Meaning |
|---|---|---|
| Foundation | Phase 1 | The web project runs and can be tested |
| Data core | Phase 2 | Valid users and products persist safely |
| Seller MVP | Phase 4 | A user can securely create and manage a listing |
| Marketplace MVP | Phase 6 | Seller and buyer can complete the main non-payment journey |
| AI-ready | Phase 7 | Data and evaluation are trustworthy enough for modelling |
| AI-enhanced | Phase 8 | Three optional, explainable AI features work with fallbacks |
| Release candidate | Phase 9 | The application is deployable and operationally documented |
| University submission | Phase 10 | The system, evidence, report, and demonstration are ready |

The best first large target is the **Marketplace MVP**. It creates a useful
application even if the AI phases later need to be simplified.

## 6. Priority rules if time becomes limited

### Must have

- Stable foundation and database.
- Secure accounts.
- Ownership-protected product management.
- Safe image handling.
- Browse, search, filters, and product details.
- Saved products or messaging, preferably both.
- Automated regression and authorization tests.
- Clear setup and demonstration documentation.

### Should have

- Both messaging and saved products.
- Personal dashboard.
- Category suggestion with user override.
- Price baseline and price suggestion.
- Deployed PostgreSQL version.

### Could have

- Personalized behavioural recommendations.
- Advanced moderation tools.
- More sophisticated model experiments.
- Live notifications or richer client-side interactions.

If a deadline appears, reduce optional scope rather than weakening password,
authorization, upload, privacy, or test protections.

## 7. Definition of done for every feature

A feature is not complete merely because its ideal demonstration works. It is
complete when:

- Its approved requirements and exclusions are clear.
- Valid input produces the expected result.
- Boundary, invalid, unauthorized, missing, and repeated input are handled.
- Database or file failures do not leave corrupt partial state.
- Existing features still pass their regression tests.
- Pages are keyboard-usable and readable on a narrow screen.
- Secrets and private values are absent from pages, errors, and logs.
- Setup or behaviour changes are documented.
- The student can explain the data flow and one important trade-off.

## 8. Immediate next choice

The project currently stops before MM-002 implementation. The next activity can
be either:

1. Read the existing approved MM-002 specification only; or
2. Explicitly request MM-002 implementation when ready.

No future phase needs to be started until the current phase is understood.
