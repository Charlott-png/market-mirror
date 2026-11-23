"""Draw and attach fictional demo illustrations. Requires only Pillow + Python.

Run with the project's .venv Python. No API key, downloads, or input files needed.
The script finds its own project folder, backs up the existing SQLite database,
and fills empty photo slots on the original seed listings only. Running it again
is safe: existing references (even broken ones) and other listings are preserved.

Pictures live in instance/uploads; the database stores their random filenames,
not the image bytes. The existing Flask media route controls who can see them.
This is deliberately an illustration generator, not an AI model or photo tool.
"""

from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# These identities/titles mirror app.commands' fictional seed fixtures. No real
# user account is selected merely because its listing has the same title.
DEMO_SELLERS = (
    ("demo-alex", "alex@example.test"),
    ("demo-blair", "blair@example.test"),
    ("demo-casey", "casey@example.test"),
)
DEMO_TITLES = (
    "Study desk lamp", "Python learning book", "Wireless keyboard", "Canvas tote bag",
    "Basketball", "Board game collection", "Portable speaker", "Ceramic plant pot",
    "Winter jacket", "Adventure novel set", "Camping lantern", "Craft supply box",
)


class Canvas:
    """Draw at four times logical size, then shrink for smooth edges."""

    scale = 4

    def __init__(self):
        self.image = Image.new("RGB", (2400, 1800), "#f7f5ef")
        self.pen = ImageDraw.Draw(self.image)

    def box(self, xy, fill, radius=0, outline=None, width=2):
        self.pen.rounded_rectangle(tuple(v * self.scale for v in xy),
            radius=radius * self.scale, fill=fill, outline=outline, width=width * self.scale)

    def oval(self, xy, fill, outline=None, width=2):
        self.pen.ellipse(tuple(v * self.scale for v in xy), fill=fill,
                         outline=outline, width=width * self.scale)

    def line(self, points, fill, width=2):
        self.pen.line([(x * self.scale, y * self.scale) for x, y in points],
                      fill=fill, width=width * self.scale, joint="curve")

    def polygon(self, points, fill):
        self.pen.polygon([(x * self.scale, y * self.scale) for x, y in points], fill=fill)

    def text(self, xy, text, size, fill="#243c3c", bold=False):
        # Windows uses Segoe UI. Pillow's bundled default keeps this runnable on
        # other systems as well, without downloading a font or guessing folders.
        font_name = "segoeuib.ttf" if bold else "segoeui.ttf"
        try:
            font = ImageFont.truetype(font_name, size * self.scale)
        except OSError:
            font = ImageFont.load_default(size=size * self.scale)
        self.pen.text((xy[0] * self.scale, xy[1] * self.scale), text, font=font, fill=fill)


