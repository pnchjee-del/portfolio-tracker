from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Email

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class TransactionForm(FlaskForm):
    asset_name = StringField('Asset Name (e.g., Reliance, Gold 24K)', validators=[DataRequired()])
    asset_type = SelectField('Asset Type', choices=[('Stock', 'Stock'), ('Mutual Fund', 'Mutual Fund'), ('Bullion', 'Bullion')], validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[('BUY', 'Buy'), ('SELL', 'Sell')], validators=[DataRequired()])
    quantity = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0.0001, message='Quantity must be greater than zero')])
    price_per_unit = FloatField('Price Per Unit', validators=[DataRequired(), NumberRange(min=0.0, message='Price cannot be negative')])
    transaction_date = DateField('Transaction Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Log Transaction')

class RequestResetForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, message='Password must be at least 6 characters')])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Reset Password')