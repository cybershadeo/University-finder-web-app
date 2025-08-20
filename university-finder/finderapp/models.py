from finderapp import db, login_manager
from flask_login import UserMixin
import datetime

@login_manager.user_loader
def loader_user(user_id):
    return Users.query.get(int(user_id)) 


class Users(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key = True)
    username = db.Column(db.String(20),unique = True,nullable = False)
    email = db.Column(db.String(100),unique = True, nullable = False)
    password = db.Column(db.String,nullable = False)
    

    def __repr__(self):
        return f"User('{self.username}','{self.email}')"
    



class Universities(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    name = db.Column(db.String(150),nullable = False)
    domain = db.Column(db.String(150),unique = True)
    website = db.Column(db.String(150),unique = True)
    country = db.Column(db.String(100),nullable = False)




class Favorites(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    user_id = db.Column(db.Integer,db.ForeignKey('users.id'),nullable = False)
    university_id = db.Column(db.Integer,db.ForeignKey('universities.id'),nullable = False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    __table_args__ = (
    db.UniqueConstraint('user_id', 'university_id', name='unique_user_university'),
)

    
    user = db.relationship('Users', backref='favorites', lazy=True)
    university = db.relationship('Universities', backref='favorites', lazy=True)