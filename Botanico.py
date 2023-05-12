from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from flask_mail import Mail, Message
from functools import wraps
from urllib.parse import urlsplit
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from forms import CreateAccountForm, ChangePasswordForm, BillingForm, CreditCardForm, AddProductForm, UpdateCartForm, UpdateOrderStatusForm
import cosmosdb
from DBcosmos import STRIPE_SECRET_KEY
import datetime
import stripe


app = Flask(__name__)
app.config['SECRET_KEY'] = 'fff'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'selva.plantasCRE@gmail.com'
app.config['MAIL_PASSWORD'] = 'CRE2023123!'
app.config['MAIL_DEFAULT_SENDER'] = 'selva.plantasCRE@gmail.com'

mail = Mail(app)

stripe.api_key = STRIPE_SECRET_KEY

class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    cosmos_db = cosmosdb.CosmosDB()
    user = cosmos_db.get_user_by_id(user_id)
    if user:
        return User(user['id'], user['email'])
    return None

cosmos_db = cosmosdb.CosmosDB()
def get_user(email):
    return cosmos_db.get_user_by_email(email)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in as admin to access this page.', 'danger')
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    cosmos_db = cosmosdb.CosmosDB()
    products = cosmos_db.get_all_products()
    return render_template('home.html', products=products)


@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    form = CreateAccountForm()
    if form.validate_on_submit():
        name = form.name.data
        lastname = form.lastname.data
        email = form.email.data
        password = form.password.data
        password_hash = generate_password_hash(password)  # Hash the password
        cosmos_db = cosmosdb.CosmosDB()
        existing_user = cosmos_db.get_user_by_email(email)  # Check if user already exists by email
        if existing_user:
            flash('Email address already exists. Please log in or use a different email address.', 'danger')
            return redirect(url_for('create_account.html'))
        print(f"Creating user with email: {email} and hashed password: {password_hash}")
        cosmos_db.create_user(name, lastname, email, password_hash)  # Save the hashed password
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('create_account.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Login route accessed")
    if current_user.is_authenticated:
        print("User already authenticated, redirecting to dashboard")
        return redirect(url_for('dashboard.html'))

    if request.method == 'POST':
        print("Login form submitted")
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember_me', False)

        cosmos_db = cosmosdb.CosmosDB()
        user = cosmos_db.get_user_by_email(email)

        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['email'])
            login_user(user_obj, remember=remember)
            print("User authenticated, redirecting to next_page or dashboard")
            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('dashboard.html')
            return redirect(next_page)
        else:
            print("Invalid email or password")
            flash('Invalid email or password')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    cosmos_db = cosmosdb.CosmosDB()
    user_id = current_user.id
    order_history = cosmos_db.get_order_history_by_user(user_id)
    billing_info = cosmos_db.get_billing_info(user_id)
    return render_template('dashboard.html', order_history=order_history, billing_info=billing_info)


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message_text = request.form['message']

        # Send the email to the site owner
        message = Message(subject, recipients=['site_owner_email@example.com'])
        message.body = f"Name: {name}\nEmail: {email}\n\n{message_text}"
        mail.send(message)

        # Show a success message to the user
        flash('Your message has been sent. We will get back to you shortly.', 'success')

    return render_template('contacts.html')


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        cosmos_db = cosmosdb.CosmosDB()

        if current_user.check_password(current_password):
            cosmos_db.update_user(current_user.id, {'password': new_password})
            flash('Your password has been updated successfully!', 'success')
            return redirect(url_for('account'))
        else:
            flash('Current password is incorrect. Please try again.', 'danger')
    return render_template('change_password.html', form=form)


@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user_id = current_user.id
    cosmos_db = cosmosdb.CosmosDB()

    # Delete the user's billing information from the database
    cosmos_db.delete_billing_info(user_id)

    # Delete the user's account from the database
    cosmos_db.delete_user(user_id)

    # Log out the user
    logout_user()

    # Redirect the user to the home page with a message indicating that their account has been deleted
    flash('Your account has been deleted.', 'success')
    return redirect(url_for('home'))


