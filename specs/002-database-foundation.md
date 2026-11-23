# MM-002: Database Foundation and Core Data Models

| Field | Value |
|---|---|
| Project | Market Mirror |
| Specification ID | MM-002 |
| Feature | Database foundation, User model, Product model, migrations, and seed data |
| Status | Approved |
| Version | 1.0 |
| Created | 2026-10-25 |
| Approved | 2026-10-25 |
| Depends on | Approved and Green MM-001 |
| Quality reference | Approved MM-QA-000 and PLAN-QA-000 |

## 1. Purpose

MM-001 proved that Market Mirror can start, render pages, return JSON, handle missing routes, and pass automated tests. MM-002 adds the first persistent data layer.

**Persistent data** is information that remains available after the server stops and starts again. Without a database, a product created today would disappear when the Python process ended.

This specification defines:

- How Flask connects to a database.
- The first `User` and `Product` tables.
- The relationship between a seller and their products.
- Rules enforced by both Python and the database.
- How schema changes are recorded through migrations.
- How safe demonstration data is created.

MM-002 does not create registration, login, product forms, or marketplace pages. Those features require later specifications.

## 2. Student learning goals

After MM-002 is complete, the student should be able to explain:

1. The difference between a Python object, a database table, and a database row.
2. What primary keys and foreign keys do.
3. Why important rules belong in the database as well as in forms.
4. What a one-to-many relationship means.
5. Why prices should not use normal floating-point numbers.
6. Why timestamps should use one consistent time standard.
7. What a database migration records.
8. Why development, testing, and production need separate configuration.
9. Why seed data must be repeatable and must not overwrite real data.

## 3. User and developer stories

### Story A: Persistent marketplace data

As a future seller, I need my account and product information stored reliably so that it remains available after the application restarts.

### Story B: Safe relationships

As a developer, I need every product to refer to a valid seller so that Market Mirror cannot contain ownerless product listings.

### Story C: Repeatable schema setup

As a developer or assessor, I need to create the database from migration files so that the project can be set up on another computer without manually creating tables.

### Story D: Demonstration data

As a student, I need safe sample users and products so that I can inspect relationships and demonstrate later features without entering every row manually.

## 4. Scope

### 4.1 Included

- Flask-SQLAlchemy integration.
- Flask-Migrate/Alembic migration support.
- Development, testing, and future production database configuration.
- A `User` model.
- A `Product` model.
- A one-user-to-many-products relationship.
- Database constraints for required fields and relationships.
- Decimal price storage in one project currency.
- UTC timestamp rules.
- An initial migration that creates the approved schema.
- A safe command that creates demonstration users and products.
- Model representations that help debugging without exposing secrets.
- Tests derived from this specification after the plan is approved.
- Documentation updates explaining migrations, database creation, and seed data.

### 4.2 Excluded

The following are intentionally not part of MM-002:

- Registration, login, logout, sessions, or password forms.
- User profile editing or account deletion.
- Product creation, editing, deletion, or sold-status web forms.
- Image uploads or image processing.
- Search, filtering, sorting, or pagination pages.
- Saved products, messages, conversations, or events.
- AI datasets, models, predictions, or recommendations.
- Production deployment or a production PostgreSQL instance.

The schema may contain fields needed by these later features, but MM-002 shall not implement their user-facing behaviour.

## 5. Database technology and environments

### DB-001: ORM

Market Mirror shall use SQLAlchemy through Flask-SQLAlchemy.

An **ORM**, or Object-Relational Mapper, lets Python classes represent database tables. A `User` Python object will represent one row in the `users` table.

Using an ORM does not remove the need to understand tables, keys, constraints, queries, and transactions.

### DB-002: Development database

- Local development shall use SQLite.
- The SQLite database file shall be stored inside Flask's local `instance` directory.
- The database file shall not be committed to Git.
- SQLite foreign-key enforcement shall be enabled for every database connection.

### DB-003: Testing database

- Automated tests shall use a separate temporary SQLite database.
- Tests shall never use the development database file.
- Each test or test group shall start from controlled data.
- Cleanup shall operate only inside a test-owned temporary location.

### DB-004: Future production database

- Configuration shall allow a database URL to be supplied through an environment variable.
- The models shall avoid SQLite-only design choices where reasonably possible.
- PostgreSQL is the expected future production database, but connecting to a live production database is outside MM-002.

