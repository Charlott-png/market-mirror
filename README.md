# Market Mirror

## Current local release — start here (2026-10-25)

The application now includes registration/login, profiles, listing management,
safe photos, search/filtering, private messages, saved products, dashboards,
optional personalization, category suggestions, price suggestions, and related
products. Phases 1–8 have a local implementation; Phase 9 is **local operation and
deployment preparation only**, as requested. Phase 10 supplies the report and
practice/demo materials. Public deployment and live PostgreSQL verification have
not been performed. Your own learning demonstration remains your checkpoint.

Earlier README content below is retained as a **historical Phase 2 snapshot**,
not current setup instructions. Original specs, plans and evidence are preserved.

### Run the existing project

Open PowerShell in this `market-mirror` directory:

```powershell
& .\scripts\local.ps1 migrate
& .\scripts\local.ps1 serve
```

Visit **http://127.0.0.1:5000/**. Use **Join** to create your own account, then
**Sign in**. Stop the server with Ctrl+C. Nothing is published to the Internet.
If script execution is blocked, use `powershell -ExecutionPolicy Bypass -File
.\scripts\local.ps1 serve`; this changes policy only for that new process.

The helper uses Waitress (a web server), chooses the local SQLite database and
creates a random session-signing key in ignored `instance/local-secret.txt`.
Keep that file private. This folder is inside OneDrive: local does not necessarily
mean unsynced. Use fake class data; review OneDrive backup/sharing before storing
real personal information. Losing/changing the key signs everyone out.

Checkout now creates a completed local order, records receipt snapshots, marks
the purchased listings Sold, empties the buyer's purchased cart rows and shows
a private thank-you page. It is a classroom transaction only: no real payment
or delivery service is connected. See the
[beginner checkout guide](docs/025-checkout-guide.md).

### Fresh installation