@app.route('/about_us')
def about_us():
    return render_template('about_us.html')


@app.route('/cart_shop')
@login_required
def cart_shop():
    user_id = current_user.id
    cosmos_db = cosmosdb.CosmosDB()

    # Get the items in the user's cart from the database
    items_in_cart = cosmos_db.get_items_in_cart(user_id)

    # Calculate the total price of the items in the cart
    total_price = sum(item['price'] for item in items_in_cart)

    return render_template('cart_shop.html', items_in_cart=items_in_cart, total_price=total_price)


@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    user = get_user(current_user.email)
    billing_info = user.get('billing_info', None)
    credit_card_info = user.get('credit_card_info', None)

    if request.method == 'POST':
        form = BillingForm(request.form)
        if form.validate():
            update_billing_info(current_user.email, form.data)
            flash('Billing information updated successfully.', 'success')
            return redirect(url_for('billing'))

    return render_template('billing.html', billing_info=billing_info, credit_card_info=credit_card_info)


@app.route('/update_billing_info', methods=['POST'])
@login_required
def update_billing_info():
    form = BillingForm(request.form)
    if form.validate():
        cosmos_db = cosmosdb.CosmosDB()  
        cosmos_db.update_billing_info_in_db(current_user.email, form.data)  # Change this line
        flash('Billing information updated successfully.', 'success')
    else:
        flash('Failed to update billing information. Please check the entered data.', 'danger')
    return redirect(url_for('billing'))


@app.route('/remove_billing_info', methods=['POST'])
@login_required
def remove_billing_info():
    cosmos_db = cosmosdb.CosmosDB() 
    cosmos_db.remove_billing_info_from_db(current_user.email)
    flash('Billing information removed successfully.', 'success')
    return redirect(url_for('billing'))


@app.route('/add_credit_card_info', methods=['POST'])
@login_required
def add_credit_card_info():
    form = CreditCardForm(request.form)
    if form.validate():
        cosmos_db = cosmosdb.CosmosDB() 
        cosmos_db.add_credit_card_info_to_db(current_user.email, form.data)
        flash('Credit card information added successfully.', 'success')
    else:
        flash('Failed to add credit card information. Please check the entered data.', 'danger')
    return redirect(url_for('billing'))


@app.route('/update_credit_card_info', methods=['POST'])
@login_required
def update_credit_card_info():
    form = CreditCardForm(request.form)
    if form.validate():
        cosmos_db = cosmosdb.CosmosDB() 
        cosmos_db.update_credit_card_info_in_db(current_user.email, form.data)
        flash('Credit card information updated successfully.', 'success')
    else:
        flash('Failed to update credit card information. Please check the entered data.', 'danger')
    return redirect(url_for('billing'))


@app.route('/remove_credit_card_info', methods=['POST'])
@login_required
def remove_credit_card_info():
    cosmos_db = cosmosdb.CosmosDB() 
    cosmos_db.remove_credit_card_info_from_db(current_user.email)
    flash('Credit card information removed successfully.', 'success')
    return redirect(url_for('billing'))


# Product details page
@app.route('/product/<product_id>')
def product(product_id):
    cosmos_db = cosmosdb.CosmosDB()
    product = cosmos_db.get_product_by_id(product_id)
    if product:
        return render_template('product.html', product=product)
    else:
        flash("Product not found.", "danger")
        return redirect(url_for('home'))


# Order history page
@app.route('/order_history')
@login_required
def order_history():
    user_id = current_user.id
    cosmos_db = cosmosdb.CosmosDB()
    orders = cosmos_db.get_order_history_by_user(user_id)
    return render_template('order_history.html', orders=orders)


# Order details page
@app.route('/order/<order_id>')
@login_required
def order_details(order_id):
    cosmos_db = cosmosdb.CosmosDB()
    order = cosmos_db.get_order_by_id(order_id) 
    
    # Check if the order belongs to the current user
    if order and order['user_id'] == current_user.id:
        return render_template('order_details.html', order=order)
    else:
        flash('Order not found or you do not have permission to view this order.', 'danger')
        return redirect(url_for('order_history'))


