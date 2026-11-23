"""MM-002 tests for safe and repeatable fictional seed data."""


def test_seed_creates_varied_fictional_dataset(db_app):
    """TEST-SEED-001 / AC-DB-008: seed data is varied and safe."""
    from app.extensions import db
    from app.models import Product, User

    result = db_app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code == 0, result.output
    assert "password" not in result.output.lower()

    with db_app.app_context():
        users = db.session.query(User).all()
        products = db.session.query(Product).all()

        assert len(users) >= 3
        assert len(products) >= 12
        assert len({product.seller_id for product in products}) >= 3
        assert len({product.category for product in products}) >= 4
        assert {"active", "sold", "archived"} <= {
            product.status for product in products
        }
        assert all(user.email.endswith("@example.test") for user in users)
        assert all(len(user.password_hash) > 20 for user in users)
        assert all("password" not in user.password_hash.lower() for user in users)


def test_second_seed_run_creates_no_duplicates(db_app):
    """TEST-SEED-002: re-running seed keeps stable row counts."""
    from app.extensions import db
    from app.models import Product, User

    runner = db_app.test_cli_runner()
    first = runner.invoke(args=["seed"])
    with db_app.app_context():
        first_counts = (
            db.session.query(User).count(),
            db.session.query(Product).count(),
        )

    second = runner.invoke(args=["seed"])
    with db_app.app_context():
        second_counts = (
            db.session.query(User).count(),
            db.session.query(Product).count(),
        )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert second_counts == first_counts


def test_seed_preserves_unrelated_records(db_app, user_factory, product_factory):
    """TEST-SEED-003: seed never deletes student-created data."""
    from app.extensions import db
    from app.models import Product, User

    unrelated_user = user_factory(
        username="unrelated-user",
        email="unrelated-user@example.test",
    )
    unrelated_product = product_factory(
        seller=unrelated_user,
        title="Unrelated product that must survive",
    )
    user_id = unrelated_user.id
    product_id = unrelated_product.id

    result = db_app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code == 0, result.output
    with db_app.app_context():
        assert db.session.get(User, user_id).username == "unrelated-user"
        assert db.session.get(Product, product_id).title == (
            "Unrelated product that must survive"
        )


def test_seed_failure_rolls_back_entire_transaction(db_app, monkeypatch):
    """TEST-SEED-004: one seed failure leaves no partial seed rows."""
    from app.extensions import db
    from app.models import Product, User

    real_commit = db.session.commit

    def fail_commit():
        raise RuntimeError("intentional seed commit failure")

    monkeypatch.setattr(db.session, "commit", fail_commit)
    result = db_app.test_cli_runner().invoke(args=["seed"])
    monkeypatch.setattr(db.session, "commit", real_commit)

    assert result.exit_code != 0

    with db_app.app_context():
        db.session.rollback()
        assert db.session.query(User).count() == 0
        assert db.session.query(Product).count() == 0

        user = User(
            username="after-failure",
            email="after-failure@example.test",
            password_hash="secure-test-hash-after-failure",
        )
        db.session.add(user)
        db.session.commit()
        assert user.id is not None
