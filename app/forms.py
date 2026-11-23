"""Form fields validate user input before model/database validation."""

from decimal import Decimal, InvalidOperation
import re

from email_validator import validate_email, EmailNotValidError
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import StringField, PasswordField, TextAreaField, SelectField, HiddenField, BooleanField
from wtforms.validators import InputRequired, Length, EqualTo, Regexp, ValidationError
from wtforms.fields.choices import SelectChoice

from app.models.product import CATEGORIES, CONDITIONS
from app.models.types import validated_price


def strip(value):
    return value.strip() if isinstance(value, str) else value


def email_structure(form, field):
    try:
        validate_email(field.data, check_deliverability=False, test_environment=True)
    except EmailNotValidError:
        raise ValidationError("Enter a valid email address.") from None


def parse_price(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d{1,2})?", value.strip(), re.ASCII):
        raise ValueError("Enter a positive price with at most two decimal places.")
    try:
        return validated_price(Decimal(value.strip()))
    except (InvalidOperation, ValueError):
        raise ValueError("Price must be between 0.01 and 9999999.99.") from None


class RegistrationForm(FlaskForm):
    username = StringField("Username", filters=[strip], validators=[InputRequired(), Length(3, 30), Regexp(r"^[A-Za-z0-9_-]+$")])
    email = StringField("Email", filters=[strip], validators=[InputRequired(), Length(max=254), email_structure])
    password = PasswordField("Password (12–128 characters)", validators=[InputRequired(), Length(12, 128)])
    confirm_password = PasswordField("Confirm password", validators=[InputRequired(), EqualTo("password")])


class LoginForm(FlaskForm):
    email = StringField("Email", filters=[strip], validators=[InputRequired(), Length(max=254)])
    password = PasswordField("Password", validators=[InputRequired(), Length(max=128)])


class ProfileForm(FlaskForm):
    bio = TextAreaField("About you", filters=[strip], validators=[Length(max=500)])
    personalization = BooleanField("Allow my views, saves and contacts to personalize recommendations for 90 days")


class ListingForm(FlaskForm):
    title = StringField("Title", filters=[strip], validators=[InputRequired(), Length(3, 120)])
    description = TextAreaField("Description", filters=[strip], validators=[InputRequired(), Length(10, 5000)])
    price = StringField("Price (USD)", filters=[strip], validators=[InputRequired(), Length(max=20)])
    category = SelectField("Category", choices=[SelectChoice(value=key, label=label) for key, label in CATEGORIES.items()])
    condition = SelectField("Condition", choices=[SelectChoice(value=key, label=label) for key, label in CONDITIONS.items()])
    image = MultipleFileField("Optional product photos (up to five JPEG or PNG files)")
    version = HiddenField()
    request_token = HiddenField(validators=[Length(max=100)])

    def validate_price(self, field):
        try:
            parse_price(field.data)
        except ValueError as error:
            raise ValidationError(str(error)) from None


class MessageForm(FlaskForm):
    body = TextAreaField("Message", filters=[strip], validators=[InputRequired(), Length(1, 2000)])
    request_token = HiddenField(validators=[InputRequired(), Length(1, 100)])