# Order confirmation page
@app.route('/order_confirmation', methods=['POST'])
@login_required
def order_confirmation():
    user_id = current_user.id
    cosmos_db = cosmosdb.CosmosDB()
    # Fetch the items in the user's cart and any other necessary information
    cart_items = cosmos_db.get_items_in_cart(user_id)
    order_details = {
        "user_id": user_id,
        "items": cart_items,
        "total_price": sum(item["price"] for item in cart_items),
        "order_date": datetime.datetime.utcnow(),
        "status": "Pending"
    }
    # Create the order
    cosmos_db.create_order(user_id, order_details)
    # Remove items from the user's cart
    cosmos_db.clear_cart(user_id)
    return render_template('order_confirmation.html', order=order_details)


# Remove one or more products from the cart
@app.route('/remove_from_cart/<product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    user_id = current_user.id
    cosmos_db = cosmosdb.CosmosDB()
    cosmos_db.remove_product_from_cart(user_id, product_id)
    flash('Product removed from cart successfully', 'success')
    return redirect(url_for('cart_shop'))


# Add a product to the cart
@app.route('/add_products', methods=['GET', 'POST'])
@admin_required
def add_products():
    if request.method == 'POST':
        product_details = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'image_url': request.form['image_url']
        }
        cosmos_db = cosmosdb.CosmosDB()
        cosmos_db.add_product(product_details)
        flash('Product added successfully!', 'success')
        return redirect(url_for('list_products'))
    return render_template('add_products.html')


# Edit product information // ADMIN ONLY
@app.route('/edit_products/<product_id>', methods=['GET', 'POST'])
@admin_required
def edit_products(product_id):
    if not session.get('admin_logged_in'):
        abort(403)
    cosmos_db = cosmosdb.CosmosDB()
    if request.method == 'POST':
        form_data = request.form
        name = form_data['name']
        price = form_data['price']
        description = form_data['description']
        image_url = form_data['image_url']
        product_details = {
            'name': name,
            'price': price,
            'description': description,
            'image_url': image_url
        }
        cosmos_db.update_product(product_id, product_details)
        flash('Product updated successfully!', 'success')
        return redirect(url_for('list_products'))
    product = cosmos_db.get_product_by_id(product_id)
    return render_template('edit_product.html', product=product)


@app.route('/list_products')
@admin_required
def list_products():
    if not session.get('admin_logged_in'):
        abort(403)
    cosmos_db = cosmosdb.CosmosDB()
    products = cosmos_db.get_all_products()
    return render_template('list_products.html', products=products)


# Delete a product from the store // ADMIN ONLY
@app.route('/delete_products')
@admin_required
def delete_products():
    if not session.get('admin_logged_in'):
        abort(403)
    cosmos_db = cosmosdb.CosmosDB()
    products = cosmos_db.get_all_products()
    return render_template('delete_products.html', products=products)


# View purchases and orders // ADMIN ONLY
@app.route('/view_orders')
@admin_required
def view_orders():
    cosmos_db = cosmosdb.CosmosDB() 
    orders = cosmos_db.get_orders() 
    return render_template('view_orders.html', title='View Orders', orders=orders)


@app.route('/update_orders/<order_id>', methods=['GET', 'POST'])
@login_required
def update_orders(order_id):
    cosmos_db = cosmosdb.CosmosDB()
    order = cosmos_db.get_order(order_id)
    form = UpdateOrderStatusForm(obj=order)
    if form.validate_on_submit():
        cosmos_db.update_order_status(order_id, form.status.data)
        flash('Order status updated successfully', 'success')
        return redirect(url_for('view_orders'))
    return render_template('update_orders.html', title='Update Order', form=form)


