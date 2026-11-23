r"""Disposable, loopback-only MM-017 browser fixtures. Never opens the real database.

Run: .venv\Scripts\python.exe -m tests.preview_image_interactions
Stop with Ctrl+C. Generated fixtures stay under .pytest-tmp for inspection.
"""

from decimal import Decimal
from pathlib import Path
import tempfile

from flask import abort, render_template, Response
from PIL import Image

from app import create_app
from app.extensions import db
from app.forms import MessageForm
from app.marketplace import TRANSITIONS
from app.models import Product, User


def build_preview():
    root = Path(__file__).resolve().parents[1]
    temp_root = root / '.pytest-tmp'
    temp_root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix='mm017-browser-', dir=temp_root))
    uploads = fixture_dir / 'uploads'
    uploads.mkdir()
    landscape = '1' * 32 + '.jpg'
    portrait = '2' * 32 + '.jpg'
    # Synthetic test images, not additions to the marketplace.
    Image.new('RGB', (1200, 800), '#497787').save(uploads / landscape)
    Image.new('RGB', (600, 1400), '#b17a45').save(uploads / portrait)
    application = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'UPLOAD_FOLDER': str(uploads), 'AI_FOLDER': str(fixture_dir / 'ai'),
        'TEMPLATES_AUTO_RELOAD': True})
    with application.app_context():
        db.create_all()
        seller = User(username='fixture-seller', email='fixture@example.test', password_hash='not-a-login')
        db.session.add(seller)
        for title, filename in [('Landscape test picture', landscape),
                                ('Portrait test picture', portrait), ('No image fixture', None)]:
            db.session.add(Product(seller=seller, title=title,
                description='Isolated browser fixture. Not a real marketplace listing. ' * 12,
                price=Decimal('10.00'), currency='USD', category='electronics',
                condition='good', status='active', image_filename=filename))
        db.session.commit()

    @application.get('/fixture/<variant>')
    def fixture(variant):
        if variant not in {'landscape', 'portrait', 'missing', 'broken', 'no-js', 'no-dialog'}:
            abort(404)
        product = db.session.get(Product, {'portrait': 2, 'missing': 3}.get(variant, 1))
        html = render_template('product.html', product=product, transitions=TRANSITIONS,
                               message_form=MessageForm())
        if variant == 'broken':
            html = html.replace(f'data-src="/media/products/{landscape}"',
                                'data-src="/fixture-image-unavailable"')
        if variant == 'no-js':
            # No script is delivered: equivalent page fallback, not a browser preference change.
            html = html.replace('<script src="/static/js/market.js" defer></script>', '')
        if variant == 'no-dialog':
            html = html.replace('<script src="/static/js/market.js"',
                '<script src="/fixture-no-dialog.js"></script><script src="/static/js/market.js"')
        return html

    @application.get('/fixture-no-dialog.js')
    def no_dialog():
        # Test-only external script; never included by the real application.
        return Response('HTMLDialogElement.prototype.showModal = undefined;', mimetype='text/javascript')

    return application


if __name__ == '__main__':
    from waitress import serve
    print('Disposable MM-017 preview: http://127.0.0.1:5017/fixture/landscape', flush=True)
    serve(build_preview(), host='127.0.0.1', port=5017)
