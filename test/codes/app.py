from flask import (
    Flask,
    render_template,
    request,
    redirect
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)


from models.user import User
from config import Config
from database.db import db
from models.book import Book

app = Flask(__name__)
login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

app.config.from_object(Config)

db.init_app(app)

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route("/")
def home():

    return redirect("/books")


@app.route("/add-book", methods=["GET","POST"])
@login_required
def add_book():

    if request.method == "POST":

        new_book = Book(

            title=request.form["title"],

            author=request.form["author"],

            category=request.form["category"],

            isbn=request.form["isbn"],

            price=request.form["price"],

            stock=request.form["stock"]

        )

        db.session.add(new_book)

        db.session.commit()

        return redirect("/books")

    return render_template("add_book.html")

@app.route("/books")
@login_required
def books():

    all_books = Book.query.all()

    return render_template(
        "books.html",
        books=all_books
    )

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)