## 6. User model

The database table name shall be `users`.

| Field | Type and limit | Required | Rules |
|---|---|---:|---|
| `id` | Integer | Yes | Primary key; generated by database; never accepted from a public form |
| `username` | String, maximum 30 characters | Yes | Trimmed; unique without regard to letter case; 3–30 characters; letters, numbers, underscores, and hyphens only |
| `email` | String, maximum 254 characters | Yes | Trimmed; stored in lowercase; unique; basic email structure required in future input validation |
| `password_hash` | String, maximum 255 characters | Yes | Contains a secure password hash only; never contains or displays a plain password |
| `bio` | String, maximum 500 characters | No | Optional; empty value stored consistently as `NULL` or empty string according to the approved implementation plan |
| `created_at` | UTC timestamp | Yes | Set by server/database when row is created; not supplied by user |
| `updated_at` | UTC timestamp | Yes | Set when row is created and updated whenever editable user data changes |

### USER-001: Identity uniqueness

- Two accounts shall not share the same normalized email.
- Two accounts shall not share usernames that differ only by letter case.
- Database constraints shall protect uniqueness even if form validation is bypassed.
- MM-002 seed data shall already follow the normalization rules.

### USER-002: Password data

- The model shall be able to store a secure hash for later authentication work.
- No field named `password` or `plain_password` shall exist in the database.
- Debug representations, logs, seed output, and error messages shall never contain `password_hash`.
- Password hashing and login behaviour will be specified fully in MM-003.

### USER-003: User representation

A developer-friendly representation may include the user ID and username. It shall not include email, password hash, private messages, or other future private information.

## 7. Product model

The database table name shall be `products`.

| Field | Type and limit | Required | Rules |
|---|---|---:|---|
| `id` | Integer | Yes | Primary key; generated by database |
| `seller_id` | Integer | Yes | Foreign key to `users.id`; indexed; cannot refer to a missing user |
| `title` | String, maximum 120 characters | Yes | Trimmed; visible content must be 3–120 characters |
| `description` | Text, maximum 5,000 characters | Yes | Trimmed; visible content must be 10–5,000 characters |
| `price` | Decimal/Numeric with 10 total digits and 2 decimal places | Yes | Minimum `0.01`; maximum `9,999,999.99`; never stored as binary floating point |
| `currency` | String, exactly 3 characters | Yes | ISO-style code; MM-002 supports one value: `USD` |
| `category` | String, maximum 40 characters | Yes | Must use one approved category key |
| `condition` | String, maximum 20 characters | Yes | Must use one approved condition key |
| `status` | String, maximum 20 characters | Yes | Defaults to `active`; must use one approved status key |
| `image_filename` | String, maximum 255 characters | No | Remains empty in MM-002; image behaviour begins in Week 5 |
| `created_at` | UTC timestamp | Yes | Set on row creation; not user supplied |
| `updated_at` | UTC timestamp | Yes | Updated whenever product data changes |

### PRODUCT-001: Approved category keys

MM-002 shall recognize these stored category keys:

| Stored key | Display label |
|---|---|
| `electronics` | Electronics |
| `home_garden` | Home & Garden |
| `clothing` | Clothing |
| `books_media` | Books & Media |
| `sports_outdoors` | Sports & Outdoors |
| `toys_games` | Toys & Games |
| `other` | Other |

Category keys are deliberately small and understandable. Adding or renaming a category later requires a specification revision because it affects forms, search, AI labels, seed data, and evaluation.

### PRODUCT-002: Approved condition keys

| Stored key | Display label |
|---|---|
| `new` | New |
| `like_new` | Like New |
| `good` | Good |
| `fair` | Fair |

### PRODUCT-003: Approved status keys

| Stored key | Meaning |
|---|---|
| `active` | Visible and available in future public browsing |
| `sold` | No longer available for purchase/contact according to later specifications |
| `archived` | Hidden from normal public browsing but retained for the owner/history |

MM-002 sets and stores valid values. The allowed transitions between statuses will be specified with product management in MM-004.

### PRODUCT-004: Product representation

A developer-friendly product representation may include product ID, shortened title, and status. It shall not include the complete description or any future private interaction data.

## 8. User–Product relationship

The relationship is:

```text
One User ─────────< Many Products
             seller_id
```