Use CPython **3.12**, the version tested for this release. From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
& .\scripts\local.ps1 migrate
& .\scripts\local.ps1 seed
& .\scripts\local.ps1 train
& .\scripts\local.ps1 index
& .\scripts\local.ps1 serve
```

`seed` is optional: it adds fictional products, not usable shared-password
accounts. `train` builds synthetic teaching models; `index` refreshes related
product features from the current active catalogue. Repeat `index` after adding
many products. Missing AI files do not prevent manual listing creation.
Model artifacts never need to be downloaded from an unknown source.

The first install needs Internet access for packages. Afterwards the core app,
tests, synthetic training, and demo work offline. Live photo suggestions are
optional and require Internet access plus a private provider key; every manual
listing feature works without one.

### Optional real Gemini photo suggestions

Market Mirror can use Google Gemini to suggest a listing Title and Category from
a product image. This feature is disabled by default. Follow the beginner guide:

[Set up real Gemini image suggestions](docs/024-gemini-vision-setup.md)

Create/manage a key at <https://aistudio.google.com/apikey>, copy `.env.example`
to the ignored `.env` file, add the key privately, enable the feature and restart
the server. Never paste a real key into source code, Git, screenshots or chat.
Google states that free-tier submitted content may be used to improve its
products, so use ordinary product photos rather than personal/sensitive images.

### Optional Gemini AI Shop Assistant

Market Mirror now includes a floating product-discovery assistant. It sends a
bounded question and limited active-product facts to Gemini, accepts only
validated product IDs, and builds current links from its own database. It is
disabled by default. Add `SHOP_ASSISTANT_ENABLED=true` beside your private
`GEMINI_API_KEY` in the ignored `.env` file, then restart the server. Read the
[beginner AI Shop Assistant guide](docs/027-ai-shop-assistant-guide.md) before
enabling it. Do not include personal or payment information in questions.

### Test and maintain

```powershell
New-Item -ItemType Directory -Path .pytest-tmp -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp/run
.\.venv\Scripts\python.exe -m pip check
& .\scripts\local.ps1 check
& .\scripts\local.ps1 images
& .\scripts\local.ps1 purge
```

pytest deletes/recreates its dedicated `--basetemp` folder: never point it at
`instance`, your uploads, or a folder containing work. `images` only reports;
`purge` removes activity older than 90 days and expired rate-limit counters.

Verified release: **536 tests passed** in an isolated test environment;
dependency and schema checks passed. See the evidence record for exact results
and the remaining manual/production verification limits.

### Read in this order

1. [Learning guide: Phases 3–10](docs/phase-03-10-learning-guide.md) — what each
   component does, why it exists, and small exercises.
2. [Architecture and report](docs/project-report.md) — request flow, database
   relations, actual AI metrics and limitations.
3. [Demo walkthrough](docs/demo-guide.md) — a seller/buyer story you can practise.
4. [Operations/deployment instructions](docs/operations-runbook.md) — backups,
   maintenance, privacy, and the optional future PostgreSQL/HTTPS release path.
5. [Verification and traceability](docs/verification-matrix.md) — evidence versus
   requirements, including checks not yet performed.
6. [Gemini vision setup](docs/024-gemini-vision-setup.md) — optional real image
   suggestions, private `.env` setup, privacy and troubleshooting.
7. [Checkout guide](docs/025-checkout-guide.md) — orders, transactions,
   snapshots, exact money, retries and two-buyer conflicts.
8. [AI Shop Assistant guide](docs/027-ai-shop-assistant-guide.md) — bounded RAG,
   structured output, trusted links, privacy, rate limits and setup.

The approved specification is `specs/003-016-remaining-phases-specification.md`;
its implementation plan is `plans/003-016-implementation-and-test-plan.md`.
Changes beyond that scope start with another specification and your approval.

---

## Historical README — Phase 2 snapshot (retained for context)

The following describes the project before Phases 3–10 execution. Feature-status
and setup statements in this historical section are superseded by the section above.

Market Mirror is a student-built online marketplace that will let people create accounts, list products, browse and search, save products, and contact sellers. Later stages will add explainable AI assistance for product categories, prices, and recommendations.

This repository contains **MM-001: Project Foundation** and the **MM-002 database implementation**. The Flask pages work, and users/products can be stored through the developer shell. Registration and marketplace web forms come in later phases. The phase roadmap in `plans/market-mirror-phase-roadmap.md` replaces the original weekly schedule.

## Prerequisites

Before starting, install:

- Python 3.11 or newer
- Git
- A web browser
- PowerShell, which is included with Windows

Check the installations:

```powershell
python --version
git --version
```

Each command should display a version number. If `python` opens the Microsoft Store or reports that it cannot be accessed, install Python from the official Python website and select **Add Python to PATH** during installation.

## Create a virtual environment

A virtual environment is a private package area for one project. It prevents Market Mirror's packages from interfering with other Python projects.

From the `market-mirror` directory, create it:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

After activation, the PowerShell prompt should begin with `(.venv)`.

If PowerShell blocks activation, allow scripts only for the current PowerShell process and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## Install dependencies

Install the packages needed to run and test the project:

```powershell
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains packages needed by the running website. `requirements-dev.txt` also includes developer tools such as pytest.

## Run the application

With the virtual environment activated, start the local development server:

```powershell
python run.py
```

Open these addresses in a browser:

- Home page: <http://127.0.0.1:5000/>
- Health endpoint: <http://127.0.0.1:5000/health>

Stop the server by returning to PowerShell and pressing `Ctrl+C`.

The Flask development server is useful for learning and local development. It is not designed to host a public production website.

## Run the tests

With the virtual environment activated, run:

```powershell
python -m pytest -q
```

pytest acts like an automated inspector. It requests pages, examines responses, and checks database records against the approved MM-001 and MM-002 specifications. Each database test uses temporary data, separate from your development database.

If your Windows environment restricts its normal temporary directory, use a dedicated disposable test folder:

```powershell
New-Item -ItemType Directory -Path .pytest-tmp -Force
.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp/run
```

pytest clears the folder supplied to `--basetemp`; use only this dedicated test folder, never a folder containing your work.

## Create the database

From the project directory, without needing to activate the virtual environment:

