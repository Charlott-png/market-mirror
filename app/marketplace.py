"""Listing ownership and public catalogue routes."""

import secrets
from datetime import timezone
from urllib.parse import urlencode

from flask import Blueprint, abort, jsonify, render_template, request, redirect, flash, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import select, or_, func, text
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.forms import ListingForm, MessageForm, parse_price
from app.images import (discard_images, gallery_references, image_path,
                        selected_uploads, store_images, usable_gallery)
from app.models import Product, ProductImage, User, ListingSubmission
from app.models.product import CATEGORIES, CONDITIONS, STATUSES
from app.recently_viewed import recent_products as load_recent_products

market = Blueprint("market", __name__)
TRANSITIONS = {"active": {"sold", "archived"}, "sold": {"archived"}, "archived": {"active"}}


def locked_product(product_id):
    """Serialize status-sensitive writes on both supported databases."""
    if db.engine.dialect.name == "sqlite":
        db.session.execute(text("UPDATE products SET version = version WHERE id = :id"), {"id": product_id})
    return db.session.scalar(select(Product).where(Product.id == product_id).with_for_update()
                             .execution_options(populate_existing=True))


def owned_product(product_id):
    product = db.session.scalar(select(Product).where(Product.id == product_id, Product.seller_id == current_user.id))
    if product is None:
        abort(404)
    return product


def page_number(arguments=None):
    arguments = request.args if arguments is None else arguments
    raw = arguments.get("page", "1")
    if not raw.isascii() or not raw.isdigit() or len(raw) > 8 or int(raw) < 1:
        abort(400, description="Page must be a positive whole number.")
    return int(raw)


