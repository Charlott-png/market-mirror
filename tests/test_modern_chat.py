"""MM-029 server contracts, written before the modern chat implementation."""

from datetime import datetime, timedelta, timezone
import re

import pytest
from sqlalchemy import event, func, select

from tests.test_marketplace import sign_in
from tests.test_seller_profile import Page


@pytest.fixture()
def chat_web(db_app):
    db_app.config.update(
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="isolated-mm029-modern-chat-secret",
    )
    return db_app.test_client()


@pytest.fixture()
def chat_story(chat_web, db_session, user_factory, product_factory):
    from app.models import Conversation, Message

    seller = user_factory(username="chat-seller", email="chat-seller@example.test")
    buyer = user_factory(username="chat-buyer", email="chat-buyer@example.test")
    stranger = user_factory(username="chat-stranger", email="chat-stranger@example.test")
    product = product_factory(seller=seller, title="Chat fixture camera")
    conversation = Conversation(
        product_id=product.id, buyer_id=buyer.id, seller_id=seller.id
    )
    db_session.add(conversation)
    db_session.flush()
    start = datetime(2026, 11, 7, 10, 45, tzinfo=timezone.utc)
    first = Message(
        conversation_id=conversation.id,
        sender_id=buyer.id,
        body="Is this still available? <script>never()</script>",
        request_token="mm029-buyer-first",
        created_at=start,
    )
    second = Message(
        conversation_id=conversation.id,
        sender_id=seller.id,
        body="Yes — it is available.",
        request_token="mm029-seller-first",
        created_at=start + timedelta(minutes=1),
    )
    db_session.add_all([first, second])
    db_session.commit()
    return {
        "seller": seller,
        "buyer": buyer,
        "stranger": stranger,
        "product": product,
        "conversation": conversation,
        "messages": [first, second],
    }


def add_messages(db_session, conversation, senders, count, *, prefix="History", same_time=False):
    from app.models import Message

    start = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(count):
        row = Message(
            conversation_id=conversation.id,
            sender_id=senders[index % len(senders)].id,
            body=f"{prefix} {index:03d}",
            request_token=f"mm029-{prefix.lower()}-{index}-{conversation.id}",
            created_at=start if same_time else start + timedelta(seconds=index),
        )
        db_session.add(row)
        rows.append(row)
    db_session.commit()
    return rows


def message_ids(html):
    return [int(value) for value in re.findall(r'data-message-id="(\d+)"', html)]


def updates(client, conversation_id, cursor="0"):
    return client.get(
        f"/messages/{conversation_id}/updates", query_string={"after_id": cursor}
    )


def table_counts(db_session):
    from app.extensions import db

    return {
        table.name: db_session.scalar(select(func.count()).select_from(table))
        for table in db.metadata.sorted_tables
    }


def test_thread_renders_semantic_owned_bubbles_and_safe_timestamps(chat_web, chat_story):
    sign_in(chat_web, chat_story["buyer"])
    response = chat_web.get(f'/messages/{chat_story["conversation"].id}')
    page = Page(response)

    shell = page.one(id="chat-shell")
    assert shell["attrs"]["data-live-updates"] == "true"
    assert shell["attrs"]["data-updates-url"].endswith("/updates")
    assert page.one("ol", id="chat-transcript")["attrs"]["aria-label"] == "Conversation messages"
    assert page.one(id="chat-live-status")["attrs"]["role"] == "status"

    html = response.get_data(as_text=True)
    first_id, second_id = [item.id for item in chat_story["messages"]]
    assert re.search(
        rf'data-message-id="{first_id}"[^>]*class="[^"]*chat-message--outgoing', html
    )
    assert re.search(
        rf'data-message-id="{second_id}"[^>]*class="[^"]*chat-message--incoming', html
    )
    assert "You" in html and "chat-seller" in html
    assert "10:45 AM UTC" in html and "10:46 AM UTC" in html
    assert re.search(r'<time[^>]+datetime="2026-11-07T10:45:00Z"', html)
    assert "&lt;script&gt;never()&lt;/script&gt;" in html
    assert "<script>never()</script>" not in html


def test_ownership_is_calculated_again_for_the_other_participant(chat_web, chat_story):
    sign_in(chat_web, chat_story["seller"])
    html = chat_web.get(f'/messages/{chat_story["conversation"].id}').get_data(as_text=True)
    first_id, second_id = [item.id for item in chat_story["messages"]]
    assert re.search(
        rf'data-message-id="{first_id}"[^>]*class="[^"]*chat-message--incoming', html
    )
    assert re.search(
        rf'data-message-id="{second_id}"[^>]*class="[^"]*chat-message--outgoing', html
    )


