from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,BooleanField
from wtforms.validators import DataRequired,Length,Email,EqualTo,ValidationError
from finderapp.models import Users


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                            validators=[DataRequired(),Length(min=2,max=20)])
    email = StringField('Email', 
                        validators=[DataRequired(), Email()]) 
    password = PasswordField('Password', 
                             validators=[DataRequired(),Length(min=6, max=10)])
    confirm_password = PasswordField('Confirm password', 
                                     validators=[DataRequired(),EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign up')

    def validate_username(self,username):
        user = Users.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is taken.Please choose another one')
        
    def validate_email(self,email):
        user = Users.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email is taken.Please choose another one')


class LoginForm(FlaskForm):
    login = StringField('Username or Email',
                            validators=[DataRequired(),Length(min=2,max=20)])
    password = PasswordField('Password', 
                             validators=[DataRequired(),Length(min=6, max=10)])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign in')