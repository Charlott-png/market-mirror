# Phase 2: Understanding your database

## What you have built

Market Mirror can now remember users and products after the program closes.
Think of two linked spreadsheets. One sheet is `users`; the other is `products`.
Every product stores the ID of its seller. Unlike an ordinary spreadsheet, the
database actively refuses some mistakes, such as a product pointing to a seller
who does not exist.

This phase adds storage, not account forms. The public welcome page still looks
the same because product pages and registration belong to later specifications.

## Follow the code in this order

1. `config.py` chooses a database location. By default it is a local SQLite file.
   The factory reads settings before it initializes database tools.
2. `app/extensions.py` creates reusable database and migration tools. They are
   attached to an application inside `create_app`, so tests can create their own
   separate application and database.
3. `app/models/user.py` describes one account row. `id` is the primary key,
   meaning the row's unique number. `username` and `email` are also unique.
4. `app/models/product.py` describes one listing. Its `seller_id` is a foreign
   key: a number that must match an existing `users.id`.
5. `app/models/types.py` adapts money and timestamps between Python and the
   database. Read this after understanding the simpler model fields.
6. `migrations/versions/46b4b94079af_mm_002_database_foundation.py` records the
   actual table-building instructions. This file uses frozen historical types
   instead of importing today's model classes. Future model edits therefore
   cannot silently rewrite the original migration.
7. `app/commands.py` adds fictional example rows only when you run `seed`.

## How a row gets saved

Suppose Python constructs a `Product` with `price=Decimal("10.10")` and an
existing seller. The model validators check its title, description, choices,
and price. `db.session.add(product)` schedules the row to be saved.
`db.session.commit()` sends the changes to the database and completes the
transaction. Database constraints check rules again during this process.

For example, two requests could both check that a username is available before
either one saves it. Only a database unique constraint can reliably stop the
second save. Checking forms alone would not be enough.

If a database write fails, call `db.session.rollback()` before reusing the
session. A rollback cancels the transaction's changes. The seed command uses
one transaction, so it cannot leave a few newly created users without their
products after an error.

## Why money needs an adapter

Python floats store approximate binary fractions. That is convenient for many
measurements, but a price should mean an exact number of cents. Python therefore
uses `Decimal` here.

SQLite has no true fixed-decimal storage type. Our adapter stores 10.10 dollars
as the whole number 1010 cents. Reading the row converts it back to
`Decimal("10.10")`. PostgreSQL will store the value as `NUMERIC(10,2)` directly.
The limit is 9,999,999.99 dollars, or 999,999,999 cents. Both database checks and
Python validation enforce the appropriate units.

This is a physical-storage clarification to MM-002's decimal requirement; the
public value, precision, currency, and limits are unchanged. Do not copy raw
SQLite prices into PostgreSQL without converting cents back to dollars.

## Why timestamps need an adapter

All records use UTC, a shared time standard. Python asks for the current time
when each row is created; it does not reuse the time when the module was imported.
SQLite does not preserve timezone metadata, so `UTCDateTime` marks retrieved
times as UTC again. `created_at` stays fixed, while `updated_at` changes when a
valid edit is saved.

## Why sample accounts do not have a shared login

The examples have fictional addresses ending in `example.test`. Their credentials
are random and discarded after hashing. This prevents sample credentials from
becoming a known shared login. When registration is implemented, you will create
your own usable accounts. MM-002 stores supplied hashes; it does not authenticate
users or verify a chosen password-hashing algorithm yet.

## Practice tasks

### Task 1: Apply the migration

Run the `db upgrade` and `db current` commands from the README. Expect revision
`46b4b94079af`. Explain why applying the upgrade again does not create extra
tables. Do not use downgrade on your normal database.

### Task 2: Inspect the relationship

Run `seed`, then open the Flask shell. Query `demo-alex` and list the titles in
`seller.products`. Query one product and inspect `product.seller.username`.
Both directions use the same `seller_id` foreign key.

### Task 3: Check repeatability

Run `seed` twice. On the second run, expect a message saying that demo identities
already exist and changes were skipped. Explain why edited example rows should
not be overwritten by a demonstration command.

### Task 4: Read one test

Open `tests/test_database_integrity.py`. Find the test that changes a category
through raw SQL. It deliberately bypasses Python validation. Explain why the
database must still refuse an unsupported value.

### Task 5: Explain a rollback

Read `test_seed_failure_rolls_back_entire_transaction`. It simulates a failed
commit and checks that no partial seed rows remain. Explain how a transaction
is similar to accepting or cancelling a complete shopping list of changes.

### Task 6: Run the suite

Use the README test command. An all-green result checks the old public pages
and new database behaviour. The integration suite creates an existing sample
database, changes a different database, compares the original bytes, and reopens
the original through a fresh application. This proves isolation and persistence
using disposable data rather than risking your development rows.

## What the tests do and do not prove

They exercise SQLite storage, boundaries, relationships, direct SQL constraints,
migrations, seeding, rollback, application recreation, and existing public routes.
They do not prove that you understand the concepts; the practice tasks provide
that learning check. A live PostgreSQL deployment remains Phase 9 work.

## Primary reference material

- [Flask-SQLAlchemy setup](https://flask-sqlalchemy.palletsprojects.com/en/stable/quickstart/)
- [Flask-Migrate and migration review](https://flask-migrate.readthedocs.io/en/latest/)
- [SQLAlchemy SQLite behaviour](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