def test_latest_and_older_message_blocks_have_no_gaps_or_duplicates(
    chat_web, db_session, chat_story
):
    from app.models import Message

    for message in chat_story["messages"]:
        db_session.expunge(message)
    db_session.query(Message).delete(synchronize_session=False)
    db_session.commit()
    rows = add_messages(
        db_session,
        chat_story["conversation"],
        [chat_story["buyer"], chat_story["seller"]],
        101,
    )
    sign_in(chat_web, chat_story["buyer"])

    first = chat_web.get(f'/messages/{chat_story["conversation"].id}')
    second = chat_web.get(f'/messages/{chat_story["conversation"].id}?page=2')
    third = chat_web.get(f'/messages/{chat_story["conversation"].id}?page=3')
    first_ids, second_ids, third_ids = map(
        message_ids,
        [first.get_data(as_text=True), second.get_data(as_text=True), third.get_data(as_text=True)],
    )

    assert first_ids == [row.id for row in rows[-50:]]
    assert second_ids == [row.id for row in rows[-100:-50]]
    assert third_ids == [rows[0].id]
    assert len(set(first_ids + second_ids + third_ids)) == 101
    assert 'data-live-updates="true"' in first.get_data(as_text=True)
    assert 'data-live-updates="false"' in second.get_data(as_text=True)
    assert "Older messages" in first.get_data(as_text=True)
    assert "Return to latest messages" in second.get_data(as_text=True)
    assert chat_web.get(f'/messages/{chat_story["conversation"].id}?page=4').status_code == 404


def test_successful_reply_from_older_page_redirects_to_latest(chat_web, chat_story):
    sign_in(chat_web, chat_story["buyer"])
    response = chat_web.post(
        f'/messages/{chat_story["conversation"].id}/send?page=2',
        data={"body": "Take me back to the latest chat", "request_token": "older-send"},
    )
    assert response.status_code == 302
    assert response.location == f'/messages/{chat_story["conversation"].id}'


def test_updates_are_private_and_ownership_is_session_specific(chat_web, chat_story):
    conversation_id = chat_story["conversation"].id
    private_canary = chat_story["messages"][0].body

    anonymous = updates(chat_web, conversation_id)
    assert anonymous.status_code in {302, 401}
    assert private_canary.encode() not in anonymous.data

    sign_in(chat_web, chat_story["stranger"])
    denied = updates(chat_web, conversation_id)
    assert denied.status_code == 404
    assert private_canary.encode() not in denied.data

    sign_in(chat_web, chat_story["buyer"])
    buyer_data = updates(chat_web, conversation_id).get_json()
    assert [item["is_own"] for item in buyer_data["messages"]] == [True, False]

    sign_in(chat_web, chat_story["seller"])
    seller_data = updates(chat_web, conversation_id).get_json()
    assert [item["is_own"] for item in seller_data["messages"]] == [False, True]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?after_id=",
        "?after_id=-1",
        "?after_id=+1",
        "?after_id=1.0",
        "?after_id= 1",
        "?after_id=١",
        "?after_id=1&after_id=2",
        "?after_id=99999999999999999999",
    ],
)
def test_updates_reject_invalid_cursors_with_safe_json(chat_web, chat_story, query):
    sign_in(chat_web, chat_story["buyer"])
    response = chat_web.get(
        f'/messages/{chat_story["conversation"].id}/updates{query}'
    )
    assert response.status_code == 400
    assert response.mimetype == "application/json"
    assert response.get_json() == {"error": "Invalid message cursor."}
    assert chat_story["messages"][0].body.encode() not in response.data


def test_updates_have_exact_allow_list_order_time_and_no_store(chat_web, chat_story):
    sign_in(chat_web, chat_story["buyer"])
    response = updates(chat_web, chat_story["conversation"].id)

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "no-store" in response.headers.get("Cache-Control", "")
    payload = response.get_json()
    assert set(payload) == {"messages", "latest_id", "has_more"}
    assert payload["latest_id"] == chat_story["messages"][-1].id
    assert payload["has_more"] is False
    assert [item["id"] for item in payload["messages"]] == [
        item.id for item in chat_story["messages"]
    ]
    assert set(payload["messages"][0]) == {
        "id", "body", "sender_username", "is_own", "created_at", "fallback_time"
    }
    assert payload["messages"][0]["created_at"] == "2026-11-07T10:45:00Z"
    assert payload["messages"][0]["fallback_time"] == "10:45 AM UTC"
    serialized = response.get_data(as_text=True)
    for forbidden in (
        "email", "password_hash", "request_token", "sender_id", "buyer_id",
        "seller_id", "last_read_message_id", "chat-buyer@example.test",
    ):
        assert forbidden not in serialized


