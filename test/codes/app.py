
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

from models.order import Order
from models.order_item import OrderItem
from models.cart import Cart
from services.google_books import fetch_book_details
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
            book_name = request.form["book_name"]

            book_data = fetch_book_details(book_name)

            if not book_data:
                return "Book not found in Google Books"

            new_book = Book(
                title=book_data["title"],
                author=book_data["author"],
                category=request.form["category"],
                isbn=book_data.get("isbn") or None,
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
            
            # Update the timeline property dynamically on change to IST
            book.updated_at = datetime.now(IST)
            
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
@app.route("/add-to-cart/<int:book_id>")
@login_required
def add_to_cart(book_id):

    book = Book.query.get_or_404(book_id)

    cart_item = Cart.query.filter_by(
        user_id=current_user.id,
        book_id=book_id
    ).first()

    if cart_item:

        if cart_item.quantity < book.stock:
            cart_item.quantity += 1

    else:

        if book.stock > 0:

            cart_item = Cart(
                user_id=current_user.id,
                book_id=book_id,
                quantity=1
            )

            db.session.add(cart_item)

    db.session.commit()

    return redirect("/books")

@app.route("/cart")
@login_required
def cart():

    cart_items = Cart.query.filter_by(
        user_id=current_user.id
    ).all()
    total = 0
    cart_data = []

    for item in cart_items:

        book = Book.query.get(item.book_id)

        subtotal = book.price * item.quantity

        total += subtotal

        cart_data.append({
            "cart_id": item.id,
            "title": book.title,
            "price": book.price,
            "quantity": item.quantity,
            "subtotal": subtotal
    })

    return render_template(
        "cart.html",
        cart_data=cart_data,
        total=total
    )

@app.route("/checkout")
@login_required
def checkout():

    cart_items = Cart.query.filter_by(
        user_id=current_user.id
    ).all()

    if not cart_items:

        return redirect("/cart")

    total_amount = 0

    for item in cart_items:

        book = Book.query.get(item.book_id)

        if item.quantity > book.stock:

            return f"""
            Not enough stock for
            {book.title}
            """

        total_amount += (
            book.price * item.quantity
        )

    order = Order(
        user_id=current_user.id,
        total_amount=total_amount
    )

    db.session.add(order)
    db.session.commit()

    for item in cart_items:

        book = Book.query.get(item.book_id)

        order_item = OrderItem(

            order_id=order.id,

            book_id=book.id,

            quantity=item.quantity,

            price=book.price
        )

        db.session.add(order_item)

        # reduce stock

        book.stock -= item.quantity

        # clear cart

        db.session.delete(item)

    db.session.commit()

    return redirect(
        f"/order-success/{order.id}"
    )
@app.route(
    "/order-success/<int:order_id>"
)
@login_required
def order_success(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    return render_template(
        "order_success.html",
        order=order
    )

@app.route("/remove-from-cart/<int:cart_id>")
@login_required
def remove_from_cart(cart_id):

    cart_item = Cart.query.get_or_404(cart_id)

    if cart_item.user_id == current_user.id:

        db.session.delete(cart_item)

        db.session.commit()

    return redirect("/")
@app.route("/decrease-cart/<int:cart_id>")
@login_required
def decrease_cart(cart_id):

    cart_item = Cart.query.get_or_404(cart_id)

    if cart_item.user_id == current_user.id:

        if cart_item.quantity > 1:

            cart_item.quantity -= 1

        else:

            db.session.delete(cart_item)

        db.session.commit()

    return redirect("/cart")

@app.route("/increase-cart/<int:cart_id>")
@login_required
def increase_cart(cart_id):

    cart_item = Cart.query.get_or_404(cart_id)

    book = Book.query.get(cart_item.book_id)

    if cart_item.user_id == current_user.id:

        if cart_item.quantity < book.stock:

            cart_item.quantity += 1

            db.session.commit()

    return redirect("/cart")

@app.route("/my-orders")
@login_required
def my_orders():

    orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Order.id.desc()
    ).all()

    return render_template(
        "my_orders.html",
        orders=orders
    )
@app.route("/order-details/<int:order_id>")
@login_required
def order_details(order_id):

    order = Order.query.get_or_404(order_id)

    order_items = OrderItem.query.filter_by(
        order_id=order.id
    ).all()

    items = []

    for item in order_items:

        book = Book.query.get(item.book_id)

        items.append({
            "title": book.title,
            "quantity": item.quantity,
            "price": item.price
        })

    return render_template(
        "order_details.html",
        order=order,
        items=items
    )
@app.route("/dashboard")
@login_required
def dashboard():

    total_orders = Order.query.filter_by(
        user_id=current_user.id
    ).count()

    cart_items = Cart.query.filter_by(
        user_id=current_user.id
    ).count()

    orders = Order.query.filter_by(
        user_id=current_user.id
    ).all()

    books_bought = 0

    for order in orders:

        items = OrderItem.query.filter_by(
            order_id=order.id
        ).all()

        for item in items:

            books_bought += item.quantity

    recent_orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Order.id.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        cart_items=cart_items,
        books_bought=books_bought,
        recent_orders=recent_orders
    )


if __name__ == "__main__":
    app.run(debug=True)