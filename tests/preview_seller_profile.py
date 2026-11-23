"""Loopback-only MM-018 browser fixtures; never reads the real database.

Run with: python -m tests.preview_seller_profile
Stop with Ctrl+C. Test assets remain in .pytest-tmp for inspection.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile

from flask import request
from PIL import Image

from app import create_app
from app.extensions import db
from app.models import Product, User


def build_preview():
    root = Path(__file__).resolve().parents[1] / '.pytest-tmp'
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix='mm018-browser-', dir=root))
    uploads = fixture_dir / 'uploads'
    uploads.mkdir()
    filename = '8' * 32 + '.jpg'
    Image.new('RGB', (900, 600), '#497787').save(uploads / filename)
    application = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'UPLOAD_FOLDER': str(uploads), 'AI_FOLDER': str(fixture_dir / 'ai'),
        'TEMPLATES_AUTO_RELOAD': True})
    with application.app_context():
        db.create_all()
        for name, count in [('three-items', 3), ('four-items', 4), ('many-items', 21),
                            ('empty-seller', 0), ('long-profile-name-123456789012', 4)]:
            seller = User(username=name, email=f'{name}@example.test', password_hash='not-a-login',
                created_at=datetime(2024, 2, 29, 12, tzinfo=timezone.utc),
                bio=None if count == 0 else 'An isolated test seller.\n' + 'LongBiographyText' * 15)
            db.session.add(seller)
            for index in range(count):
                db.session.add(Product(seller=seller, title=f'{name} item {index + 1:02}',
                    description='Isolated browser test product, not a real marketplace listing.',
                    price=Decimal('10.00'), currency='USD', category='electronics',
                    condition='good', status='active',
                    image_filename=filename if name == 'three-items' and index == 0 else None))
        db.session.commit()

    @application.after_request
    def optional_no_script_fixture(response):
        # Only this disposable app has the fixture switch, not the real server.
        if request.args.get('fixture_no_script') == '1' and response.mimetype == 'text/html':
            response.set_data(response.get_data(as_text=True).replace(
                '<script src="/static/js/market.js" defer></script>', ''))
        return response

    return application


if __name__ == '__main__':
    from waitress import serve
    print('MM-018 fixtures: http://127.0.0.1:5018/sellers/four-items', flush=True)
    serve(build_preview(), host='127.0.0.1', port=5018)
