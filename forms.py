from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, validators, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

class CreateAccountForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    lastname = StringField('Lastname', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class DeleteAccountForm(FlaskForm):
    confirm_deletion = StringField('Type "DELETE" to confirm', validators=[DataRequired()])
    submit = SubmitField('Delete Account')

class BillingForm(FlaskForm):
    full_name = StringField('Full Name', [validators.DataRequired()])
    address = StringField('Address', [validators.DataRequired()])
    city = StringField('City', [validators.DataRequired()])
    state = StringField('State', [validators.DataRequired()])
    zip_code = StringField('Zip Code', [validators.DataRequired()])
    country = StringField('Country', [validators.DataRequired()])
    phone = StringField('Phone', [validators.DataRequired(), validators.Length(min=10, max=15)])

class CreditCardForm(FlaskForm):
    card_holder_name = StringField('Card Holder Name', [validators.DataRequired()])
    card_number = StringField('Card Number', [validators.DataRequired(), validators.Length(min=16, max=16)])
    expiry_month = IntegerField('Expiry Month', [validators.DataRequired(), validators.NumberRange(min=1, max=12)])
    expiry_year = IntegerField('Expiry Year', [validators.DataRequired(), validators.NumberRange(min=2021, max=2099)])
    cvv = StringField('CVV', [validators.DataRequired(), validators.Length(min=3, max=4)])

class AddProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    price = IntegerField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Product')

class UpdateOrderStatusForm(FlaskForm):
    order_id = IntegerField('Order ID', validators=[DataRequired()])
    status = SelectField('Status', choices=[('pending', 'Pending'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')])
    submit = SubmitField('Update Status')

class UpdateCartForm(FlaskForm):
    product_id = IntegerField('Product ID', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Update Cart')