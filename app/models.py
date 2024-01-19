from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    marks = db.Column(db.Integer, index=True)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_marks(self):
        return self.marks if self.marks is not None else 0
    
    def set_marks(self, marks):
        self.marks = marks


    @classmethod
    def find_user_with_highest_marks(cls):
        user_with_highest_marks = cls.query.order_by(desc(cls.marks)).first()
        return user_with_highest_marks        

class Questions(db.Model):
    q_id = db.Column(db.Integer, primary_key=True)
    ques = db.Column(db.String(350), unique=True)
    a = db.Column(db.String(100))
    b = db.Column(db.String(100))
    c = db.Column(db.String(100))
    d = db.Column(db.String(100))
    ans = db.Column(db.String(100))

    def __repr__(self):
        return '<Question: {}>'.format(self.ques)
    

class City(db.Model) :
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50),nullable=False)