def paginate(statement, per_page=20, arguments=None):
    page = page_number(arguments)
    count = db.session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    if page > 1 and (page - 1) * per_page >= count:
        abort(404)
    items = db.session.scalars(statement.limit(per_page).offset((page - 1) * per_page)).unique().all()
    return dict(items=items, page=page, total=count, pages=max(1, (count + per_page - 1) // per_page))


BROWSE_ARGUMENTS = ("q", "category", "condition", "min_price", "max_price", "sort", "page")


def browse_context(arguments=None):
    """Validate one public search and return results plus a safe canonical query."""
    arguments = request.args if arguments is None else arguments
    if any(len(arguments.getlist(key)) > 1 for key in BROWSE_ARGUMENTS):
        abort(400, description="Supply each filter only once.")

    statement = select(Product).options(joinedload(Product.seller)).where(Product.status == "active")
    canonical = {}
    term = arguments.get("q", "").strip()
    if len(term) > 120:
        abort(400, description="Search is limited to 120 characters.")
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(or_(Product.title.ilike(f"%{escaped}%", escape="\\"),
                                       Product.description.ilike(f"%{escaped}%", escape="\\")))
        canonical["q"] = term

    for key, choices in (("category", CATEGORIES), ("condition", CONDITIONS)):
        value = arguments.get(key, "")
        if value:
            if value not in choices:
                abort(400, description="Choose a supported filter.")
            statement = statement.where(getattr(Product, key) == value)
            canonical[key] = value

    try:
        minimum = parse_price(arguments["min_price"]) if arguments.get("min_price") else None
        maximum = parse_price(arguments["max_price"]) if arguments.get("max_price") else None
    except ValueError:
        abort(400, description="Use a valid price range.")
    if minimum is not None and maximum is not None and minimum > maximum:
        abort(400, description="Minimum price must not exceed maximum price.")
    if minimum is not None:
        statement = statement.where(Product.price >= minimum)
        canonical["min_price"] = format(minimum, "f")
    if maximum is not None:
        statement = statement.where(Product.price <= maximum)
        canonical["max_price"] = format(maximum, "f")

    sorts = {"newest": Product.created_at.desc(), "price_asc": Product.price.asc(),
             "price_desc": Product.price.desc()}
    sort = arguments.get("sort", "newest")
    if sort not in sorts:
        abort(400, description="Choose a supported sort order.")
    if sort != "newest":
        canonical["sort"] = sort

    result = paginate(statement.order_by(sorts[sort], Product.id.desc()), arguments=arguments)
    if result["page"] > 1:
        canonical["page"] = result["page"]
    result["canonical_query"] = urlencode(canonical)
    return result


def render_listing(form, title, code=200, image_dropzone=False,
                   show_vision_ai=False, product=None):
    vision_ai_available = False
    vision_ai_provider_label = "AI provider"
    if show_vision_ai:
        from app.ai.vision import vision_available, vision_provider_label
        vision_ai_available = vision_available()
        vision_ai_provider_label = vision_provider_label()
    return render_template("form.html", title=title, form=form, submit="Save listing",
                           listing=True, image_dropzone=image_dropzone,
                           show_vision_ai=show_vision_ai,
                           current_gallery=usable_gallery(product) if product else [],
                           replacing_gallery=product is not None,
                           vision_ai_available=vision_ai_available,
                           vision_ai_provider_label=vision_ai_provider_label), code


@market.route("/listings/new", methods=["GET", "POST"])
@login_required
def create_listing():
    form = ListingForm()
    if request.method == "GET":
        form.request_token.data = secrets.token_urlsafe(24)
        return render_listing(form, "Sell a product", image_dropzone=True,
                              show_vision_ai=True)
    token = form.request_token.data
    if not token or len(token) > 100:
        abort(400, description="Please reopen the listing form.")
    prior = db.session.get(ListingSubmission, (current_user.id, token))
    if prior:
        return redirect(url_for("market.preview", product_id=prior.product_id))
    new_images = []
    if form.validate_on_submit():
        try:
            product = Product(seller_id=current_user.id, title=form.title.data,
                description=form.description.data, price=parse_price(form.price.data),
                category=form.category.data, condition=form.condition.data, currency="USD", status="active")
            new_images = store_images(form.image.data)
            product.image_filename = new_images[0] if new_images else None
            db.session.add(product)
            db.session.flush()
            product.gallery_images.extend(
                ProductImage(filename=filename, position=position)
                for position, filename in enumerate(new_images)
            )
            db.session.add(ListingSubmission(user_id=current_user.id, token=token, product_id=product.id))
            db.session.commit()
            return redirect(url_for("market.preview", product_id=product.id))
        except IntegrityError:
            db.session.rollback()
            discard_images(new_images)
            prior = db.session.get(ListingSubmission, (current_user.id, token))
            if prior:
                return redirect(url_for("market.preview", product_id=prior.product_id))
            form.title.errors.append("Could not save this listing. Please try again.")
        except ValueError as error:
            db.session.rollback()
            discard_images(new_images)
            form.image.errors.append(str(error))
        except (OSError, SQLAlchemyError):
            db.session.rollback()
            discard_images(new_images)
            form.image.errors.append("Could not save the listing or photos. Check their format, count, and size, then retry.")
    return render_listing(form, "Sell a product", 400, image_dropzone=True,
                          show_vision_ai=True)


@market.route("/listings/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(product_id):
    product = owned_product(product_id)
    if product.status == "sold":
        abort(400, description="Archive this sold listing before editing it.")
    form = ListingForm(obj=product if request.method == "GET" else None)
    if request.method == "GET":
        form.price.data = str(product.price)
        form.version.data = str(product.version)
        return render_listing(form, "Edit listing", image_dropzone=True,
                              product=product)
    if form.version.data != str(product.version):
        abort(409, description="This listing changed. Reload it before editing.")
    new_images = []
    old_images = gallery_references(product)
    if form.validate_on_submit():
        try:
            product.title, product.description = form.title.data, form.description.data
            product.price = parse_price(form.price.data)
            product.category, product.condition = form.category.data, form.condition.data
            if selected_uploads(form.image.data):
                new_images = store_images(form.image.data)
            if new_images:
                # Delete old gallery rows before inserting the same numbered
                # slots. The files themselves stay until the commit succeeds.
                product.gallery_images.clear()
                db.session.flush()
                product.gallery_images.extend(
                    ProductImage(filename=filename, position=position)
                    for position, filename in enumerate(new_images)
                )
                product.image_filename = new_images[0]
            db.session.commit()
            if new_images:
                discard_images(name for name in old_images if name not in new_images)
            return redirect(url_for("market.preview", product_id=product.id))
        except StaleDataError:
            db.session.rollback()
            discard_images(new_images)
            abort(409, description="This listing changed. Reload it before editing.")
        except ValueError as error:
            db.session.rollback()
            discard_images(new_images)
            form.image.errors.append(str(error))
        except (OSError, SQLAlchemyError):
            db.session.rollback()
            discard_images(new_images)
            form.image.errors.append("Unable to save changes. Your previous listing is unchanged.")
    return render_listing(form, "Edit listing", 400, image_dropzone=True,
                          product=product)


@market.post("/listings/<int:product_id>/status")
@login_required
def change_status(product_id):
    owned_product(product_id)
    product = locked_product(product_id)
    if request.form.get("version") != str(product.version):
        abort(409, description="This listing changed. Reload before updating.")
    target = request.form.get("status")
    if target == product.status:
        db.session.rollback()
        return redirect(url_for("market.preview", product_id=product_id))
    if target not in TRANSITIONS[product.status]:
        abort(400, description="That status transition is not allowed.")
    product.status = target
    try:
        db.session.commit()
    except StaleDataError:
        db.session.rollback()
        abort(409)
    return redirect(url_for("market.preview", product_id=product_id))


@market.get("/listings/<int:product_id>/preview")
@login_required
def preview(product_id):
    product = owned_product(product_id)
    return render_template("product.html", product=product, gallery=usable_gallery(product), preview=True,
                           transitions=TRANSITIONS, message_form=MessageForm())


@market.get("/account/listings")
@login_required
def own_listings():
    statement = select(Product).where(Product.seller_id == current_user.id)
    status = request.args.get("status", "")
    if status:
        if status not in STATUSES:
            abort(400)
        statement = statement.where(Product.status == status)
    return render_template("catalogue.html", title="Your listings", own=True,
                           **paginate(statement.order_by(Product.created_at.desc(), Product.id.desc())))


@market.get("/products")
def browse():
    viewed = (load_recent_products(current_user.id)
              if current_user.is_authenticated else [])
    return render_template("catalogue.html", title="Explore the marketplace", search=True,
                           recent_products=viewed, **browse_context())


@market.get("/products/search")
def live_search():
    try:
        context = browse_context()
    except HTTPException as error:
        response = jsonify(error="Choose valid search options.")
        response.status_code = error.code
        response.headers["Cache-Control"] = "no-store"
        return response

    total = context["total"]
    response = jsonify(
        results_html=render_template("_product_grid.html", **context),
        pagination_html=render_template("_catalogue_pagination.html", **context).strip(),
        total=total,
        count_label=f"{total} product" + ("" if total == 1 else "s"),
        page=context["page"],
        pages=context["pages"],
        canonical_query=context["canonical_query"],
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@market.get("/products/<int:product_id>")
def detail(product_id):
    product = db.session.scalar(select(Product).options(joinedload(Product.seller)).where(
        Product.id == product_id, Product.status.in_(["active", "sold"])))
    if product is None:
        abort(404)
    related_products = db.session.scalars(select(Product).options(
        joinedload(Product.seller)).where(
            Product.status == "active",
            Product.category == product.category,
            Product.id != product.id).order_by(func.random()).limit(3)).all()
    form = MessageForm()
    form.request_token.data = secrets.token_urlsafe(24)
    return render_template("product.html", product=product, gallery=usable_gallery(product),
                           message_form=form, transitions=TRANSITIONS,
                           related_products=related_products)


@market.get("/sellers/<username>")
def seller_profile(username):
    seller = db.session.scalar(select(User).where(User.username == username.lower()))
    if seller is None:
        abort(404)
    if len(request.args.getlist("page")) > 1:
        abort(400, description="Supply the page number only once.")
    statement = select(Product).options(joinedload(Product.seller)).where(
        Product.seller_id == seller.id, Product.status == "active")
    listing_page = paginate(statement.order_by(Product.created_at.desc(), Product.id.desc()))
    # One full seller-scoped count drives both the label and the activity badge.
    # len(items) would incorrectly remove the badge on a small final page.
    has_activity_badge = listing_page["total"] > 3
    joined = seller.created_at.astimezone(timezone.utc).date()
    months = ("January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December")
    joined_label = f"{joined.day} {months[joined.month - 1]} {joined.year}"
    return render_template("seller.html", seller=seller, has_activity_badge=has_activity_badge,
                           joined_iso=joined.isoformat(), joined_label=joined_label, **listing_page)


@market.get("/media/products/<filename>")
def media(filename):
    try:
        path = image_path(filename)
    except ValueError:
        abort(404)
    product = db.session.scalar(select(Product).outerjoin(ProductImage).where(
        or_(Product.image_filename == filename, ProductImage.filename == filename)))
    if product is None or (product.status == "archived" and
                           (not current_user.is_authenticated or current_user.id != product.seller_id)):
        abort(404)
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/jpeg", conditional=False, max_age=0)