def draw_product(title):
    """Return one original 1200x900 RGB illustration for a known demo product."""
    if title not in DEMO_TITLES:
        raise ValueError("Unknown demo product; refusing to invent a matching image.")
    c = Canvas()
    ink, teal, light = "#243c3c", "#347d78", "#edf5ed"
    c.text((32, 22), "MARKET MIRROR", 13, bold=True)
    c.box((443, 23, 568, 47), "#dce9e1", radius=12)
    c.text((455, 27), "DEMO ARTWORK", 10, bold=True)
    c.oval((174, 83, 426, 335), "#e7eee4")
    c.oval((171, 321, 429, 344), "#d7dfd6")

    if title == "Study desk lamp":
        c.oval((225, 307, 365, 334), teal)
        c.line([(295, 315), (280, 228), (340, 159)], ink, 12)
        c.oval((268, 216, 292, 240), "#e4ac56", ink)
        c.line([(337, 160), (310, 139)], ink, 10)
        c.polygon([(257, 139), (309, 114), (353, 171), (259, 202)], teal)
        c.line([(260, 200), (353, 171)], "#edc16f", 8)
        c.oval((264, 146, 275, 157), "#73aaa0")
    elif title == "Python learning book":
        c.box((214, 120, 384, 329), ink, radius=9)
        c.box((211, 108, 375, 320), "#337b9c", radius=9)
        c.box((224, 312, 374, 325), "#fff9e8", radius=3)
        c.line([(230, 110), (230, 309)], "#22556f", 3)
        c.text((246, 137), "PYTHON", 25, "white", True)
        c.text((246, 174), "LEARNING", 13, "#d9ecf3")
        c.text((251, 212), "{  }", 49, "#f4c66b", True)
        c.text((247, 284), "CODE / CREATE", 10, "white")
    elif title == "Wireless keyboard":
        c.box((127, 185, 477, 303), ink, radius=17)
        c.box((122, 177, 472, 294), "#a2b6b3", radius=17)
        for row in range(4):
            for col in range(12):
                x, y = 138 + col * 26, 190 + row * 20
                c.box((x, y, x + 21, y + 15), light, radius=3)
        c.box((214, 270, 357, 283), "#f6fbf5", radius=4)
        c.oval((449, 181, 453, 185), teal)
        c.line([(279, 138), (288, 133), (308, 133), (317, 138)], teal, 3)
        c.line([(286, 147), (293, 143), (303, 143), (310, 147)], teal, 3)
        c.oval((296, 152, 301, 157), teal)
    elif title == "Canvas tote bag":
        c.oval((241, 104, 359, 238), None, "#a58865", 12)
        c.polygon([(210, 180), (390, 180), (374, 328), (225, 328)], "#d8bf94")
        c.box((224, 177, 377, 189), "#f2dfbc", radius=3)
        c.line([(238, 192), (248, 315), (357, 315), (368, 192)], "#bc9c6d", 2)
        c.line([(299, 275), (299, 220)], teal, 4)
        c.oval((268, 226, 298, 248), teal)
        c.oval((301, 210, 331, 232), teal)
        c.text((265, 289), "REUSE", 16, teal, True)
    elif title == "Basketball":
        c.oval((196, 113, 405, 322), "#dd8548", ink, 4)
        c.oval((212, 126, 382, 296), None, "#ef9c5a", 3)
        c.line([(197, 216), (403, 216)], ink, 4)
        c.line([(300, 114), (300, 321)], ink, 4)
        c.line([(231, 139), (254, 163), (266, 196), (266, 239), (254, 274), (231, 297)], ink, 4)
        c.line([(367, 139), (343, 163), (331, 196), (331, 239), (343, 274), (367, 297)], ink, 4)
    elif title == "Board game collection":
        c.box((185, 265, 416, 326), "#d39c51", radius=6)
        c.box((172, 206, 403, 267), "#cf7967", radius=6)
        c.box((190, 142, 420, 208), teal, radius=6)
        c.text((211, 155), "GAME NIGHT", 22, "white", True)
        c.text((194, 222), "PLAY TOGETHER", 17, "white", True)
        c.text((205, 282), "STRATEGY CLUB", 17, ink, True)
        c.box((371, 103, 413, 145), "#fff9e8", radius=7, outline=ink)
        for x, y in [(382, 114), (402, 134), (392, 124)]:
            c.oval((x - 3, y - 3, x + 3, y + 3), ink)
    elif title == "Portable speaker":
        c.box((209, 168, 394, 322), ink, radius=28)
        c.box((217, 174, 386, 313), "#426663", radius=23)
        for y in range(188, 301, 9):
            for x in range(230, 377, 9):
                c.oval((x, y, x + 3, y + 3), "#7fa29a")
        c.line([(233, 169), (244, 142), (359, 142), (371, 169)], ink, 10)
        c.box((270, 162, 334, 177), "#bad1c5", radius=7)
        c.line([(283, 166), (283, 173)], ink, 2)
        c.line([(279, 169), (287, 169)], ink, 2)
        c.line([(313, 169), (321, 169)], ink, 2)
    elif title == "Ceramic plant pot":
        c.polygon([(208, 177), (390, 177), (364, 326), (235, 326)], "#c9866b")
        c.oval((235, 311, 364, 338), "#c9866b")
        c.oval((202, 151, 397, 207), "#e2ac8a")
        c.oval((216, 164, 383, 194), "#7c594a")
        c.oval((224, 173, 375, 194), "#a2755d")
        c.line([(239, 213), (252, 301)], "#e5b69a", 6)
        c.line([(363, 218), (352, 301)], "#ab6953", 3)
    elif title == "Winter jacket":
        c.polygon([(249, 128), (213, 150), (162, 257), (205, 278), (237, 218),
                   (234, 327), (367, 327), (364, 218), (396, 278), (439, 257),
                   (388, 150), (351, 128)], "#467378")
        c.box((253, 105, 348, 157), "#294e55", radius=20)
        c.polygon([(267, 111), (300, 140), (334, 111)], "#b4cbc3")
        for y in (175, 209, 243, 277, 312):
            c.line([(240, y), (360, y)], "#669095", 3)
        c.line([(300, 144), (300, 326)], "#ead9b4", 4)
        c.box((272, 263, 284, 287), "#294e55", radius=3)
        c.box((315, 263, 327, 287), "#294e55", radius=3)
    elif title == "Adventure novel set":
        for x, top, color, word in [(191, 133, "#ba6b53", "EXPLORE"),
                                    (266, 114, "#347d78", "WANDER"),
                                    (341, 143, "#c59649", "DISCOVER")]:
            c.box((x, top, x + 69, 326), ink, radius=5)
            c.box((x, top, x + 63, 320), color, radius=4)
            c.line([(x + 9, top + 7), (x + 9, 312)], "#ffffff", 1)
            c.polygon([(x + 16, 240), (x + 35, 203), (x + 58, 240)], "#f1e9cc")
            c.text((x + 13, top + 23), word, 7, "white", True)
            c.line([(x + 19, 280), (x + 50, 280)], "#f1e9cc", 2)
    elif title == "Camping lantern":
        c.oval((255, 92, 346, 201), None, ink, 7)
        c.box((241, 172, 362, 307), "#e7c470", radius=18)
        c.box((259, 186, 343, 292), "#fff4c8", radius=14)
        c.box((232, 154, 370, 182), teal, radius=10)
        c.box((232, 300, 370, 328), teal, radius=10)
        c.line([(253, 181), (253, 301)], ink, 6)
        c.line([(350, 181), (350, 301)], ink, 6)
        c.box((287, 306, 315, 320), "#d9c288", radius=5)
        c.line([(207, 220), (184, 220)], "#dab263", 3)
        c.line([(393, 220), (416, 220)], "#dab263", 3)
    else:  # Craft supply box
        for x, color, lean in [(224, "#c55d54", -10), (244, "#e0ac54", -3),
                                (265, "#518d83", 6), (287, "#547a9d", 12)]:
            c.line([(x, 255), (x + lean, 140)], color, 10)
            c.polygon([(x + lean - 5, 139), (x + lean + 5, 139), (x + lean, 124)], "#ba956d")
        c.line([(331, 244), (369, 139)], ink, 6)
        c.line([(355, 244), (329, 140)], ink, 6)
        c.oval((313, 207, 343, 250), None, "#c96f57", 6)
        c.oval((346, 207, 376, 250), None, "#c96f57", 6)
        c.box((195, 241, 410, 328), "#bf9b6f", radius=7)
        c.box((184, 231, 420, 249), "#e0c59c", radius=4)
        c.box((266, 269, 347, 306), "#f9eed8", radius=3)
        c.text((279, 279), "CREATE", 12, ink, True)

    c.line([(32, 364), (568, 364)], "#d8dfd7", 1)
    c.text((32, 377), title, 24, bold=True)
    c.text((33, 418), "FICTIONAL LISTING  /  ILLUSTRATION, NOT A PRODUCT PHOTO", 10, "#5f716b")
    return c.image.resize((1200, 900), Image.Resampling.LANCZOS)


