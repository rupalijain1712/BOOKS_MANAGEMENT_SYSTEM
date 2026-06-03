
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone

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
        Book.id.desc()
    ).limit(4).all()

    categories = db.session.query(
        Book.category
    ).distinct().all()

    return render_template(
        "index.html",
        latest_books=latest_books,
        categories=categories
    )


# Registrations Code:
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
    # 1. Security Check
    if current_user.role != "admin":
        return "Access Denied", 403

    # 2. Handle Form Submission
    if request.method == "POST":
        try:
            # Create the new Book instance from form data
            new_book = Book(
                title=request.form["title"],
                author=request.form["author"],
                category=request.form["category"],
                isbn=request.form["isbn"],
                price=float(request.form["price"]),
                stock=int(request.form["stock"])
            )

            # Stage and commit to MySQL
            db.session.add(new_book)
            db.session.commit()

            # Success! Redirect back to the inventory
            return redirect("/books")

        except Exception as e:
            # CRITICAL: Roll back the transaction to clean up the broken database session
            db.session.rollback()
            
            # Print the error to your VS Code console for debugging
            print(f"Database Error: {e}")
            
            # Return a friendly error message to the user instead of a generic 500 crash page
            return f"An error occurred while adding the book. It might be due to a duplicate ISBN number. Error: {e}", 400

    # 3. Handle GET request (Render the actual form page)
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
# Make sure your app.py imports timezone utility at the very top:
# from datetime import datetime, timezone

@app.route("/edit-book/<int:id>", methods=["GET", "POST"])
@login_required
def edit_book(id):
    book = Book.query.get_or_404(id)
    
    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":
        try:
            book.title = request.form["title"]
            book.author = request.form["author"]
            book.isbn = request.form["isbn"]
            book.price = float(request.form["price"])
            book.stock = int(request.form["stock"])
            book.category = request.form["category"]
            
            # Update the timeline property dynamically on change
            book.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            db.session.rollback()
            return f"There was an error updating the book: {e}"

    return render_template("edit_book.html", book=book)

# delete books:
@app.route("/delete-book/<int:id>", methods=["GET", "POST"])
@login_required
def delete_book(id):
    # 1. Security check: Ensure only logged-in administrators can delete inventory
    if current_user.role != "admin":
        return "Access Denied", 403

    # 2. Retrieve the specific book from MySQL or throw a 404 error if it doesn't exist
    book_to_delete = Book.query.get_or_404(id)

    try:
        # 3. Tell SQLAlchemy to stage this record for deletion
        db.session.delete(book_to_delete)
        
        # 4. Commit the transaction to permanently remove the row from MySQL
        db.session.commit()
        
        # 5. Redirect the administrator back to the dashboard to show the updated table
        return redirect(url_for("admin_dashboard"))
        
    except Exception as e:
        # If something goes wrong with the database connection, safely undo the staging
        db.session.rollback()
        return f"There was an error deleting the book: {e}", 500


# code for the books that will showcase in the website
@app.route("/books")
def books():

    search = request.args.get("search")
    category = request.args.get("category")

    query = Book.query

    if search:

        query = query.filter(
            Book.title.ilike(f"%{search}%")
        )

    if category:

        query = query.filter_by(
            category=category
        )

    all_books = query.all()

    categories = db.session.query(
        Book.category
    ).distinct().all()

    return render_template(
        "books.html",
        books=all_books,
        categories=categories
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