def test_updates_are_bounded_and_catch_up_without_duplicates(
    chat_web, db_session, chat_story
):
    from app.models import Message

    for message in chat_story["messages"]:
        db_session.expunge(message)
    db_session.query(Message).delete(synchronize_session=False)
    db_session.commit()
    rows = add_messages(
        db_session,
        chat_story["conversation"],
        [chat_story["buyer"], chat_story["seller"]],
        51,
        same_time=True,
    )
    sign_in(chat_web, chat_story["buyer"])

    first = updates(chat_web, chat_story["conversation"].id).get_json()
    second = updates(chat_web, chat_story["conversation"].id, first["latest_id"]).get_json()
    ids = [item["id"] for item in first["messages"] + second["messages"]]

    assert len(first["messages"]) == 50 and first["has_more"] is True
    assert len(second["messages"]) == 1 and second["has_more"] is False
    assert ids == [row.id for row in rows]
    assert len(ids) == len(set(ids)) == 51


def test_updates_empty_result_keeps_cursor(chat_web, chat_story):
    sign_in(chat_web, chat_story["buyer"])
    cursor = chat_story["messages"][-1].id
    assert updates(chat_web, chat_story["conversation"].id, cursor).get_json() == {
        "messages": [], "latest_id": cursor, "has_more": False
    }


def test_cross_conversation_cursor_never_returns_other_private_text(
    chat_web, db_session, chat_story, product_factory
):
    from app.models import Conversation, Message

    other_product = product_factory(seller=chat_story["seller"], title="Other private product")
    other = Conversation(
        product_id=other_product.id,
        buyer_id=chat_story["stranger"].id,
        seller_id=chat_story["seller"].id,
    )
    db_session.add(other)
    db_session.flush()
    secret = Message(
        conversation_id=other.id,
        sender_id=chat_story["stranger"].id,
        body="OTHER-CONVERSATION-PRIVATE-CANARY",
        request_token="other-private-token",
    )
    db_session.add(secret)
    db_session.commit()
    sign_in(chat_web, chat_story["buyer"])

    response = updates(
        chat_web, chat_story["conversation"].id, chat_story["messages"][0].id
    )
    assert response.status_code == 200
    assert b"OTHER-CONVERSATION-PRIVATE-CANARY" not in response.data


def test_polling_get_is_read_only(chat_web, db_session, chat_story):
    sign_in(chat_web, chat_story["buyer"])
    before = table_counts(db_session)
    for cursor in ("0", str(chat_story["messages"][0].id), "999999"):
        assert updates(chat_web, chat_story["conversation"].id, cursor).status_code == 200
    db_session.expire_all()
    assert table_counts(db_session) == before


def test_poll_query_count_is_bounded_for_large_thread(
    chat_web, db_app, db_session, chat_story
):
    add_messages(
        db_session,
        chat_story["conversation"],
        [chat_story["buyer"], chat_story["seller"]],
        1000,
        prefix="Scale",
    )
    sign_in(chat_web, chat_story["buyer"])
    statements = []

    def count_selects(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    with db_app.app_context():
        engine = db_app.extensions["sqlalchemy"].engine
        event.listen(engine, "before_cursor_execute", count_selects)
        try:
            response = updates(chat_web, chat_story["conversation"].id)
        finally:
            event.remove(engine, "before_cursor_execute", count_selects)

    assert response.status_code == 200
    assert len(response.get_json()["messages"]) == 50
    assert len(statements) <= 5


@pytest.mark.parametrize("status,composer", [("active", True), ("sold", True), ("archived", False)])
def test_status_policy_keeps_history_and_only_hides_archived_composer(
    chat_web, db_session, chat_story, status, composer
):
    chat_story["product"].status = status
    db_session.commit()
    sign_in(chat_web, chat_story["buyer"])
    response = chat_web.get(f'/messages/{chat_story["conversation"].id}')
    assert response.status_code == 200
    page = Page(response)
    assert bool(page.find("form", id="chat-composer")) is composer
    assert bool(page.find(id="chat-read-only")) is (not composer)
    assert len(message_ids(response.get_data(as_text=True))) == 2


def test_read_form_remains_explicit_and_participant_only(chat_web, chat_story):
    conversation_id = chat_story["conversation"].id
    latest = chat_story["messages"][-1]
    sign_in(chat_web, chat_story["buyer"])
    page = Page(chat_web.get(f"/messages/{conversation_id}"))
    form = page.one("form", id="chat-mark-read")
    assert form["attrs"]["method"].lower() == "post"
    assert page.one("input", id="chat-read-message-id")["attrs"]["value"] == str(latest.id)

    sign_in(chat_web, chat_story["stranger"])
    assert chat_web.post(
        f"/messages/{conversation_id}/read", data={"message_id": latest.id}
    ).status_code == 404