```powershell
.venv\Scripts\python.exe -m flask --app app:create_app db upgrade
.venv\Scripts\python.exe -m flask --app app:create_app db current
.venv\Scripts\python.exe -m flask --app app:create_app seed
```

A **migration** is a saved instruction for changing the database structure. `db upgrade` applies instructions not yet applied. Running it twice is safe. `db current` reports the current revision. `db check` checks for model/schema drift. `db migrate` creates a draft migration when you intentionally change models; inspect that draft before upgrading. New installations use the existing migration files, so do not run `db init` again.

Development data lives in the ignored `instance/market-mirror.sqlite` file. Starting the server never creates tables or sample rows automatically. The `seed` command adds three fictional users and twelve products. Their randomly generated credentials are discarded; these are database examples, not accounts with published passwords. Later registration will create usable accounts.

Seed behaviour is deliberately conservative: if any expected demo identity already exists, it skips the whole batch. If a demo username/email collides with a different account, it fails without changes. It does not overwrite edited demo products or repair a partial demo dataset. An unexpected failure rolls back the entire transaction. `APP_ENV=production` disables seeding.

`db downgrade base` removes the initial tables and their data. It is demonstrated only by tests using disposable databases. Never run it on data you want to keep; it is not a backup operation.

## Explore users and products

```powershell
.venv\Scripts\python.exe -m flask --app app:create_app shell
```

Inside the Python shell, `db`, `User`, and `Product` are already available:

```python
seller = db.session.scalar(db.select(User).filter_by(username="demo-alex"))
seller.username
[(product.title, str(product.price)) for product in seller.products]
product = db.session.scalar(db.select(Product).filter_by(title="Study desk lamp"))
product.seller.username
exit()
```

The `seller_id` column links a product to its owner. The database rejects missing sellers and prevents deleting users who still own products. Python validators give early errors; named database constraints provide another layer of protection. Blank optional biographies are stored as `NULL`.

## Prices, timestamps, and configuration

Use `Decimal("10.10")`, not a float, for Python price values. The approved logical money type has two decimal places. SQLite stores **integer cents** through the `Money` adapter (`10.10` dollars becomes `1010` cents) because SQLite has no native exact decimal storage. PostgreSQL uses `NUMERIC(10,2)`. The application always reads a `Decimal` in dollars. Raw SQLite queries therefore show cents; transfer data between database engines through the adapter, not by copying raw price values. This physical-storage clarification is recorded in the implementation notes.

Timestamps are generated in UTC for each insert/update. The `UTCDateTime` adapter restores timezone information when reading SQLite. Updating a record leaves its original creation time unchanged.

`DATABASE_URL` overrides the development database. `APP_ENV` defaults to `development`; `production` requires an explicit database URL. Production hosting and the PostgreSQL driver are later-phase work. Test mode without an explicit database URL uses memory and ignores the environment's database URL.

Indexes exist for seller, category, status, and creation time to support future listing queries. Unique constraints index usernames and emails. All database code is in `app/models/`, `app/extensions.py`, and `app/commands.py`; existing page routes remain in `app/routes.py`.

For a step-by-step explanation and practice tasks, see `docs/phase-02-database-guide.md`.

## Available routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Display the Market Mirror welcome page |
| `GET` | `/health` | Confirm the application is running |
| `GET` | Any unknown route | Display the custom 404 page |

## Not implemented yet

The following features are not implemented yet:

- User registration and login
- Product listings and image uploads
- Search and filtering
- Saved products
- Buyer-seller messaging
- Product categorization
- Price suggestions
- Product recommendations
- Payments, shipping, or deployment

Each major feature will receive its own specification, plan, tests, and implementation.

## Spec-Driven Development workflow

Market Mirror follows this sequence for every feature:

1. **Specification:** agree on what the feature must do.
2. **Planning:** map requirements to implementation and tests.
3. **Testing:** write tests first and observe the expected Red result.
4. **Implementation:** add the minimum code needed to turn the suite Green.

The approved documents for this stage are located in `specs/` and `plans/`.