### REL-001: Required seller

- Every product shall belong to exactly one existing user.
- A product cannot be created with a missing or null seller.
- A product cannot point to a seller ID that does not exist.
- The relationship shall allow `user.products` to retrieve a user's products.
- The relationship shall allow `product.seller` to retrieve the owning user.

### REL-002: User deletion policy

MM-002 shall use a **restrictive deletion policy**:

- A user with products shall not be physically deleted automatically.
- Deleting a user shall not silently delete all their products.
- Account deletion is outside MM-002 and will later define archival/anonymization behaviour.

This prevents an early schema decision from destroying marketplace history before messages, saves, events, and privacy rules exist.

### REL-003: Product deletion policy

- Product physical deletion is not exposed in MM-002.
- The database relationship shall not delete the seller when a product is deleted.
- MM-004 will decide when to use physical deletion versus the `archived` status.

## 9. Validation and database constraints

### VAL-001: Two layers of protection

Later forms and services will provide friendly validation messages. The database shall provide a second layer for rules that protect data integrity.

At minimum, database constraints shall protect:

- Required values from being `NULL`.
- Unique normalized email.
- Unique case-insensitive username according to the selected cross-database strategy.
- Valid product seller foreign key.
- Positive product price within the approved maximum.
- Valid currency value.
- Valid category, condition, and status keys.

### VAL-002: Invalid writes

- An invalid write shall fail without leaving a partial row.
- A failed transaction shall be rolled back before the database session is reused.
- Raw database exceptions shall not be displayed to future users.
- Tests may intentionally bypass future forms to prove the database constraints work.

## 10. Money rules

### MONEY-001: Single currency

- MM-002 proposes `USD` as the single project currency.
- Every product shall store `USD` explicitly rather than assuming an invisible currency.
- Currency conversion is outside the 16-week MVP.
- If another currency is preferred, it should be changed now before approval and seed data creation.

### MONEY-002: Exact decimal values

- Prices shall use a database decimal/numeric type with two decimal places.
- Python code shall use `Decimal` for model/service price values.
- Binary floating-point values shall not be relied on for exact price storage.
- Extra decimal places, commas, symbols, `NaN`, infinity, negative, zero, and excessive values shall be rejected by future input validation and protected where possible at the database layer.

## 11. Timestamp rules

### TIME-001: UTC storage

- `created_at` and `updated_at` shall represent UTC time.
- They shall be generated by trusted application/database behaviour, not public form data.
- Future pages may convert UTC to a display timezone without changing the stored value.
- Sorting records with equal timestamps shall use the primary key as a deterministic second key.

### TIME-002: Update behaviour

- `created_at` shall not change when a row is edited.
- `updated_at` shall initially equal or closely follow creation time.
- `updated_at` shall change when editable model data is successfully modified.
- A failed/rolled-back update shall not produce a committed timestamp change.

## 12. Migration requirements

### MIG-001: Migration history

- Flask-Migrate/Alembic shall record schema history in a committed `migrations` directory.
- The initial migration shall create the `users` and `products` tables, indexes, foreign key, and approved constraints.
- Developers shall use migrations rather than calling `create_all()` as the normal long-term schema-management process.
- Migration files shall be reviewed before being applied.

### MIG-002: Upgrade from an empty database

- Running the documented upgrade command on an empty development database shall create the approved schema.
- Running the same upgrade command again shall report that the schema is current rather than duplicating tables.

### MIG-003: Downgrade and recovery

- The initial migration shall include a downgrade that removes the created tables in safe dependency order.
- Downgrade is a development learning/recovery tool, not a substitute for a production backup.
- Before any future destructive migration, the plan must include backup and data-preservation steps.

### MIG-004: SQLite and future PostgreSQL compatibility

- Constraint and indexing choices shall be reviewed for both SQLite and PostgreSQL behaviour.
- If case-insensitive uniqueness needs different implementation by database, the chosen strategy shall be documented and tested rather than assumed.

## 13. Seed-data requirements

### SEED-001: Explicit command

Sample data shall be created only by an explicit developer command. Importing the application or starting the server shall never seed or erase data automatically.

### SEED-002: Contents

The seed set shall contain at least:

