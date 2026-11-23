# Local demo-image utility

Scope: a data-preparation helper for the existing MM-002 fictional seed data,
MM-005 image format/storage contract, and MM-016 local demonstration. Requested
directly by the student on 2026-10-25. No application feature, database schema,
visibility rule, earlier specification, or historical evidence is replaced.

## Implementation and acceptance checks

1. Provide one self-contained Python script, using Pillow and the standard
   library. It draws twelve product-specific, clearly labelled demo illustrations
   offline. These are not photographs or evidence of an actual item's condition.
2. Find the project from the script's location, not the terminal's current folder.
   Open only the existing local `instance/market-mirror.sqlite` database. Refuse
   production mode, missing databases, unexpected schema, and unsafe redirected
   paths. Never follow a DATABASE_URL into another database.
3. Match the exact seed seller username **and** email, product title, and original
   fictional description. Leave student-created/modified listings alone. Refuse
   ambiguous duplicate matches. Never create users, listings, or migrations.
4. Preserve any existing image reference, even if the file is missing. A second
   run must be a no-op. Do not change price, availability, text, or ownership.
5. Before updating anything, take a uniquely named SQLite online backup. Store
   it privately under instance/backups. A failed backup prevents all updates.
6. Use a short SQLite write transaction to prevent competing database writes.
   Save fresh RGB JPEGs with random 32-hex filenames in instance/uploads, as
   required by the application's existing protected image route. Flush files
   before committing references. Advance the optimistic-lock version and UTC
   modification timestamp so stale browser forms cannot overwrite the update.
7. Roll back database changes on failure and delete only this invocation's new
   files; preserve existing files and the backup. Abrupt process/OS termination
   can leave unreferenced files: use the existing read-only image reconciliation
   command to inspect these, not automatic sweeping deletion.
8. Print attached/skipped counts, backup location, and a reminder to refresh the
   browser. Nothing is published and archived items remain private.

## Test plan

Use disposable test-owned databases, seeded through the existing CLI. Validate
all twelve distinct deterministic illustrations, supported dimensions/format,
metadata absence, successful attachment, backup integrity and prior contents,
unchanged unrelated fields/accounts, optimistic-lock increments, public/archived
media access, rerun idempotency, existing/missing photo-reference preservation,
modified identity/text/owner exclusion, duplicate refusal, missing database and
production refusal, rendering failure, and database-update failure cleanup.
Include unsafe-folder, backup failure, and real command-line invocation checks.
Review an image contact sheet visually. Record actual Red and Green results.

The user will run the final command on their real database; development and test
runs must not attach images to that database on their behalf in this turn.
