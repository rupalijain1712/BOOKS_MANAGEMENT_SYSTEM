from database.db import db
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

class Book(db.Model):

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(255), nullable=False)

    author = db.Column(db.String(255), nullable=False)

    category = db.Column(db.String(100))

    isbn = db.Column(db.String(50), unique=True, nullable=True)

    price = db.Column(db.Float)

    stock = db.Column(db.Integer)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(IST)
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(IST),
        onupdate=lambda: datetime.now(IST)
    )