- 3 demonstration users with unique normalized usernames/emails.
- 12 products distributed across several categories, conditions, statuses, prices, and sellers.
- At least one active product per seller.
- At least one sold product and one archived product for later filtering tests.
- Realistic but fictional data containing no real personal information.
- Password hashes only, never plain passwords in the database or command output.

### SEED-003: Repeatability

- Running the seed command twice shall not create duplicate users or products.
- The command may be idempotent or may safely refuse to run when seed records already exist.
- The chosen behaviour shall be documented and tested.

### SEED-004: Destructive safety

- The seed command shall not delete existing data.
- Any future reset command must be separate, clearly named, restricted to development/testing, and require explicit confirmation or an unmistakable testing flag.
- Production configuration shall refuse destructive development seed/reset behaviour.

## 14. Application-structure requirements

MM-002 may reorganize the application only as needed for database support while preserving MM-001 behaviour.

### STRUCT-001: Extensions

- Database and migration extension objects shall be created without immediately binding them to one global application.
- The application factory shall initialize them for each created application.
- Tests shall be able to create an isolated application with an isolated database.

### STRUCT-002: Model organization

- Models shall live in a clear module or package rather than inside route functions.
- Import organization shall avoid circular imports.
- Model constants or enums for category, condition, and status shall have one authoritative source.

### STRUCT-003: Existing MM-001 behaviour

After database integration:

- `/` shall still return the approved home page.
- `/health` shall still return exactly the approved public JSON fields.
- Missing routes shall still return the custom 404 page.
- Existing MM-001 tests shall remain Green.
- The application shall start even when the database currently contains no rows.

## 15. Developer interfaces

MM-002 shall document these developer capabilities, though exact command spelling will be finalized in the approved plan:

| Capability | Expected result |
|---|---|
| Apply migrations | Bring an empty or older database to the latest approved schema |
| Show current migration | Identify the schema revision currently applied |
| Create seed data | Add the approved fictional sample dataset safely |
| Open an interactive shell | Allow supervised inspection of users, products, and relationships |
| Run tests | Use only the isolated test database and preserve development data |

No public web route for creating or editing database records is required by MM-002.

## 16. Non-functional requirements

### NFR-DB-001: Beginner readability

- Model fields and relationships shall use descriptive names.
- Unfamiliar database concepts shall be explained in documentation.
- Clever abstractions shall not hide basic SQLAlchemy behaviour.

### NFR-DB-002: Portability

- Development shall work with SQLite.
- The design shall remain reasonable for future PostgreSQL use.
- Machine-specific absolute database paths shall not be committed.

### NFR-DB-003: Testability

- Tests shall create and destroy only temporary databases.
- Model tests shall not require a running HTTP server.
- Test outcomes shall not depend on execution order.

### NFR-DB-004: Data safety

- Database sessions shall be rolled back after failed writes.
- Seed behaviour shall not destroy user-created data.
- The database file and private configuration shall remain ignored by Git.

### NFR-DB-005: Performance foundation

- Primary keys, unique identity fields, `seller_id`, and fields needed for future common listing queries shall be indexed intentionally.
- MM-002 shall avoid premature complex optimization but document each created index and its reason.

## 17. Risk traceability

MM-002 must address these approved project-wide issues:

| Risk ID | MM-002 response |
|---|---|
| `X-DATA-001` | Constraints, transactions, rollback, and relationship tests |
| `X-MONEY-001` | Decimal price type, range, currency, boundary tests |
| `X-TIME-001` | UTC timestamp policy and deterministic sorting rule |
| `X-PRIV-001` | Safe model representations and no secret database output |
| `X-FAIL-001` | Useful configuration/migration failures and rollback |
| `X-TEST-001` | Temporary isolated test database |
| `X-SDD-001` | Requirement-to-test traceability before implementation |
| `W02-SCHEMA-001` | Required, unique, check, and foreign-key constraints |
| `W02-PRICE-002` | Exact price round trips and invalid-value rejection |
| `W02-DELETE-003` | Restrictive user deletion and deferred archival policy |
| `W02-MIGRATE-004` | Upgrade, repeat upgrade, downgrade, and compatibility checks |
| `W02-SEED-005` | Explicit, fictional, repeatable, non-destructive seed data |
| `W02-LOCK-006` | Short transactions and rollback; concurrency test planned where practical |

## 18. Acceptance scenarios

### AC-DB-001: Empty database migration

