# Local operation and future deployment runbook

## Current decision

The user selected **keep it local; prepare deployment instructions**. Nothing has
been published and no paid resource created. The normal local entry point is:

```powershell
& .\scripts\local.ps1 serve
```

This binds Waitress to 127.0.0.1:5000. Do not change this to 0.0.0.0 merely to share
a demo. Public use requires the separate release checks below. The app has no
email verification/recovery or dedicated reporting/moderation UI. Use fake class
data, not real sensitive conversations. OneDrive may synchronize the workspace,
including ignored runtime files: Git ignore does not prevent cloud synchronization.

## Runtime files and secrets

| Location | Meaning | Recovery |
|---|---|---|
| `instance/market-mirror.sqlite` | Local accounts, listings and relations | Database backup |
| `instance/uploads/` | Normalized product photos | Matching media backup |
| `instance/ai/` | Model/index artifacts and evaluation files | Rebuild with train/index |
| `instance/local-secret.txt` | Local cookie-signing secret | Protect separately; rotation logs everyone out |
| `migrations/` | Versioned schema history | Source control/archive |

Only the local helper reads `local-secret.txt`. Direct Flask/Waitress commands
require SECRET_KEY in the environment. For MM-024, Market Mirror automatically
loads an optional project-root `.env` without overriding existing process
variables. `.env.example` contains placeholders only; `.env` is ignored by Git
but may still be synchronized by OneDrive. Never paste credentials into
screenshots, reports, shell arguments, logs, Git or chat. Do not put a model
uploaded by someone else into AI_FOLDER: joblib is executable serialization,
not inert data.

The exact dependency lock is verified on CPython 3.12/Windows. It is version-pinned,
not hash-pinned. Linux wheel compatibility and image digest pinning still require
rehearsal before a hosted release. Install from trusted package indexes and review
dependency updates rather than silently mixing model/library versions.

## Health, errors and logs

`GET /health` returns the original fixed liveness JSON. `GET /ready` returns 200
only when the users table can be queried; a database error gives 503 and generic
JSON. After an outage, retry readiness and a read-only catalogue request.
Readiness does not prove that every migration, media file or optional model exists.
Run `scripts/local.ps1 check` as part of each schema release.

Logs contain generated request ID, response status and elapsed milliseconds. Do
not add query strings, form bodies, passwords, messages or raw exception text to
logs. X-Request-ID is returned in the response for troubleshooting. Development
debug mode remains off by default. A future reverse proxy must avoid sensitive
URL/query logging too. Keep routine logs only as long as needed for this project;
the suggested operational rotation is seven days, to be configured on a host.

## Local backup and restore practice

1. Stop the local server and all CLI writers with Ctrl+C. This is important for
   a consistent database/photo snapshot, not just to make copying convenient.
2. Create a **new, empty** dated backup folder outside `instance`. Copy the entire
   `instance` directory into it, including any SQLite `-wal` and `-shm` sidecars.
   Keep source/migrations and the dependency lock with the release. Never overwrite
   the last known good backup. Treat the copy as private: it includes account data
   and possibly the session-signing secret.
3. Restore only into a **new, empty rehearsal directory**. Do not copy over your
   live database to test a restore. Point an isolated application at its copied
   database/uploads and check SQLite integrity and foreign keys, row counts, exact
   prices, visible photos and a test conversation. Use disposable accounts.
4. Compare schema revision with the expected release. Do not run `db downgrade`
   on your only copy. A schema downgrade can delete data.
5. Record the backup date, release version, row counts and restore outcome. Keep
   copies encrypted/restricted. For a classroom retention policy, keep seven daily
   and four weekly backups; remove expired copies through a deliberate verified
   operator action, not an unattended broad deletion command.

Automated rehearsal: `tests/test_hardening.py::test_sqlite_backup_restores_rows_prices_and_foreign_keys`
uses SQLite's backup API to restore into a fresh test-owned file and checks
integrity, relationships and integer-cent money. This verifies a local database
roundtrip, not an end-to-end production database/media disaster-recovery process.

## Routine maintenance

Run the following manually at a planned maintenance time; no scheduler was
installed as part of this work:

```powershell
& .\scripts\local.ps1 purge
& .\scripts\local.ps1 images
& .\scripts\local.ps1 index
```

Purge removes consented events older than 90 days and expired throttle counters.
Opt-out removes the user's events immediately, and recommendations check current
consent without a persistent personalized cache. Recommendation reads also exclude
events older than 90 days even if the purge has not yet run.

The image report counts missing references and orphan UUID-named JPEGs. Default
mode deletes nothing. For intentional orphan deletion, **stop web/CLI writers
first**, review a backup and the report, then use the underlying Flask command
`maintenance images --delete-orphans` with the same local environment settings.
Stopping writers avoids deleting an upload between its file write and DB commit.
The tool ignores unrelated filenames and symlinks. A crash may leave `.pending`
files; inspect their age and origin manually during downtime before removing
anything. Do not use wildcard recursive deletion against uploads.

