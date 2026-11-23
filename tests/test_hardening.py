"""Additional adversarial and concurrent checks against the approved contracts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import logging
import re
import time

import pytest
from PIL import Image
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from werkzeug.datastructures import FileStorage


def login(client, identifier):
    with client.session_transaction() as session:
        session['_user_id'] = str(identifier)
        session['_fresh'] = True
        session['login_at'] = time.time()


def data(**changes):
    values = dict(title="A useful lamp", description="A useful lamp in good working condition.",
                  category="home_garden", condition="good", price="12.50", request_token="same-request")
    values.update(changes)
    return values


@pytest.mark.parametrize('source,target,expected', [
    ('active', 'active', 302), ('active', 'sold', 302), ('active', 'archived', 302),
    ('sold', 'active', 400), ('sold', 'sold', 302), ('sold', 'archived', 302),
    ('archived', 'active', 302), ('archived', 'sold', 400), ('archived', 'archived', 302)])
def test_complete_status_matrix(db_app, user_factory, product_factory, source, target, expected):
    from app.extensions import db
    db_app.config['WTF_CSRF_ENABLED'] = False
    owner = user_factory()
    product = product_factory(seller=owner, status=source)
    client = db_app.test_client()
    login(client, owner.id)
    result = client.post(f'/listings/{product.id}/status', data={'version': product.version, 'status': target})
    assert result.status_code == expected
    db.session.refresh(product)
    assert product.status == (target if expected == 302 else source)


@pytest.mark.parametrize('operation', ['create', 'save', 'contact'])
def test_two_simultaneous_requests_are_idempotent(db_app, user_factory, product_factory, operation):
    from app.extensions import db
    from app.models import Product, SavedProduct, Conversation, Message
    db_app.config['WTF_CSRF_ENABLED'] = False
    user = user_factory()
    product = product_factory()
    uid, pid = user.id, product.id
    clients = [db_app.test_client(), db_app.test_client()]
    for client in clients:
        login(client, uid)
    route = '/listings/new' if operation == 'create' else f'/products/{pid}/{operation}'
    payload = data() if operation == 'create' else {'body': 'Hello seller', 'request_token': 'same-message'}
    db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda client: client.post(route, data=payload), clients))
    assert [r.status_code for r in responses] == [302, 302]
    if operation == 'create':
        assert db.session.query(Product).filter_by(seller_id=uid).count() == 1
        assert responses[0].location == responses[1].location
    elif operation == 'save':
        assert db.session.query(SavedProduct).count() == 1
    else:
        assert db.session.query(Conversation).count() == db.session.query(Message).count() == 1


def test_listing_image_commit_failure_keeps_old_image(db_app, user_factory, product_factory, monkeypatch):
    from app.extensions import db
    from app.images import store_image, image_path
    db_app.config['WTF_CSRF_ENABLED'] = False
    picture = BytesIO()
    Image.new('RGB', (20, 30), 'green').save(picture, format='PNG')
    original_bytes = picture.getvalue()
    old_name = store_image(FileStorage(stream=BytesIO(original_bytes), filename='old.png'))
    owner = user_factory()
    product = product_factory(seller=owner, image_filename=old_name)
    client = db_app.test_client()
    login(client, owner.id)
    def failure():
        raise OperationalError('private-path', {}, Exception('secret-canary'))
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'commit', failure)
        result = client.post(f'/listings/{product.id}/edit', data=data(version=product.version,
            image=(BytesIO(original_bytes), 'new.png')))
    assert result.status_code == 400 and b'secret-canary' not in result.data
    db.session.refresh(product)
    assert product.image_filename == old_name and image_path(old_name).exists()
    assert [p.name for p in Path(db_app.config['UPLOAD_FOLDER']).iterdir()] == [old_name]


@pytest.mark.parametrize('kind', ['empty', 'bytes', 'pixels', 'animated'])
def test_rejected_image_limits(db_app, kind):
    from app.images import store_image
    if kind == 'empty':
        payload = b''
    elif kind == 'bytes':
        payload = b'x' * (5 * 1024 * 1024 + 1)
    else:
        stream = BytesIO()
        if kind == 'pixels':
            Image.new('RGB', (4001, 3000)).save(stream, format='PNG')
        else:
            frames = [Image.new('RGB', (8, 8), color) for color in ('red', 'blue')]
            frames[0].save(stream, format='PNG', save_all=True, append_images=frames[1:])
        payload = stream.getvalue()
    with db_app.app_context(), pytest.raises(ValueError):
        store_image(FileStorage(stream=BytesIO(payload), filename='image.png'))


def test_real_csrf_protects_all_mutations(db_app, user_factory, product_factory):
    from app.extensions import db
    from app.models import Product, SavedProduct, Conversation
    owner = user_factory()
    product = product_factory(seller=owner)
    client = db_app.test_client()
    login(client, owner.id)
    routes = ['/auth/logout', '/account/profile', '/listings/new', f'/listings/{product.id}/edit',
              f'/listings/{product.id}/status', f'/products/{product.id}/save',
              f'/products/{product.id}/unsave', f'/products/{product.id}/contact',
              f'/products/{product.id}/view', '/messages/1/send', '/messages/1/read', '/ai/category', '/ai/price']
    for route in routes:
        assert client.post(route, data=data()).status_code == 400
    assert db.session.query(Product).count() == 1
    assert db.session.query(SavedProduct).count() == db.session.query(Conversation).count() == 0


def test_tampered_cookie_cannot_authenticate(db_app, user_factory):
    client = db_app.test_client()
    login(client, user_factory().id)
    cookie = client.get_cookie('session').value
    client.set_cookie('session', cookie[:-3] + 'bad')
    assert client.get('/dashboard').status_code == 302


def test_query_counts_and_pagination_are_bounded(db_app, user_factory, capsys):
    from app.extensions import db
    from app.models import Product
    owner = user_factory()
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db.session.add_all([Product(seller_id=owner.id, title=f'Fixture item {i:04d}', description='A complete fixture description.',
        price=Decimal('12.50'), category='electronics', condition='good', status='active', created_at=stamp)
        for i in range(1000)])
    db.session.commit()
    client = db_app.test_client()
    count = []
    def observed(*args):
        count.append(1)
    event.listen(db.engine, 'before_cursor_execute', observed)
    try:
        started = time.perf_counter()
        first = client.get('/products?sort=price_asc')
        first_count = len(count)
        count.clear()
        second = client.get('/products?sort=price_asc&page=2')
        assert first.status_code == second.status_code == 200
        first_ids = set(re.findall(rb'href="/products/(\d+)"', first.data))
        second_ids = set(re.findall(rb'href="/products/(\d+)"', second.data))
        assert len(first_ids) == len(second_ids) == 20 and not first_ids & second_ids
        assert first_count <= 4 and len(count) <= 4
        login(client, owner.id)
        count.clear()
        assert client.get('/dashboard').status_code == 200
        assert len(count) <= 8
        print(f'1000-row fixture: catalogue queries={first_count}, dashboard queries={len(count)}, elapsed={time.perf_counter()-started:.3f}s')
    finally:
        event.remove(db.engine, 'before_cursor_execute', observed)


def test_request_logging_contains_no_private_values(db_app, caplog):
    with caplog.at_level(logging.INFO):
        response = db_app.test_client().get('/products?q=private-search-canary')
    assert response.status_code == 200
    assert 'request_complete' in caplog.text
    assert 'private-search-canary' not in caplog.text
    assert 'X-Request-ID' in response.headers


def test_dataset_rejects_extra_private_fields_and_near_duplicates():
    from app.ai.data import synthetic_rows, prepare_dataset
    rows = synthetic_rows()
    private = {**rows[0], 'product_id': 'private', 'email': 'do-not-train@example.test'}
    near = {**rows[0], 'product_id': 'near', 'duplicate_group': 'new-group',
            'description': rows[0]['description'] + ' Available.'}
    report = prepare_dataset(rows + [private, near])
    assert report['rejected_count'] == 2


def test_index_ranking_staleness_and_consent(db_app, user_factory, product_factory):
    from app.extensions import db
    from app.ai.recommendations import build_index, recommend
    from app.models import InteractionEvent
    viewer = user_factory(personalization=True)
    base = product_factory(title='Digital keyboard', description='Digital computer keyboard typing electronic keys.')
    match = product_factory(title='Digital keyboard', description='Digital computer keyboard typing electronic keys.')
    unrelated = product_factory(title='Garden watering can', description='Water garden plants and flowers.', category='home_garden')
    build_index(db_app.config['AI_FOLDER'])
    assert recommend(viewer.id, base.id)['items'][0]['id'] == match.id
    match.status = 'archived'
    db.session.add(InteractionEvent(user_id=viewer.id, product_id=base.id, kind='view', window=1))
    db.session.commit()
    assert match.id not in [p['id'] for p in recommend(viewer.id, base.id)['items']]
    viewer.personalization = False
    db.session.commit()
    assert all('opted-in' not in p['reason'] for p in recommend(viewer.id)['items'])


def test_training_has_no_test_vocabulary_or_price_target(tmp_path):
    from app.ai.data import synthetic_rows, prepare_dataset
    from app.ai.training import train_models, structured_features
    from app.ai.inference import load_bundle
    rows = synthetic_rows()
    split = prepare_dataset(rows)
    test_ids = {r['product_id'] for r in split['test']}
    for row in rows:
        if row['product_id'] in test_ids:
            row['description'] += ' Heldoutcanary.'
    train_models(rows, tmp_path)
    bundle, _ = load_bundle(tmp_path)
    vocabulary = bundle['category'].named_steps['features'].named_steps['tfidf'].vocabulary_
    assert 'heldoutcanary' not in vocabulary
    assert structured_features([{'category': 'other', 'condition': 'good', 'price': '123.45'}]) == [{'category': 'other', 'condition': 'good'}]


def test_catalogue_cards_name_the_seller_without_email(db_app, user_factory, product_factory):
    seller = user_factory(username='visible-seller', email='private-seller@example.test')
    product_factory(seller=seller)
    page = db_app.test_client().get('/products')
    assert b'visible-seller' in page.data
    assert b'private-seller@example.test' not in page.data


def test_unexpected_exception_logs_no_secret(db_app, caplog):
    @db_app.get('/test-only-crash')
    def fail():
        raise RuntimeError('private-error-canary')
    with caplog.at_level(logging.WARNING):
        response = db_app.test_client().get('/test-only-crash')
    assert response.status_code == 500
    assert b'private-error-canary' not in response.data
    assert 'private-error-canary' not in caplog.text


def test_sqlite_backup_restores_rows_prices_and_foreign_keys(db_app, user_factory, product_factory, tmp_path):
    import sqlite3
    from sqlalchemy.engine import make_url
    from app.extensions import db
    owner = user_factory()
    product = product_factory(seller=owner, price=Decimal('123.45'))
    source_path = make_url(db_app.config['SQLALCHEMY_DATABASE_URI']).database
    restored = tmp_path / 'restored.sqlite'
    db.session.remove()
    with sqlite3.connect(source_path) as source, sqlite3.connect(restored) as destination:
        source.backup(destination)
        assert destination.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert destination.execute('PRAGMA foreign_key_check').fetchall() == []
        assert destination.execute('SELECT price FROM products').fetchone() == (12345,)
        assert destination.execute('SELECT count(*) FROM users').fetchone() == (1,)


@pytest.mark.parametrize('failure_point', ['open', 'replace'])
def test_image_disk_failure_does_not_leave_new_file(db_app, monkeypatch, failure_point):
    from app.images import store_image
    stream = BytesIO()
    Image.new('RGB', (10, 10), 'red').save(stream, format='PNG')
    original = getattr(Path, failure_point)
    def fail(path, *args, **kwargs):
        if path.suffix == '.pending':
            raise OSError('private-disk-canary')
        return original(path, *args, **kwargs)
    with db_app.app_context(), monkeypatch.context() as patch:
        patch.setattr(Path, failure_point, fail)
        with pytest.raises(OSError):
            store_image(FileStorage(stream=BytesIO(stream.getvalue()), filename='photo.png'))
    root = Path(db_app.config['UPLOAD_FOLDER'])
    assert not list(root.iterdir())


def test_photo_orientation_and_metadata_are_normalized(db_app):
    from app.images import store_image, image_path
    stream = BytesIO()
    source = Image.new('RGB', (200, 100), 'blue')
    exif = Image.Exif()
    exif[274] = 6  # Rotate the landscape source clockwise for portrait display.
    exif[270] = 'private-photo-metadata'
    source.save(stream, format='JPEG', exif=exif)
    with db_app.app_context():
        name = store_image(FileStorage(stream=BytesIO(stream.getvalue()), filename='portrait.jpg'))
        with Image.open(image_path(name)) as normalized:
            assert normalized.size == (100, 200)
            assert not normalized.getexif()


def test_ready_recovers_after_database_outage(db_app, monkeypatch):
    from app.extensions import db
    client = db_app.test_client()
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise OperationalError('private-path', {}, Exception('private-outage'))
        patch.setattr(db.session, 'execute', fail)
        assert client.get('/ready').status_code == 503
    assert client.get('/ready').status_code == 200


def test_production_configuration_cookie_hosts_and_storage(monkeypatch, tmp_path):
    from config import environment_settings
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'test-only-production-configuration' * 2)
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://test:unused@localhost/test_only')
    monkeypatch.setenv('TRUSTED_HOSTS', 'market.example.test')
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path / 'uploads'))
    settings = environment_settings(tmp_path)
    assert settings['SESSION_COOKIE_SECURE'] is True and settings['DEBUG'] is False
    assert settings['TRUSTED_HOSTS'] == ['market.example.test']
    assert settings['UPLOAD_FOLDER'] == str(tmp_path / 'uploads')


def test_optional_event_failure_does_not_undo_save(db_app, user_factory, product_factory, monkeypatch):
    from app.extensions import db
    from app.models import SavedProduct
    db_app.config['WTF_CSRF_ENABLED'] = False
    buyer = user_factory(personalization=True)
    product = product_factory()
    client = db_app.test_client()
    login(client, buyer.id)
    original = db.session.execute
    def fail_event(statement, *args, **kwargs):
        if str(statement).startswith('UPDATE users SET id = id'):
            raise OperationalError('private-event', {}, Exception('unavailable'))
        return original(statement, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'execute', fail_event)
        assert client.post(f'/products/{product.id}/save').status_code == 302
    assert db.session.query(SavedProduct).count() == 1


@pytest.mark.parametrize('operation', ['contact', 'reply'])
def test_invalid_message_preserves_safe_text_and_field_error(db_app, user_factory, product_factory, operation):
    from app.extensions import db
    from app.models import Message
    db_app.config['WTF_CSRF_ENABLED'] = False
    buyer = user_factory()
    product = product_factory()
    client = db_app.test_client()
    login(client, buyer.id)
    url = f'/products/{product.id}/contact'
    if operation == 'reply':
        result = client.post(url, data={'body': 'First valid message', 'request_token': 'initial'})
        assert result.status_code == 302
        url = result.location + '/send'
    body = '<script>not executable</script>' + 'x' * 2000
    response = client.post(url, data={'body': body, 'request_token': 'retry'})
    assert response.status_code == 400
    assert b'&lt;script&gt;not executable&lt;/script&gt;' in response.data
    assert b'<script>not executable</script>' not in response.data
    assert b'2000' in response.data
    assert db.session.query(Message).count() == (1 if operation == 'reply' else 0)