**Given** an empty development database location  
**When** the developer applies all migrations  
**Then** the `users` and `products` tables are created  
**And** their approved columns, indexes, constraints, and foreign key exist  
**And** the operation completes without manually creating tables.

### AC-DB-002: Valid user and products persist

**Given** a valid user  
**When** the user and two valid products are committed  
**And** a new database session queries them  
**Then** the user and products still exist  
**And** `user.products` returns both products  
**And** each `product.seller` returns the user.

### AC-DB-003: Invalid seller is rejected

**Given** no user with ID `999999` exists  
**When** code attempts to commit a product using that seller ID  
**Then** the database rejects the write  
**And** no product row is created  
**And** the session can be rolled back and safely reused.

### AC-DB-004: Duplicate identities are rejected

**Given** a stored normalized username and email  
**When** another row attempts to use an equivalent email or case-equivalent username  
**Then** the database rejects the duplicate according to the approved normalization strategy  
**And** the original user remains unchanged.

### AC-DB-005: Price is exact and bounded

**Given** a valid product price such as `10.10`  
**When** it is committed and retrieved in a new session  
**Then** the value remains exactly `10.10`  
**And** zero, negative, excessive, non-finite, or over-precision prices are rejected by the appropriate validation/constraint layer.

### AC-DB-006: Approved choices are enforced

**Given** the approved category, condition, currency, and status keys  
**When** valid keys are committed  
**Then** they persist  
**And** unsupported keys fail without creating a partial row.

### AC-DB-007: Restrictive user deletion

**Given** a user owns at least one product  
**When** code attempts to physically delete that user  
**Then** the database prevents orphaning or silently deleting the products  
**And** the transaction is rolled back safely.

### AC-DB-008: Seed data is safe and repeatable

**Given** a migrated empty development database  
**When** the approved seed command runs  
**Then** it creates at least 3 fictional users and 12 varied products  
**When** the command runs again  
**Then** it creates no duplicates and deletes no existing records.

### AC-DB-009: Tests are isolated

**Given** a development database containing a recognizable record  
**When** the MM-002 pytest suite runs  
**Then** tests use a different temporary database  
**And** the recognizable development record remains unchanged.

### AC-DB-010: Migration downgrade and re-upgrade

**Given** the initial migration is applied to disposable data  
**When** the migration is downgraded and then upgraded again  
**Then** table removal/creation follows safe dependency order  
**And** the final schema matches the approved latest schema.

### AC-DB-011: MM-001 regression protection

**Given** database integration is complete  
**When** the entire test suite runs  
**Then** all existing MM-001 tests remain Green  
**And** the public home, health, static file, and 404 contracts remain unchanged.

### AC-DB-012: No automatic seed side effect

**Given** a migrated database with no rows  
**When** the Flask application starts normally  
**Then** it does not automatically add, delete, or modify users or products.

## 19. Proposed decisions requiring approval

Approving MM-002 approves these design choices:

1. SQLite for local development and isolated tests; future PostgreSQL configuration remains possible.
2. SQLAlchemy through Flask-SQLAlchemy and migrations through Flask-Migrate/Alembic.
3. A 30-character username, 254-character email, 500-character bio, 120-character title, and 5,000-character description limit.
4. `USD` as the one MVP currency, stored explicitly.
5. Decimal prices from `0.01` through `9,999,999.99`.
6. The seven category keys, four condition keys, and three status keys listed above.
7. UTC timestamp storage.
8. Restricting physical deletion of users who own products.
9. At least 3 fictional users and 12 products in the demonstration seed.
10. No user-facing database CRUD pages during MM-002.

Any of these can be revised now while this document is Draft.

## 20. Completion and approval rule

MM-002 moved from **Draft** to **Approved** when the student explicitly approved it on 2026-10-25.

After approval, work must continue in this exact order:

1. Create an implementation and test plan mapped to MM-002 requirements, acceptance scenarios, and risk IDs.
2. Review and approve that plan.
3. Write the planned pytest tests without database implementation.
4. Validate test syntax and discovery, then record the expected Red failures.
5. Implement only the approved database foundation, migrations, seed command, and documentation.
6. Turn the new tests Green while keeping every MM-001 test Green.
7. Record migration, isolation, seed-safety, and regression evidence.

No MM-002 plan, test code, dependency change, migration, model, seed command, or application integration is authorized while this specification remains Draft.

