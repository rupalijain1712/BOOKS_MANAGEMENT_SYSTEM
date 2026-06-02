from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)
from flask import url_for

from flask import (
    Flask,
    render_template,
    request,
    redirect
)


from models.user import User
from config import Config
from database.db import db
from models.book import Book

app = Flask(__name__)

# For Login:

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

app.config.from_object(Config)

db.init_app(app)

# login for the user:
@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# The landing page of the website:
@app.route("/")
def home():

    latest_books = Book.query.order_by(
        Book.created_at.desc()
    ).limit(4).all()

    return render_template(
        "index.html",    #Code for the website is written in the index.html 
        latest_books=latest_books
    )

# Registerions Code:
@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        user = User(
            username=request.form["username"],
            email=request.form["email"],
            password=request.form["password"],
            role="customer"
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/books")

    return render_template("register.html") #Registeration html code is wriiten in register.html


# code for checking the login for the admin:
@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(
            email=email
        ).first()

        if user and user.password == password:

            login_user(user)

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect("/books")

        return "Invalid Credentials"

    return render_template("login.html")


# code for the add books:

@app.route("/add-book", methods=["GET", "POST"])
@login_required
def add_book():

    if current_user.role != "admin":
        return "Access Denied"

    if request.method == "POST":

        new_book = Book(
            title=request.form["title"],
            author=request.form["author"],
            category=request.form["category"],
            isbn=request.form["isbn"],
            price=float(request.form["price"]),
            stock=int(request.form["stock"])
        )

        db.session.add(new_book)
        db.session.commit()

        return redirect("/books")

    return render_template("add_book.html")
# manage users:
@app.route("/admin/users")
@login_required
def admin_users():

    if current_user.role != "admin":
        return "Access Denied"

    users = User.query.filter_by(
            role="customer"
        ).all()

    return render_template(
        "admin_users.html",
        users=users
    ) 

# edit books:

# delete books:

# code for the books that will showcase in the website
@app.route("/books")
def books():

    search = request.args.get("search")

    if search:

        all_books = Book.query.filter(
            Book.title.ilike(f"%{search}%")
        ).all()

    else:

        all_books = Book.query.all()

    return render_template(
        "books.html",
        books=all_books
    )

# code for the logout
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/")

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():

    if current_user.role != "admin":
        return "Access Denied"

    category = request.args.get("category")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    query = Book.query

    if category:
        query = query.filter(Book.category == category)

    if min_price:
        query = query.filter(Book.price >= float(min_price))

    if max_price:
        query = query.filter(Book.price <= float(max_price))

    books = query.all()

    categories = db.session.query(
        Book.category
    ).distinct().all()

    books_count = Book.query.count()

    users_count = User.query.filter_by(
        role="customer"
        ).count()

    return render_template(
        "admin_dashboard.html",
        books=books,
        categories=categories,
        books_count=books_count,
        users_count=users_count
    )
if __name__ == "__main__":
    app.run(debug=True)