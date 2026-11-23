# Generate and attach demo illustrations

The script is already written. Paste these commands into PowerShell:

```powershell
Set-Location "C:\Users\Amaal\OneDrive\Desktop\Ai folder\market-mirror"
.\.venv\Scripts\python.exe -m pip install "Pillow==12.3.0"
.\.venv\Scripts\python.exe .\scripts\generate_demo_images.py
```

Then refresh the marketplace in your browser. If it reports that the database is
locked, stop the local server with Ctrl+C, run the image command again, and restart
the server with `& .\scripts\local.ps1 serve`.

## What the script does

**Pillow** is a Python drawing library. The script uses shapes, colours, and text
to draw a different illustration for each of the twelve original demo products.
It works offline without an API key, extra artwork files, or paid image service.
These are labelled fictional illustrations, not real product photos or AI output.

Think of the database as an index card: it stores the picture's filename, while
the actual JPEG lives in the uploads folder. The existing application uses that
filename to find and display the picture. The script creates all needed folders
and fills these references automatically; you do not need to arrange files.

Before changing anything, it saves a uniquely named database backup. It updates
only original fictional listings identified by their seller, title, and original
description. Your own listings and existing photo references are left alone.
Edited demo descriptions, changed ownership, and ambiguous duplicates are not
silently treated as untouched seed records. It does not create missing listings.

A **transaction** groups the database updates: either all image references are
saved, or none are. If a handled error occurs, the script also removes its new
image files. If the computer loses power or the process is forcibly killed,
unreferenced new files may remain; the existing image reconciliation command can
report these. No existing photos are swept up or deleted automatically.

Each changed listing's **version number** goes up. This prevents a browser edit
form opened before the script ran from accidentally overwriting newer changes.
Refresh any open edit form after running the script.

Running the command a second time skips existing image references. Sold and
archived products keep their status and visibility; adding artwork does not
publish them. An existing broken image reference is also skipped, not replaced.

The helper intentionally targets only this project's default local SQLite
database and upload folder, regardless of DATABASE_URL or UPLOAD_FOLDER settings.
Production mode is refused. It is not a production import/migration tool.

Backups live in `instance/backups/` and should be kept private like the original
database. The script prints the exact backup location when it finishes. A backup
contains database rows, not copies of existing uploaded photos; those photos are
not modified by this helper. Do not replace a live database casually, because
restoring a backup also rolls back other changes made since it was taken.
