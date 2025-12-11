from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_jwt_extended import JWTManager

app = Flask(__name__)

app.config['SECRET_KEY'] = '4f3a9cd9f3e8d12abf2e0fa8bcd213fa'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university.db'
app.config['JWT_SECRET_KEY'] = "super-secret-key"

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
jwt = JWTManager(app)


from finderapp import routes