@app.route('/list_orders_to_update')
def list_orders_to_update():
    if not session.get('admin_logged_in'):
        abort(403)
    cosmos_db = cosmosdb.CosmosDB()
    orders = cosmos_db.get_all_orders() 
    return render_template('list_orders_to_update.html', orders=orders)


@app.route('/sales/<period>')
@admin_required
def sales(period):
    if not session.get('admin_logged_in'):
        abort(403)
    if period not in ['today', 'week', 'month']:
        abort(404)
    cosmos_db = cosmosdb.CosmosDB()
    sales_data = cosmos_db.get_sales_data(period)
    return render_template('sales.html', period=period, sales_data=sales_data)


# Check how many users are online // ADMIN ONLY
@app.route('/check_users')
@admin_required
def check_users():
    cosmos_db = cosmosdb.CosmosDB()
    users = cosmos_db.get_users()
    return render_template('check_users.html', title='Check Users', users=users)


# Update cart information
@app.route('/update_cart/<product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    form = UpdateCartForm()
    if form.validate_on_submit():
        user_id = current_user.id
        cosmos_db = cosmosdb.CosmosDB()
        cosmos_db.update_cart(user_id, product_id, form.quantity.data)
        flash('Cart updated successfully', 'success')
        return redirect(url_for('cart_shop'))
    return render_template('cart_shop.html', title='Cart Shop', form=form)


# Checkout process
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cosmos_db = cosmosdb.CosmosDB()
    if request.method == 'POST':
        items = cosmos_db.get_items_in_cart(current_user.id)
        if not items:
            flash('Your cart is empty.', 'danger')
            return redirect(url_for('cart_shop'))
        # Create a new order with the user's cart items
        order_details = {
            'items': items,
            'status': 'Pending'
        }
        cosmos_db.create_order(current_user.id, order_details)
        # Clear the user's cart
        cosmos_db.clear_cart(current_user.id)
        flash('Order placed successfully! Your cart has been cleared.', 'success')
        return redirect(url_for('order_history'))
    billing_info = cosmos_db.get_billing_info_by_user_id(current_user.id)
    return render_template('checkout.html', billing_info=billing_info)


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'fer@admin.com' and password == 'admin_password':
            session['admin_logged_in'] = True
            flash('Logged in as admin.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin username or password.', 'danger')
    return render_template('admin_login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    print(session)
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login', next=request.url))
    cosmos_db = cosmosdb.CosmosDB()
    products = cosmos_db.get_all_products()
    return render_template('admin_dashboard.html', products=products)


@app.route('/store', methods=['GET', 'POST'])
def store():
    if request.method == 'POST':
        if 'admin_logged_in' in session and session['admin_logged_in']:
            form_data = request.form
            if 'action' in form_data:
                action = form_data['action']
                # Add a new product
                if action == 'add':
                    name = form_data['name']
                    price = form_data['price']
                    description = form_data['description']
                    image_url = form_data['image_url']
                    product_details = {
                        'name': name,
                        'price': price,
                        'description': description,
                        'image_url': image_url
                    }
                    cosmos_db = cosmosdb.CosmosDB()
                    cosmos_db.add_product(product_details)
                # Edit an existing product
                elif action == 'edit':
                    product_id = form_data['product_id']
                    name = form_data['name']
                    price = form_data['price']
                    description = form_data['description']
                    image_url = form_data['image_url']
                    product_details = {
                        'name': name,
                        'price': price,
                        'description': description,
                        'image_url': image_url
                    }
                    cosmos_db = cosmosdb.CosmosDB()
                    cosmos_db.update_product(product_id, product_details)
                # Delete a product
                elif action == 'delete':
                    product_id = form_data['product_id']
                    cosmos_db = cosmosdb.CosmosDB()
                    cosmos_db.delete_product(product_id)
    cosmos_db = cosmosdb.CosmosDB()
    products = cosmos_db.get_all_products()
    return render_template('store.html', products=products, admin_logged_in=session.get('admin_logged_in', False))




if __name__ == '__main__':
    app.run(debug=True)

    
