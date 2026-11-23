"""Private messages, saved products, consented events, and personal summaries."""

from datetime import datetime, timezone
import secrets

from flask import (Blueprint, abort, request, render_template, redirect, url_for,
                   current_app, jsonify)
from flask_login import current_user, login_required
from sqlalchemy import select, or_, and_, func, delete, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.forms import MessageForm
from app.marketplace import locked_product, paginate, page_number
from app.models import Product, User, Conversation, Message, ReadMarker, SavedProduct, InteractionEvent
from app.recently_viewed import record_recent_view, recent_products
from app.security import now, consume_limit

engagement = Blueprint("engagement", __name__)

CHAT_PAGE_SIZE = 50
MAX_MESSAGE_CURSOR = 9_223_372_036_854_775_807


def participant(conversation_id):
    result = db.session.scalar(select(Conversation).where(Conversation.id == conversation_id,
        or_(Conversation.buyer_id == current_user.id, Conversation.seller_id == current_user.id)))
    if result is None:
        abort(404)
    return result


def record_event(product_id, kind):
    """Optional analytics starts AFTER the essential user action has committed."""
    try:
        user_id = current_user.id
        if db.engine.dialect.name == "sqlite":
            db.session.execute(text("UPDATE users SET id = id WHERE id = :id"), {"id": user_id})
        user = db.session.scalar(select(User).where(User.id == user_id).with_for_update()
                                 .execution_options(populate_existing=True))
        product = db.session.get(Product, product_id)
        if not user.personalization or not product or product.seller_id == user_id:
            db.session.rollback()
            return
        timestamp = now()
        # Check the rolling window as well as the unique fixed bucket. This avoids
        # double events around a bucket boundary and serializes on the user row.
        recent = db.session.scalar(select(InteractionEvent.id).where(
            InteractionEvent.user_id == user_id, InteractionEvent.product_id == product_id,
            InteractionEvent.kind == kind,
            InteractionEvent.created_at > datetime.fromtimestamp(timestamp - 1800, timezone.utc)))
        if recent is None:
            db.session.add(InteractionEvent(user_id=user_id, product_id=product_id, kind=kind,
                window=int(timestamp // 1800), created_at=datetime.fromtimestamp(timestamp, timezone.utc)))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.warning("optional_event_unavailable")


def write_message(conversation, form):
    prior = db.session.scalar(select(Message).where(Message.sender_id == current_user.id,
                                                    Message.request_token == form.request_token.data))
    if prior:
        if prior.conversation_id != conversation.id:
            abort(409, description="Use a fresh message form.")
        return
    db.session.add(Message(conversation_id=conversation.id, sender_id=current_user.id,
                          body=form.body.data, request_token=form.request_token.data))


def invalid_message(form):
    """Keep escaped, non-secret text available so the writer can correct it."""
    if form.request_token.errors:
        form.request_token.data = secrets.token_urlsafe(24)
        form.body.errors.append("Please review your message and submit this fresh form.")
    return render_template("form.html", title="Correct your message", form=form, submit="Send message"), 400


def message_time_parts(value):
    """Return one predictable UTC value for HTML and JSON chat timestamps."""
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return {
        "created_at": value.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "fallback_time": value.strftime("%I:%M %p UTC").lstrip("0"),
    }


def message_payload(message):
    """Serialize only the chat fields approved by MM-029."""
    return {
        "id": message.id,
        "body": message.body,
        "sender_username": message.sender.username,
        "is_own": message.sender_id == current_user.id,
        **message_time_parts(message.created_at),
    }


def message_cursor():
    """Read one bounded ASCII integer without looking up another message."""
    values = request.args.getlist("after_id")
    if len(values) != 1:
        return None
    raw = values[0]
    if (not raw or len(raw) > 19 or not raw.isascii() or not raw.isdigit()):
        return None
    value = int(raw)
    return value if value <= MAX_MESSAGE_CURSOR else None


@engagement.post("/products/<int:product_id>/contact")
@login_required
def contact(product_id):
    form = MessageForm()
    if not form.validate_on_submit():
        return invalid_message(form)
    consume_limit("message", str(current_user.id), 20, 600)
    product = locked_product(product_id)
    if product is None or product.status == "archived":
        abort(404)
    if product.seller_id == current_user.id or product.status != "active":
        abort(400, description="You can contact another seller about an active product.")
    conversation = db.session.scalar(select(Conversation).where(Conversation.product_id == product_id,
                                                               Conversation.buyer_id == current_user.id))
    if conversation is None:
        conversation = Conversation(product_id=product_id, buyer_id=current_user.id, seller_id=product.seller_id)
        db.session.add(conversation)
        db.session.flush()
    write_message(conversation, form)
    db.session.commit()
    conversation_id = conversation.id
    record_event(product_id, "contact")
    return redirect(url_for("engagement.thread", conversation_id=conversation_id))


@engagement.get("/messages")
@login_required
def inbox():
    statement = select(Conversation).options(joinedload(Conversation.product)).where(
        or_(Conversation.buyer_id == current_user.id, Conversation.seller_id == current_user.id))
    return render_template("inbox.html", **paginate(statement.order_by(Conversation.created_at.desc(), Conversation.id.desc())))


@engagement.get("/messages/<int:conversation_id>")
@login_required
def thread(conversation_id):
    conversation = participant(conversation_id)
    form = MessageForm()
    form.request_token.data = secrets.token_urlsafe(24)
    page = page_number()
    total = db.session.scalar(select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id))
    pages = max(1, (total + CHAT_PAGE_SIZE - 1) // CHAT_PAGE_SIZE)
    if page > 1 and (page - 1) * CHAT_PAGE_SIZE >= total:
        abort(404)
    newest_first = db.session.scalars(select(Message).options(joinedload(Message.sender)).where(
        Message.conversation_id == conversation_id).order_by(
            Message.created_at.desc(), Message.id.desc()).limit(CHAT_PAGE_SIZE).offset(
                (page - 1) * CHAT_PAGE_SIZE)).unique().all()
    items = list(reversed(newest_first))
    times = {message.id: message_time_parts(message.created_at) for message in items}
    return render_template(
        "conversation.html", conversation=conversation, form=form, items=items,
        page=page, pages=pages, total=total, message_times=times,
        latest_message_id=max((message.id for message in items), default=0),
        live_updates=page == 1)


@engagement.get("/messages/<int:conversation_id>/updates")
@login_required
def message_updates(conversation_id):
    participant(conversation_id)
    after_id = message_cursor()
    if after_id is None:
        response = jsonify(error="Invalid message cursor.")
        response.status_code = 400
        response.headers["Cache-Control"] = "no-store"
        return response
    rows = db.session.scalars(select(Message).options(joinedload(Message.sender)).where(
        Message.conversation_id == conversation_id, Message.id > after_id).order_by(
            Message.created_at, Message.id).limit(CHAT_PAGE_SIZE + 1)).unique().all()
    messages = rows[:CHAT_PAGE_SIZE]
    response = jsonify(
        messages=[message_payload(message) for message in messages],
        latest_id=max((message.id for message in messages), default=after_id),
        has_more=len(rows) > CHAT_PAGE_SIZE,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@engagement.post("/messages/<int:conversation_id>/send")
@login_required
def reply(conversation_id):
    conversation = participant(conversation_id)
    form = MessageForm()
    if not form.validate_on_submit():
        return invalid_message(form)
    consume_limit("message", str(current_user.id), 20, 600)
    product = locked_product(conversation.product_id)
    if product.status == "archived":
        abort(400, description="This archived product's conversation is read-only.")
    write_message(conversation, form)
    db.session.commit()
    return redirect(url_for("engagement.thread", conversation_id=conversation_id))


@engagement.post("/messages/<int:conversation_id>/read")
@login_required
def mark_read(conversation_id):
    conversation = participant(conversation_id)
    try:
        message_id = int(request.form.get("message_id", ""))
    except ValueError:
        abort(400)
    message = db.session.get(Message, message_id)
    if not message or message.conversation_id != conversation_id:
        abort(400)
    locked_product(conversation.product_id)
    marker = db.session.get(ReadMarker, (conversation_id, current_user.id))
    if marker:
        marker.last_read_message_id = max(marker.last_read_message_id, message_id)
    else:
        db.session.add(ReadMarker(conversation_id=conversation_id, user_id=current_user.id,
                                  last_read_message_id=message_id))
    db.session.commit()
    return redirect(url_for("engagement.thread", conversation_id=conversation_id))


@engagement.post("/products/<int:product_id>/save")
@login_required
def save(product_id):
    product = locked_product(product_id)
    if product is None or product.status == "archived":
        abort(404)
    if product.status != "active" or product.seller_id == current_user.id:
        abort(400, description="Save an available product offered by someone else.")
    if db.session.get(SavedProduct, (current_user.id, product_id)) is None:
        db.session.add(SavedProduct(user_id=current_user.id, product_id=product_id))
    db.session.commit()
    record_event(product_id, "save")
    return redirect("/saved")


@engagement.post("/products/<int:product_id>/unsave")
@login_required
def unsave(product_id):
    db.session.execute(delete(SavedProduct).where(SavedProduct.user_id == current_user.id,
                                                SavedProduct.product_id == product_id))
    db.session.commit()
    return redirect("/saved")


@engagement.get("/saved")
@login_required
def saved():
    statement = select(SavedProduct).options(joinedload(SavedProduct.product)).where(SavedProduct.user_id == current_user.id)
    return render_template("saved.html", **paginate(statement.order_by(SavedProduct.created_at.desc(), SavedProduct.product_id.desc())))


@engagement.post("/products/<int:product_id>/view")
@login_required
def viewed(product_id):
    product = db.session.get(Product, product_id)
    if product is None or product.status != "active":
        abort(404)
    try:
        if not record_recent_view(current_user.id, product_id):
            db.session.rollback()
            abort(404)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.warning("recent_product_view_unavailable")
        abort(503, description="Viewing history is temporarily unavailable.")
    record_event(product_id, "view")
    return "", 204


@engagement.get("/dashboard")
@login_required
def dashboard():
    uid = current_user.id
    counts = dict(db.session.execute(select(Product.status, func.count(Product.id))
                                    .where(Product.seller_id == uid).group_by(Product.status)).all())
    saves = db.session.scalar(select(func.count()).select_from(SavedProduct).where(SavedProduct.user_id == uid))
    unread = db.session.scalar(select(func.count(func.distinct(Conversation.id))).join(
        Message, Message.conversation_id == Conversation.id).outerjoin(ReadMarker, and_(
        ReadMarker.conversation_id == Conversation.id, ReadMarker.user_id == uid)).where(
        or_(Conversation.buyer_id == uid, Conversation.seller_id == uid), Message.sender_id != uid,
        Message.id > func.coalesce(ReadMarker.last_read_message_id, 0)))
    products = db.session.scalars(select(Product).where(Product.seller_id == uid)
        .order_by(Product.updated_at.desc(), Product.id.desc()).limit(5)).all()
    conversations = db.session.scalars(select(Conversation).options(joinedload(Conversation.product)).where(
        or_(Conversation.buyer_id == uid, Conversation.seller_id == uid))
        .order_by(Conversation.id.desc()).limit(5)).all()
    return render_template("dashboard.html", counts=counts, save_count=saves, unread=unread,
                           products=products, conversations=conversations,
                           recent_products=recent_products(uid))
