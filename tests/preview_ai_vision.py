"""Loopback-only MM-023 browser fixture; never reads the real database.

Run with: python -m tests.preview_ai_vision
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

import base64
from io import BytesIO
from pathlib import Path
import tempfile

from flask import Response, jsonify, request
from PIL import Image, ImageDraw
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User


PASSWORD = "Vision fixture passphrase!"


class FixtureAnalyzer:
    def __init__(self):
        self.calls = []

    def __call__(self, clean_jpeg):
        self.calls.append(clean_jpeg)
        return {
            "title": "Silver laptop computer",
            "category": "sports_outdoors",
            "title_confidence": 0.91,
            "category_confidence": 0.94,
            "abstain_reason": "",
        }


def laptop_picture():
    stream = BytesIO()
    image = Image.new("RGB", (720, 480), "#e7edf1")
    drawing = ImageDraw.Draw(image)
    drawing.rounded_rectangle((150, 75, 570, 350), radius=18, fill="#50677a", outline="#263847", width=8)
    drawing.rectangle((176, 101, 544, 324), fill="#9bd5df")
    drawing.polygon(((105, 360), (615, 360), (670, 415), (50, 415)), fill="#adb8c1", outline="#52616d")
    drawing.rectangle((315, 371, 405, 384), fill="#7d8991")
    image.save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode("ascii")


def fixture_script():
    encoded = laptop_picture()
    return f"""
(() => {{
  document.documentElement.dataset.mm023FixtureReady = 'true';
  const raw = atob('{encoded}');
  const bytes = Uint8Array.from(raw, character => character.charCodeAt(0));
  const button = document.querySelector('#fixture-laptop-photo');
  button?.addEventListener('click', () => {{
    const input = document.querySelector('#image');
    const transfer = new DataTransfer();
    transfer.items.add(new File([bytes], 'fixture-laptop.png', {{type: 'image/png'}}));
    input.files = transfer.files;
    input.dispatchEvent(new Event('change', {{bubbles: true}}));
  }});
}})();
"""


def fixture_panel():
    return """
<section id="mm023-fixtures" class="panel" aria-label="MM-023 temporary controls">
  <h2>Temporary AI vision fixture</h2>
  <p>This isolated page uses a generated laptop picture and a fake Gemini model. It never calls Google or OpenAI.</p>
  <button id="fixture-laptop-photo" type="button">Select fixture laptop photo</button>
</section>
<script src="/fixture-mm023.js"></script>
"""


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm023-browser-", dir=root))
    analyzer = FixtureAnalyzer()
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'vision.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(fixture_dir / "uploads"),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
        "VISION_AI_ENABLED": True,
        "VISION_AI_PROVIDER": "gemini",
        "VISION_AI_MODEL": "gemini-3.5-flash-lite",
        "VISION_AI_TIMEOUT_SECONDS": 12,
        "VISION_AI_ANALYZER": analyzer,
    })
    with application.app_context():
        db.create_all()
        db.session.add(User(
            username="vision-seller",
            email="seller@vision-fixture.test",
            password_hash=generate_password_hash(PASSWORD),
        ))
        db.session.commit()

    @application.get("/fixture-mm023.js")
    def fixture_javascript():
        return Response(fixture_script(), mimetype="application/javascript")

    @application.get("/fixture-mm023-state")
    def fixture_state():
        dimensions = None
        if analyzer.calls:
            with Image.open(BytesIO(analyzer.calls[-1])) as image:
                dimensions = list(image.size)
        return jsonify(calls=len(analyzer.calls), dimensions=dimensions)

    @application.after_request
    def controlled_fixture_html(response):
        if response.mimetype != "text/html":
            return response
        html = response.get_data(as_text=True)
        if request.args.get("fixture_no_script") == "1":
            html = html.replace('<script src="/static/js/market.js" defer></script>', "")
        elif request.path == "/listings/new" and response.status_code in {200, 400}:
            html = html.replace("</main>", fixture_panel() + "</main>")
        response.set_data(html)
        return response

    return application


if __name__ == "__main__":
    from waitress import serve
    print("MM-023 fixture: http://127.0.0.1:5023/auth/login?next=/listings/new", flush=True)
    print("Login: seller@vision-fixture.test / Vision fixture passphrase!", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5023, threads=8)