def safe_child(parent, name):
    """Do not let a symbolic link/junction redirect private output elsewhere."""
    child = parent / name
    if child.is_symlink() or child.resolve() != parent.resolve() / name:
        raise RuntimeError(f"Unsafe redirected path: {name}. No changes made.")
    return child


def backup_database(database, backup_folder):
    """SQLite's backup API includes committed WAL data, unlike copying a file."""
    backup_folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_folder / f"before-demo-images-{stamp}-{uuid.uuid4().hex}.sqlite"
    # Exclusive creation guarantees an existing backup cannot be overwritten.
    with destination.open("xb"):
        pass
    deadline = time.monotonic() + 15

    def check_timeout(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError("Database backup took too long; stop the app and retry.")

    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target, pages=128, progress=check_timeout)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed; no images were attached.")
    except BaseException:
        destination.unlink(missing_ok=True)  # Only this invocation's incomplete backup.
        raise
    return destination


def attach_demo_images(project_root=PROJECT_ROOT):
    """Back up, generate, and attach as one all-or-nothing database transaction."""
    if os.environ.get("APP_ENV", "").strip().lower() == "production":
        raise RuntimeError("Demo image generation is disabled in production.")
    root = Path(project_root).resolve()
    instance = safe_child(root, "instance")
    database = safe_child(instance, "market-mirror.sqlite")
    uploads = safe_child(instance, "uploads")
    backups = safe_child(instance, "backups")
    if not database.is_file():
        raise RuntimeError("Local database not found. Set up and seed Market Mirror first.")

    # mode=rw is intentional: SQLite must never create an empty wrong database.
    with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True,
                                 timeout=5, isolation_level=None)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")  # Other writers wait until commit/rollback.
        created = []
        try:
            # Also require the version/timestamp columns before creating any files.
            products = connection.execute("""
                SELECT p.id, p.title, p.description, p.image_filename, p.version,
                       p.updated_at, u.username, u.email
                FROM products p JOIN users u ON p.seller_id = u.id
                WHERE u.username IN (?, ?, ?) ORDER BY p.id
                """, tuple(user[0] for user in DEMO_SELLERS)).fetchall()
            expected = {(DEMO_SELLERS[index // 4][0], DEMO_SELLERS[index // 4][1], title)
                        for index, title in enumerate(DEMO_TITLES)}
            matches = defaultdict(list)
            for product in products:
                key = (product["username"], product["email"], product["title"])
                description = f"Fictional demonstration listing: {product['title']}. For project practice only."
                if key in expected and product["description"] == description:
                    matches[key].append(product)
            if any(len(group) > 1 for group in matches.values()):
                raise RuntimeError("Duplicate demo listings found; resolve the ambiguity before retrying.")
            if not matches:
                raise RuntimeError("No unchanged original demo listings found. No data was changed.")
            selected = [group[0] for group in matches.values()]
            pending = [row for row in selected if row["image_filename"] is None]
            skipped = len(selected) - len(pending)
            if not pending:
                connection.rollback()
                return {"attached": 0, "skipped": skipped, "backup": None}

            # Separate read connection can back up while this connection reserves
            # the write lock. No writes have occurred yet, so it captures the old state.
            backup = backup_database(database, backups)
            uploads.mkdir(parents=True, exist_ok=True)
            for product in pending:
                illustration = draw_product(product["title"])
                filename = uuid.uuid4().hex + ".jpg"
                path = uploads / filename
                with path.open("xb") as stream:
                    created.append(path)
                    illustration.save(stream, format="JPEG", quality=90, optimize=True)
                    stream.flush()
                    os.fsync(stream.fileno())
                # Versions invalidate stale listing-edit forms. UTC uses the
                # same storage format as the application's SQLAlchemy adapter.
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                result = connection.execute("""
                    UPDATE products SET image_filename=?, version=version+1, updated_at=?
                    WHERE id=? AND version=? AND image_filename IS NULL
                    """, (filename, now, product["id"], product["version"]))
                if result.rowcount != 1:
                    raise RuntimeError("A listing changed unexpectedly; no attachments were saved.")
            connection.commit()
        except BaseException:
            connection.rollback()
            for path in created:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    print(f"Cleanup needed for unreferenced generated file: {path}", file=sys.stderr)
            raise
        return {"attached": len(pending), "skipped": skipped, "backup": backup}


def main():
    try:
        report = attach_demo_images()
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as error:
        print(f"Could not attach demo images: {error}", file=sys.stderr)
        print("No new image attachments were committed. If the database is locked, stop the app and retry.",
              file=sys.stderr)
        return 1
    print(f"Attached {report['attached']} demo illustrations; preserved {report['skipped']} existing photo references.")
    if report["backup"]:
        print(f"Database backup: {report['backup']}")
    print("Your own listings were left alone. Refresh Market Mirror to see the images.")
    print("Sold/archived listings keep their existing visibility rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
