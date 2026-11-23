"""Create and configure the Market Mirror Flask application."""

from pathlib import Path

from flask import Flask, render_template, request, url_for, g
from flask_login import AnonymousUserMixin
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from config import Config, environment_settings, load_local_environment
from app.extensions import db, migrate, login_manager, csrf


def create_app(test_config=None):
    """Build and return a configured Flask application.

    ``test_config`` lets pytest safely change settings without changing the
    configuration used when a student runs the application normally.
    """
    application = Flask(__name__)

    # Waitress does not load Flask dotenv files. Local development does so here,
    # while pytest stays isolated from a student's real private .env file.
    if not (test_config and test_config.get("TESTING")):
        load_local_environment(Path(__file__).resolve().parent.parent)

    application.config.from_object(Config)
    if test_config and test_config.get("TESTING"):
        # A forgotten test URL must never fall back to DATABASE_URL or local data.
        application.config.update(APP_ENV="testing", SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SECRET_KEY="test-only-secret-not-for-production", UPLOAD_FOLDER=str(Path(application.instance_path) / "test-uploads"),
            AI_FOLDER=str(Path(application.instance_path) / "test-ai"))
    else:
        application.config.update(environment_settings(application.instance_path))

    if test_config is not None:
        application.config.from_mapping(test_config)

    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(application)
    login_manager.init_app(application)
    csrf.init_app(application)
    from app.security import initialize_security
    initialize_security(application)
    from app.models import Order, OrderItem, Product, ProductImage, User
    migration_path = Path(application.root_path).parent / "migrations"
    migrate.init_app(application, db, directory=str(migration_path))
    from app.commands import register_commands
    register_commands(application)

    @application.shell_context_processor
    def shell_objects():
        return {"db": db, "User": User, "Product": Product,
                "ProductImage": ProductImage,
                "Order": Order, "OrderItem": OrderItem}

    from app.routes import main_blueprint

    application.register_blueprint(main_blueprint)
    from app.auth import auth
    from app.marketplace import market
    from app.engagement import engagement
    from app.cart import cart
    from app.orders import orders
    application.register_blueprint(auth)
    application.register_blueprint(market)
    application.register_blueprint(engagement)
    application.register_blueprint(cart)
    application.register_blueprint(orders)
    from app.ai.routes import ai, register_ai_commands
    from app.operations import operations, register_maintenance
    application.register_blueprint(ai)
    application.register_blueprint(operations)
    register_ai_commands(application)
    register_maintenance(application)

    @application.context_processor
    def page_helpers():
        from flask_login import current_user
        from sqlalchemy import func, select
        from app.models import CartItem
        from app.models.product import CATEGORIES, CONDITIONS
        from app.images import image_exists
        from app.navigation import mobile_nav_section
        from app.ai.shop_assistant import shop_assistant_available

        def page_url(number, endpoint=None):
            allowed = {"q", "category", "condition", "min_price", "max_price", "sort", "status"}
            arguments = {key: value for key, value in request.args.items() if key in allowed}
            arguments.update(request.view_args or {})
            arguments["page"] = number
            return url_for(endpoint or request.endpoint, **arguments)
        if not current_user.is_authenticated:
            cart_count = 0
        else:
            # Key the request cache by owner as well as value. Tests keep an outer
            # application context, and this also makes an in-request identity
            # change incapable of showing the previous account's count.
            if g.get("cart_count_user_id") != current_user.id:
                g.cart_count = db.session.scalar(select(func.count()).select_from(CartItem).where(
                    CartItem.user_id == current_user.id))
                g.cart_count_user_id = current_user.id
            cart_count = g.cart_count
        return dict(categories=CATEGORIES, conditions=CONDITIONS, image_exists=image_exists,
                    page_url=page_url, cart_count=cart_count,
                    mobile_nav_section=mobile_nav_section,
                    shop_assistant_available=shop_assistant_available())

    @application.errorhandler(HTTPException)
    def http_error(error):
        db.session.rollback()
        return render_template("errors/generic.html", heading=error.name, explanation=error.description), error.code

    @application.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        g._login_user = AnonymousUserMixin()
        application.logger.warning("database_operation_failed")
        return render_template("errors/generic.html", heading="Temporarily unavailable",
                               explanation="We could not complete that request. Please try again."), 503

    @application.errorhandler(Exception)
    def unexpected_error(error):
        db.session.rollback()
        g._login_user = AnonymousUserMixin()
        # Do not log exception text/tracebacks: they may contain submitted data.
        application.logger.error("unexpected_request_failure type=%s id=%s", type(error).__name__, g.get("request_id", "none"))
        return render_template("errors/generic.html", heading="Something went wrong",
                               explanation="Please retry. If it continues, share the request ID with the operator."), 500

    @application.errorhandler(404)
    def page_not_found(error):
        """Render a friendly page while preserving the correct 404 status."""
        return render_template("errors/404.html"), 404

    return application
