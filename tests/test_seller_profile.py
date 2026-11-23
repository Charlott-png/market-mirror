"""MM-018 contracts written before the profile upgrade; no live database use."""

from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import pytest
from sqlalchemy import select

from tests.test_marketplace import sign_in, listing_data


class Page(HTMLParser):
    """Small HTML reader: collect attributes and descendant text, not whitespace."""
    def __init__(self, response):
        super().__init__(convert_charrefs=True)
        assert response.status_code == 200
        self.html = response.get_data(as_text=True)
        self.nodes, self.stack = [], []
        self.feed(self.html)

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'text': ''}
        self.nodes.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]['tag'] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node['text'] += data

    def find(self, tag=None, **attrs):
        return [n for n in self.nodes if (tag is None or n['tag'] == tag)
                and all(n['attrs'].get(k) == v for k, v in attrs.items())]

    def one(self, tag=None, **attrs):
        found = self.find(tag, **attrs)
        assert len(found) == 1, f'Expected one {tag}/{attrs}, found {len(found)}'
        return found[0]

    def text(self, tag=None, **attrs):
        return ' '.join(self.one(tag, **attrs)['text'].split())

    def card_ids(self):
        return [int(n['attrs']['href'].rsplit('/', 1)[1])
                for n in self.find('a', **{'class': 'photo-link'})]


def profile(client, seller, query=''):
    return Page(client.get(f'/sellers/{seller.username}' + query))


def assert_badge(page, expected):
    badges = page.find(id='seller-activity-badge')
    explanations = page.find(id='seller-badge-explanation')
    assert len(badges) == len(explanations) == int(expected)
    if expected:
        assert page.text(id='seller-activity-badge') == 'Verified Seller'
        assert 'Identity has not been verified.' in page.text(id='seller-badge-explanation')
        assert 'hidden' not in explanations[0]['attrs']
        assert 'Verified Seller' in page.text(id='seller-profile-header')


@pytest.mark.parametrize('active_count', [0, 1, 2, 3, 4, 5])
def test_badge_exact_threshold_and_count(client, user_factory, product_factory, active_count):
    seller = user_factory()
    for _ in range(active_count):
        product_factory(seller=seller)
    page = profile(client, seller)
    assert_badge(page, active_count > 3)
    assert page.text(id='seller-active-count') == f'{active_count} active listing' + ('' if active_count == 1 else 's')
    assert page.text('h1') == seller.username
    assert page.text('h2', id='seller-listings-title') == 'Active listings'
    assert len(page.card_ids()) == active_count


@pytest.mark.parametrize('viewer', ['anonymous', 'owner', 'other'])
def test_product_link_public_access_and_case(client, user_factory, product_factory, viewer):
    seller = user_factory(username='profile-seller')
    other = user_factory()
    product = product_factory(seller=seller)
    if viewer != 'anonymous':
        sign_in(client, seller if viewer == 'owner' else other)
    detail = Page(client.get(f'/products/{product.id}'))
    link = detail.one('a', href='/sellers/profile-seller')['attrs']['href']
    assert Page(client.get(link)).text('h1') == seller.username
    upper = Page(client.get('/sellers/PROFILE-SELLER'))
    assert upper.text('h1') == seller.username
    assert upper.card_ids() == [product.id]
    assert upper.find('a', href='/products')


def test_excludes_other_sellers_and_inactive_products(client, user_factory, product_factory):
    seller, other = user_factory(), user_factory()
    visible = [product_factory(seller=seller) for _ in range(3)]
    excluded = [product_factory(seller=seller, title=f'Private {status}', status=status)
                for status in ['sold', 'archived']]
    excluded += [product_factory(seller=other, title=f'Other seller {i}') for i in range(4)]
    page = profile(client, seller, '?verified=true&status=archived&seller_id=' + str(other.id))
    assert set(page.card_ids()) == {p.id for p in visible}
    assert_badge(page, False)
    assert page.text(id='seller-active-count') == '3 active listings'
    assert all(p.title not in page.html for p in excluded)


def test_pagination_and_deterministic_order(client, user_factory, product_factory):
    seller = user_factory()
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    products = [product_factory(seller=seller, created_at=base + timedelta(days=i % 3)) for i in range(21)]
    product_factory(seller=seller, status='archived')
    product_factory()
    expected = [p.id for p in sorted(products, key=lambda p: (p.created_at, p.id), reverse=True)]
    first, second = profile(client, seller), profile(client, seller, '?page=2')
    assert first.card_ids() == expected[:20]
    assert second.card_ids() == expected[20:]
    for page in (first, second):
        assert_badge(page, True)
        assert page.text(id='seller-active-count') == '21 active listings'
    assert first.find('a', href=f'/sellers/{seller.username}?page=2')
    assert second.find('a', href=f'/sellers/{seller.username}?page=1')
    assert client.get(f'/sellers/{seller.username}?page=3').status_code == 404


