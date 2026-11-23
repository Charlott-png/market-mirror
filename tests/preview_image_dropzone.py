"""Loopback-only MM-022 browser fixture; never reads the real database.

Run with: python -m tests.preview_image_dropzone
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile

from flask import Response, request
from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User


PASSWORD = "Image dropzone demo passphrase!"


def encoded_picture(image_format, color, size):
    stream = BytesIO()
    mode = "RGBA" if image_format == "PNG" else "RGB"
    Image.new(mode, size, color).save(stream, format=image_format)
    return base64.b64encode(stream.getvalue()).decode("ascii")


def fixture_javascript():
    files = {
        "jpeg": [{"name": "landscape-demo.jpg", "type": "image/jpeg",
                  "base64": encoded_picture("JPEG", "#24748a", (600, 300))}],
        "png": [{"name": "portrait-demo.png", "type": "image/png",
                 "base64": encoded_picture("PNG", (130, 70, 190, 120), (240, 480))}],
        "unsafe-name": [{"name": "<img src=x onerror=alert(1)>-照片.png", "type": "image/png",
                         "base64": encoded_picture("PNG", (40, 150, 90, 255), (180, 180))}],
        "multiple": [
            {"name": "first.jpg", "type": "image/jpeg",
             "base64": encoded_picture("JPEG", "#805030", (80, 40))},
            {"name": "second.png", "type": "image/png",
             "base64": encoded_picture("PNG", (30, 90, 160, 255), (40, 80))},
        ],
    }
    manifest = json.dumps(files).replace("<", "\\u003c")
    return f"""
(() => {{
  const manifest = {manifest};
  window.MM022Fixture = {{revokeCount: 0, fetches: []}};
  document.documentElement.dataset.mm022FixtureReady = 'true';
  document.documentElement.dataset.mm022RevokeCount = '0';
  document.documentElement.dataset.mm022FetchCount = '0';
  const originalRevoke = URL.revokeObjectURL.bind(URL);
  URL.revokeObjectURL = value => {{
    window.MM022Fixture.revokeCount += 1;
    document.documentElement.dataset.mm022RevokeCount = String(window.MM022Fixture.revokeCount);
    originalRevoke(value);
  }};
  const originalFetch = window.fetch.bind(window);
  window.fetch = (...args) => {{
    window.MM022Fixture.fetches.push(String(args[0]));
    document.documentElement.dataset.mm022FetchCount = String(window.MM022Fixture.fetches.length);
    return originalFetch(...args);
  }};
  const bytes = value => {{
    const raw = atob(value);
    return Uint8Array.from(raw, character => character.charCodeAt(0));
  }};
  const makeFiles = key => {{
    if (manifest[key]) return manifest[key].map(item =>
      new File([bytes(item.base64)], item.name, {{type: item.type}}));
    if (key === 'zero') return [new File([], 'empty.png', {{type: 'image/png'}})];
    if (key === 'unsupported') return [new File(['notes'], 'notes.txt', {{type: 'text/plain'}})];
    if (key === 'corrupt') return [new File(['not image bytes'], 'corrupt.png', {{type: 'image/png'}})];
    if (key === 'over-limit') return [new File([new Uint8Array(5 * 1024 * 1024 + 1)],
      'too-large.jpg', {{type: 'image/jpeg'}})];
    return [];
  }};
  document.querySelectorAll('.fixture-drag-source').forEach(source => {{
    source.addEventListener('dragstart', event => {{
      event.dataTransfer.clearData();
      makeFiles(source.dataset.fixture).forEach(file => event.dataTransfer.items.add(file));
      event.dataTransfer.effectAllowed = 'copy';
    }});
    // Browser automation cannot always hold a native drag long enough to
    // produce DataTransfer files. A real button click therefore dispatches
    // the same browser DragEvents as a deterministic accessibility fallback.
    source.addEventListener('click', () => {{
      const zone = document.querySelector('#product-image-dropzone');
      const transfer = new DataTransfer();
      makeFiles(source.dataset.fixture).forEach(file => transfer.items.add(file));
      ['dragenter', 'dragover', 'drop'].forEach(type => zone.dispatchEvent(
        new DragEvent(type, {{bubbles: true, cancelable: true, dataTransfer: transfer}})
      ));
    }});
  }});
}})();
"""


def fixture_panel():
    return """
<section id="mm022-fixtures" class="panel" aria-label="MM-022 temporary drag sources">
  <h2>Temporary drag-test files</h2>
  <p>These controls exist only in the isolated browser fixture.</p>
  <div class="actions">
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="jpeg">Valid JPEG</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="png">Valid PNG</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="unsafe-name">HTML-like filename</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="multiple">Two files</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="zero">Empty PNG</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="unsupported">Text file</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="corrupt">Corrupt PNG</button>
    <button type="button" draggable="true" class="fixture-drag-source" data-fixture="over-limit">Over 5 MiB</button>
  </div>
</section>
<script src="/fixture-mm022.js"></script>
"""


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm022-browser-", dir=root))
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'dropzone.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(fixture_dir / "uploads"),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
    })
    with application.app_context():
        db.create_all()
        db.session.add(User(username="dropzone-seller", email="seller@dropzone.test",
                            password_hash=generate_password_hash(PASSWORD)))
        db.session.commit()

    @application.get("/fixture-mm022.js")
    def fixture_script():
        return Response(fixture_javascript(), mimetype="application/javascript")

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
    print("MM-022 fixture: http://127.0.0.1:5022/auth/login?next=/listings/new", flush=True)
    print("Login: seller@dropzone.test / Image dropzone demo passphrase!", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5022, threads=8)
