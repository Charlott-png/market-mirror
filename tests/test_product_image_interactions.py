"""MM-017 server-rendering contracts; browser behaviour is checked separately."""

from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

from PIL import Image
import pytest
from sqlalchemy import select


class Markup(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def find(self, tag=None, **attrs):
        return [a for t, a in self.nodes if (tag is None or t == tag)
                and all(a.get(k) == v for k, v in attrs.items())]


@pytest.fixture
def photo(db_app):
    folder = Path(db_app.config['UPLOAD_FOLDER'])
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + '.jpg'
    Image.new('RGB', (120, 90), 'teal').save(folder / name)
    return name


def login(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['login_at'] = 2000000000


def assert_lightbox(response, product):
    assert response.status_code == 200
    markup = Markup(response.get_data(as_text=True))
    url = f'/media/products/{product.image_filename}'
    trigger, = markup.find('a', id='product-image-trigger')
    assert trigger['href'] == url
    assert trigger['aria-label'] == f'Enlarge image of {product.title}'
    dialog, = markup.find('dialog', id='product-image-dialog')
    assert 'open' not in dialog
    assert dialog['aria-label'] == f'Image of {product.title}'
    large, = markup.find('img', id='product-lightbox-image')
    assert large['alt'] == product.title
    assert large['data-src'] == url  # Assigned on open, after error listeners.
    assert 'src' not in large
    close, = markup.find('button', id='product-image-close')
    assert close['type'] == 'button'
    assert close['aria-label'] == 'Close image'
    error, = markup.find(id='product-image-error')
    assert 'hidden' in error and error['role'] == 'status'
    script, = markup.find('script', src='/static/js/market.js')
    assert 'defer' in script
    assert not any(k.startswith('on') for _, a in markup.nodes for k in a)
    return markup


@pytest.mark.parametrize('status', ['active', 'sold'])
def test_available_public_photo_contract(client, product_factory, photo, status):
    product = product_factory(image_filename=photo, status=status)
    assert_lightbox(client.get(f'/products/{product.id}'), product)
    assert client.get(f'/media/products/{photo}').status_code == 200


@pytest.mark.parametrize('filename', [None, 'a' * 32 + '.jpg'])
def test_missing_photo_remains_noninteractive(client, product_factory, filename):
    product = product_factory(image_filename=filename)
    response = client.get(f'/products/{product.id}')
    assert response.status_code == 200 and b'No photo yet' in response.data
    markup = Markup(response.get_data(as_text=True))
    assert not markup.find(id='product-image-trigger')
    assert not markup.find('dialog')


def test_owner_preview_and_archived_media_permissions(client, product_factory, user_factory, photo):
    owner = user_factory()
    stranger = user_factory()
    product = product_factory(seller=owner, image_filename=photo, status='archived')
    preview = f'/listings/{product.id}/preview'
    media = f'/media/products/{photo}'
    assert client.get(f'/products/{product.id}').status_code == 404
    assert client.get(media).status_code == 404
    login(client, stranger)
    assert client.get(preview).status_code == 404
    assert client.get(media).status_code == 404
    login(client, owner)
    assert_lightbox(client.get(preview), product)
    assert client.get(media).status_code == 200


def test_title_is_escaped_in_all_new_attributes(client, product_factory, photo):
    title = 'Laptop "quoted" <img src=x onerror=alert(1)> & more'
    product = product_factory(title=title, image_filename=photo)
    markup = assert_lightbox(client.get(f'/products/{product.id}'), product)
    assert not markup.find('img', src='x')


def test_catalogue_cards_are_unchanged(client, product_factory, photo):
    product = product_factory(image_filename=photo)
    markup = Markup(client.get('/products').get_data(as_text=True))
    assert markup.find('a', href=f'/products/{product.id}')
    assert not markup.find(id='product-image-trigger')
    assert not markup.find('dialog')
    assert not Markup(client.get('/').get_data(as_text=True)).find('dialog')


def test_rendering_preserves_database_and_existing_forms(client, product_factory, user_factory, photo, db_session):
    from app.models import Product, User
    owner = user_factory()
    buyer = user_factory()
    product = product_factory(seller=owner, image_filename=photo)
    before_products = db_session.execute(select(Product.__table__)).all()
    before_users = db_session.execute(select(User.__table__)).all()
    login(client, buyer)
    markup = assert_lightbox(client.get(f'/products/{product.id}'), product)
    assert markup.find('form', action=f'/products/{product.id}/save')
    assert markup.find('form', action=f'/products/{product.id}/contact')
    login(client, owner)
    owner_markup = assert_lightbox(client.get(f'/products/{product.id}'), product)
    assert owner_markup.find('a', href=f'/listings/{product.id}/edit')
    assert owner_markup.find('form', action=f'/listings/{product.id}/status')
    assert db_session.execute(select(Product.__table__)).all() == before_products
    assert db_session.execute(select(User.__table__)).all() == before_users
