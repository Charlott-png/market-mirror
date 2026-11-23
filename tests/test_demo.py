"""Rehearsal of the student demonstration with real forms and CSRF enabled.

Unlike unit fixtures that set a session directly, this uses registration and
password login. It needs no browser/server/network and uses only temporary data.
"""

import re


def fields(response):
    html = response.get_data(as_text=True)
    return {name: value for name, value in re.findall(r'<input[^>]*name="([^"]+)"[^>]*type="hidden"[^>]*value="([^"]*)"', html)}


def csrf(response):
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.get_data(as_text=True))
    assert token, 'Expected a real CSRF-protected page'
    return token.group(1)


def test_two_account_demo_with_real_password_login_and_csrf(db_app):
    from app.extensions import db
    from app.models import Product, SavedProduct, Message, Conversation
    clients = [db_app.test_client(), db_app.test_client()]
    for client, name in zip(clients, ('demo-seller', 'demo-buyer')):
        page = client.get('/auth/register')
        result = client.post('/auth/register', data={
            'csrf_token': csrf(page), 'username': name, 'email': name + '@example.test',
            'password': 'Disposable classroom passphrase!', 'confirm_password': 'Disposable classroom passphrase!'})
        assert result.status_code == 302
        page = client.get('/auth/login')
        result = client.post('/auth/login', data={'csrf_token': csrf(page), 'email': name + '@example.test',
                                               'password': 'Disposable classroom passphrase!'})
        assert result.status_code == 302 and client.get('/dashboard').status_code == 200
    seller, buyer = clients
    page = seller.get('/listings/new')
    payload = {**fields(page), 'csrf_token': csrf(page), 'title': 'Demo wireless keyboard',
               'description': 'A working electronic keyboard with digital controls and cable.',
               'price': '25.00', 'category': 'electronics', 'condition': 'good'}
    suggestion = seller.post('/ai/price', data=payload)
    assert suggestion.status_code == 200 and suggestion.json['value'] is None  # missing-artifact fallback
    created = seller.post('/listings/new', data=payload)
    assert created.status_code == 302
    identifier = int(re.search(r'/listings/(\d+)/preview', created.location).group(1))
    assert buyer.get('/products?q=wireless&category=electronics&max_price=30').status_code == 200
    page = buyer.get(f'/products/{identifier}')
    assert buyer.post(f'/products/{identifier}/save', data={'csrf_token': csrf(page)}).status_code == 302
    message_form = fields(page)
    message_form.update(csrf_token=csrf(page), body='Is this keyboard available?')
    contacted = buyer.post(f'/products/{identifier}/contact', data=message_form)
    assert contacted.status_code == 302
    thread = seller.get(contacted.location)
    reply = {**fields(thread), 'csrf_token': csrf(thread), 'body': 'Yes, it is available.'}
    assert seller.post(contacted.location + '/send', data=reply).status_code == 302
    assert b'Yes, it is available.' in buyer.get(contacted.location).data
    assert buyer.get(f'/listings/{identifier}/edit').status_code == 404
    preview = seller.get(created.location)
    version = re.search(r'name="version" value="(\d+)"', preview.get_data(as_text=True)).group(1)
    assert seller.post(f'/listings/{identifier}/status', data={'csrf_token': csrf(preview), 'version': version, 'status': 'sold'}).status_code == 302
    assert b'unavailable' in buyer.get(f'/products/{identifier}').data
    assert b'Unavailable product' in buyer.get('/saved').data
    with db_app.app_context():
        assert db.session.query(Product).one().status == 'sold'
        assert db.session.query(SavedProduct).count() == 1
        assert db.session.query(Conversation).count() == 1
        assert db.session.query(Message).count() == 2