def test_badge_recomputed_after_supported_status_transitions(client, db_app, user_factory, product_factory, db_session):
    db_app.config['WTF_CSRF_ENABLED'] = False
    seller = user_factory()
    items = [product_factory(seller=seller) for _ in range(4)]
    sign_in(client, seller)
    target = items[0]
    assert_badge(profile(client, seller), True)
    for status, expected in [('archived', False), ('active', True), ('sold', False)]:
        response = client.post(f'/listings/{target.id}/status', data={'status': status, 'version': target.version})
        assert response.status_code == 302
        db_session.refresh(target)
        page = profile(client, seller)
        assert_badge(page, expected)
        assert page.text(id='seller-active-count') == ('4 active listings' if expected else '3 active listings')


@pytest.mark.parametrize('instant,iso,label', [
    (datetime(2024, 2, 29, 12, tzinfo=timezone.utc), '2024-02-29', '29 February 2024'),
    (datetime(2026, 10, 29, 0, 15, tzinfo=timezone(timedelta(hours=8))), '2026-10-28', '28 October 2026'),
    (datetime(2026, 1, 1, tzinfo=timezone.utc), '2026-01-01', '1 January 2026'),
])
def test_join_date_uses_persisted_utc_date(client, user_factory, db_session, instant, iso, label):
    seller = user_factory(created_at=instant)
    db_session.expire_all()
    page = profile(client, seller)
    assert page.text('time', datetime=iso) == label
    assert 'Joined' in page.text(id='seller-profile-header')


def test_listing_edit_does_not_change_join_date(client, db_app, user_factory, product_factory, db_session):
    db_app.config['WTF_CSRF_ENABLED'] = False
    seller = user_factory(created_at=datetime(2020, 5, 6, tzinfo=timezone.utc))
    product = product_factory(seller=seller)
    sign_in(client, seller)
    assert profile(client, seller).text('time', datetime='2020-05-06') == '6 May 2020'
    assert client.post(f'/listings/{product.id}/edit', data=listing_data(version=product.version)).status_code == 302
    db_session.refresh(seller)
    assert profile(client, seller).text('time', datetime='2020-05-06') == '6 May 2020'


@pytest.mark.parametrize('page', ['0', '-1', '', 'abc', '1.5', '١', '123456789', '1&page=2', '1&page=1'])
def test_invalid_pages(client, user_factory, page):
    seller = user_factory()
    assert client.get(f'/sellers/{seller.username}?page={page}').status_code == 400


def test_empty_missing_and_bio_fallback(client, user_factory):
    seller = user_factory(bio='   ')
    page = profile(client, seller)
    assert 'This seller has no active listings right now.' in page.html
    assert 'This seller has not added a biography yet.' in page.html
    assert_badge(page, False)
    assert client.get(f'/sellers/{seller.username}?page=2').status_code == 404
    assert client.get('/sellers/nonexistent-seller').status_code == 404


def test_privacy_escaping_and_read_only(client, user_factory, product_factory, db_session):
    from app.extensions import db
    from app.models import SavedProduct, Conversation, Message, InteractionEvent
    seller = user_factory(email='secret-profile-canary@example.test', password_hash='private-hash-canary',
        bio='Verified Seller\n<script>alert("BIO_CANARY")</script> & hello')
    buyer = user_factory()
    product = product_factory(seller=seller)
    conversation = Conversation(product_id=product.id, seller_id=seller.id, buyer_id=buyer.id)
    db_session.add(conversation)
    db_session.flush()
    db_session.add_all([Message(conversation_id=conversation.id, sender_id=buyer.id,
        body='private-message-canary', request_token='private-token-canary'),
        SavedProduct(user_id=buyer.id, product_id=product.id),
        InteractionEvent(user_id=buyer.id, product_id=product.id, kind='view', window=1)])
    db_session.commit()
    def snapshot():
        return {t.name: db_session.execute(select(t)).all() for t in db.metadata.sorted_tables}
    before = snapshot()
    page = profile(client, seller)
    assert not page.find('script', src=None)
    assert '&lt;script&gt;' in page.html
    assert page.text(id='seller-bio') == 'Verified Seller <script>alert("BIO_CANARY")</script> & hello'
    assert_badge(page, False)
    for private in (seller.email, seller.password_hash, 'private-message-canary', 'private-token-canary'):
        assert private not in page.html
    assert snapshot() == before


def test_cards_and_other_pages_do_not_get_profile_header(client, user_factory, product_factory):
    seller = user_factory()
    products = [product_factory(seller=seller) for _ in range(4)]
    page = profile(client, seller)
    assert len(page.find('span', **{'class': 'photo-placeholder', 'aria-label': 'No product photo'})) == 4
    assert '$49.99' in page.html and 'USD' in page.html
    assert Page(client.get('/products')).find(id='seller-profile-header') == []
    sign_in(client, seller)
    own = Page(client.get('/account/listings'))
    assert not own.find(id='seller-profile-header')
    assert not own.find(id='seller-activity-badge')
    assert own.find('a', href=f'/listings/{products[0].id}/preview')
