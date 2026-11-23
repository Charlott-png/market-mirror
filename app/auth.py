"""Identity is verified here; resource ownership is checked in feature routes."""

from flask import Blueprint, render_template, request, redirect, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.forms import RegistrationForm, LoginForm, ProfileForm
from app.models import User, InteractionEvent
from app.security import now, consume_limit, check_limit, safe_next

auth = Blueprint("auth", __name__)
DUMMY_HASH = generate_password_hash("unknown-account-timing-check-not-a-login")


@auth.route("/auth/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if request.method == "POST":
        consume_limit("register", request.remote_addr or "local", 5, 3600)
        if form.validate_on_submit():
            try:
                db.session.add(User(username=form.username.data, email=form.email.data,
                                    password_hash=generate_password_hash(form.password.data)))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                form.username.errors.append("Those account details cannot be registered. Try different details.")
            else:
                flash("Account created. Sign in to continue.")
                return redirect("/auth/login")
    return render_template("form.html", title="Create your account", form=form, submit="Create account"), (400 if request.method == "POST" else 200)


@auth.route("/auth/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        consume_limit("login-address", request.remote_addr or "local", 30, 900)
        email = (form.email.data or "").lower()
        check_limit("login-account", email, 5)
        if form.validate_on_submit():
            user = db.session.scalar(select(User).where(User.email == email))
            valid = check_password_hash(user.password_hash if user else DUMMY_HASH, form.password.data)
            if user and user.enabled and valid:
                session.clear()
                session.permanent = True
                login_user(user)
                session["login_at"] = now()
                return redirect(safe_next(request.args.get("next")))
        consume_limit("login-account", email, 5, 900)
        form.password.errors.append("Invalid email or password")
    return render_template("form.html", title="Sign in", form=form, submit="Sign in"), (400 if request.method == "POST" else 200)


@auth.post("/auth/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/")


@auth.route("/account/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user if request.method == "GET" else None)
    if form.validate_on_submit():
        current_user.bio = form.bio.data
        current_user.personalization = form.personalization.data
        if not current_user.personalization:
            db.session.execute(delete(InteractionEvent).where(InteractionEvent.user_id == current_user.id))
        db.session.commit()
        flash("Profile updated.")
        return redirect("/account/profile")
    return render_template("form.html", title="Your profile", form=form, submit="Save profile",
                           mobile_account_shortcuts=True), (400 if request.method == "POST" else 200)