### Verified account requests

There is no public admin endpoint. An operator first verifies the requester
outside the application and agrees on scope. Never anonymize an account merely
because an unauthenticated person knows its username. After verification, backup
and record a minimal operator ticket with the numeric ID and purpose, without
copying private conversation text. The command is:

```text
python -m flask --app app:create_app maintenance anonymize USER_ID --confirm-verified-request
```

This disables login, replaces username/email/password hash, clears bio/consent,
deletes saves/events belonging to the user, replaces that user's message bodies,
and archives their listings. It retains relational IDs and the other participant's
messages. **It is not complete erasure of every possible personal datum.** Review
listing titles/descriptions/images and quoted content from other people separately;
handle any further changes under a verified scope. Backups retain old data until
their retention expires; reapply verified requests after restoring an older backup.

For reported abuse in this local project: record product/conversation ID, restrict
access to evidence, verify the report with the instructor/operator, then decide
whether to archive an owned listing or disable an account through an explicitly
authorized operation. No automated content decision is made by the AI features.
Before public launch, establish a real reporting channel, response ownership and
appeal procedure; these are not currently implemented product features.

## Optional future PostgreSQL/container rehearsal — NOT EXECUTED

Docker and PostgreSQL executables were unavailable here. `Dockerfile` and
`compose.yaml` are preparation, **not a verified deployment**. Use a disposable
environment first. Never point tests at a production database.

1. Install Docker on the intended host and review the image/lock versions there.
2. Supply POSTGRES_PASSWORD, SECRET_KEY, DATABASE_URL and TRUSTED_HOSTS through
   an operator-controlled environment/secret manager. Use
   `postgresql+psycopg://marketmirror:<URL-encoded-password>@db:5432/marketmirror`.
   Supply the same database password to the DB service. Do not commit it.
3. Run `docker compose build`, then `docker compose up -d db`.
4. Run `docker compose run --rm web python -m flask --app app:create_app db upgrade`
   followed by `db current` and `db check` using the same command prefix. Migrations
   are explicit release steps; web workers do not auto-migrate.
5. Start `docker compose up -d web`. The host port is loopback-only 8080. Put a
   separately configured HTTPS reverse proxy in front. Secure cookies intentionally
   prevent a production login over plain HTTP. No TLS proxy is silently installed.
6. Keep PostgreSQL internal and media/database volumes persistent. Confirm the
   unprivileged container user can write `/data`. Restart the container and verify
   accounts/photos persist. Rebuild trusted AI artifacts in the target environment
   with `ai train` and `ai index`; missing AI does not block core use.
7. Configure exact trusted hosts. Do not enable generic forwarded-header trust:
   the current app trusts no proxy headers. Behind a proxy, address throttles may
   share one proxy address until a reviewed exact-hop trusted-proxy configuration
   is added and tested. Never accept arbitrary X-Forwarded-For from clients.
8. Execute the PostgreSQL equivalents of money/FK/uniqueness/migration/concurrent
   write tests against a **dedicated disposable DB**, including upgrade with
   populated foundation rows. The SQLite pytest suite is not this verification.
9. Check HTTPS cookies, host rejection, CSRF, redirects, request limits, restart
   behaviour, safe logs, disk exhaustion and restoration. Only then evaluate public
   release authorization. Email recovery/moderation omissions remain release risks.

### PostgreSQL backup/restore outline

During a maintenance window, stop web writers. Inside the DB container run
`pg_dump -U marketmirror -d marketmirror -Fc -f /tmp/market-mirror.dump`, then
`docker compose cp db:/tmp/market-mirror.dump` to an explicit new backup file.
Avoid PowerShell binary stdout redirection; use pg_dump's output file and copy.
Back up the media volume during the same window. Do not run `docker compose down -v`:
that removes persistent volumes.

For rehearsal, create a separate empty restore DB/container, copy the dump there,
run `pg_restore --no-owner --dbname=<rehearsal_db> <dump_file>`, and compare revision,
counts, sampled prices and foreign keys. Restore matching media, verify access,
and reapply pending deletion requests. This procedure is unverified until it is
actually executed on the chosen PostgreSQL host and recorded.

### Rollback

Retain the previous application source/lock, a tested DB backup and matching media
before a release. If code fails with a compatible schema, revert the application
release through source control. If the migration is incompatible, stop writes and
restore into a new database first; validate it before switching connection settings.
Do not assume a downgrade is data-preserving. Record any writes that occurred
after backup so data loss is understood. This project has no Git commit history yet;
configure your identity and create reviewed commits before relying on Git rollback.
