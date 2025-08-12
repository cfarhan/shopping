from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import logging
import stripe
import json
import uuid
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Import database and models
from database import init_db
from models import User, CartItem, Order, Product

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Database configuration
def get_database_url():
    """Resolve database URL from env. Supports DATABASE_URL or discrete DB_* vars."""
    # Prefer a provided DATABASE_URL (Heroku style)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url

    # Compose from discrete env vars if available
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME')
    db_sslmode = os.environ.get('DB_SSLMODE')  # e.g., require

    if db_host and db_user and db_name:
        pwd = quote_plus(db_password or '')
        url = f"postgresql://{db_user}:{pwd}@{db_host}:{db_port}/{db_name}"
        if db_sslmode:
            url = f"{url}?sslmode={db_sslmode}"
        return url

    # Fallbacks
    if os.environ.get('FLASK_ENV') == 'development':
        return 'sqlite:///app.db'
    return 'sqlite:///app.db'

app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Initialize extensions
db = init_db(app)
jwt = JWTManager(app)
CORS(app)

# JWT error handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    app.logger.error(f"JWT Token expired: {jwt_payload}")
    return jsonify({'error': 'Token has expired'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    app.logger.error(f"Invalid JWT token: {error}")
    return jsonify({'error': 'Invalid token'}), 422

@jwt.unauthorized_loader
def missing_token_callback(error):
    app.logger.error(f"Missing JWT token: {error}")
    return jsonify({'error': 'Authorization token is required'}), 401

# Request logging middleware
@app.before_request
def log_request_info():
    if app.debug:
        app.logger.info(f"Request: {request.method} {request.url}")
        if request.is_json:
            app.logger.info(f"JSON Body: {request.get_json()}")

@app.after_request
def log_response_info(response):
    if app.debug:
        app.logger.info(f"Response Status: {response.status_code}")
    return response

# Utility functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Authentication Routes
@app.route('/v1/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create new user
        user = User(email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User created successfully',
            'access_token': access_token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        app.logger.error(f"Signup error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/signin', methods=['POST'])
def signin():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Signin error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Product Routes
@app.route('/v1/products', methods=['GET'])
def get_products():
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        query = Product.query
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        if category:
            query = query.filter_by(category=category)
        
        products = query.order_by(Product.name).all()
        
        return jsonify({
            'products': [product.to_dict() for product in products]
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get products error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/products/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify(product.to_dict()), 200
        
    except Exception as e:
        app.logger.error(f"Get product error: {str(e)}")
        return jsonify({'error': 'Product not found'}), 404

@app.route('/v1/products', methods=['POST'])
@jwt_required()
def create_product():
    """Create a new product (admin functionality)"""
    try:
        # Check if multipart form data (for image upload)
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Handle form data
            name = request.form.get('name')
            description = request.form.get('description')
            price = float(request.form.get('price', 0))
            category = request.form.get('category')
            stock_quantity = int(request.form.get('stock_quantity', 0))
            
            # Handle image upload
            image_url = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    # This part is removed as S3 is no longer used
                    pass
        else:
            # Handle JSON data
            data = request.get_json()
            name = data.get('name')
            description = data.get('description')
            price = float(data.get('price', 0))
            category = data.get('category')
            stock_quantity = int(data.get('stock_quantity', 0))
            image_url = data.get('image_url')
        
        if not name or price <= 0:
            return jsonify({'error': 'Name and valid price are required'}), 400
        
        product = Product(
            name=name,
            description=description,
            price=price,
            category=category,
            image_url=image_url,
            stock_quantity=stock_quantity
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product.to_dict()
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Invalid price or stock quantity'}), 400
    except Exception as e:
        app.logger.error(f"Create product error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Cart Routes
@app.route('/v1/cart', methods=['GET'])
@jwt_required()
def get_cart():
    try:
        current_user_id = get_jwt_identity()
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        cart_total = sum(item.total_price for item in cart_items)
        
        return jsonify({
            'cart_items': [item.to_dict() for item in cart_items],
            'cart_total': cart_total
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get cart error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('product_id'):
            return jsonify({'error': 'Product ID is required'}), 400
        
        product_id = data['product_id']
        quantity = int(data.get('quantity', 1))
        
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400
        
        # Check if product exists and is active
        product = Product.query.filter_by(id=product_id, is_active=True).first()
        if not product:
            return jsonify({'error': 'Product not found or not available'}), 404
        
        # Check stock availability
        if product.stock_quantity < quantity:
            return jsonify({'error': f'Only {product.stock_quantity} items in stock'}), 400
        
        # Check if item already exists in cart
        existing_item = CartItem.query.filter_by(
            user_id=current_user_id,
            product_id=product_id
        ).first()
        
        if existing_item:
            # Check if total quantity would exceed stock
            total_quantity = existing_item.quantity + quantity
            if total_quantity > product.stock_quantity:
                return jsonify({'error': f'Only {product.stock_quantity} items in stock'}), 400
            
            # Update quantity
            existing_item.quantity = total_quantity
        else:
            # Create new cart item
            cart_item = CartItem(
                user_id=current_user_id,
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        # Get updated cart
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        cart_total = sum(item.total_price for item in cart_items)
        
        return jsonify({
            'message': 'Item added to cart successfully',
            'cart_items': [item.to_dict() for item in cart_items],
            'cart_total': cart_total
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid quantity format'}), 400
    except Exception as e:
        app.logger.error(f"Add to cart error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/cart/update', methods=['PUT'])
@jwt_required()
def update_cart_item():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('product_id') or not data.get('quantity'):
            return jsonify({'error': 'Product ID and quantity are required'}), 400
        
        product_id = data['product_id']
        quantity = int(data['quantity'])
        
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400
        
        cart_item = CartItem.query.filter_by(
            user_id=current_user_id,
            product_id=product_id
        ).first()
        
        if not cart_item:
            return jsonify({'error': 'Cart item not found'}), 404
        
        # Check stock availability
        if cart_item.product.stock_quantity < quantity:
            return jsonify({'error': f'Only {cart_item.product.stock_quantity} items in stock'}), 400
        
        cart_item.quantity = quantity
        db.session.commit()
        
        return jsonify({
            'message': 'Cart item updated successfully',
            'cart_item': cart_item.to_dict()
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid quantity format'}), 400
    except Exception as e:
        app.logger.error(f"Update cart error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/cart/remove', methods=['DELETE'])
@jwt_required()
def remove_from_cart():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('product_id'):
            return jsonify({'error': 'Product ID is required'}), 400
        
        product_id = data['product_id']
        
        cart_item = CartItem.query.filter_by(
            user_id=current_user_id,
            product_id=product_id
        ).first()
        
        if not cart_item:
            return jsonify({'error': 'Cart item not found'}), 404
        
        db.session.delete(cart_item)
        db.session.commit()
        
        return jsonify({'message': 'Item removed from cart'}), 200
        
    except Exception as e:
        app.logger.error(f"Remove from cart error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Payment Routes
@app.route('/v1/stripe-config', methods=['GET'])
def get_stripe_config():
    return jsonify({
        'publicKey': STRIPE_PUBLISHABLE_KEY
    })

@app.route('/v1/create-payment-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    try:
        current_user_id = get_jwt_identity()
        
        # Get all cart items for the user
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Verify stock availability
        for item in cart_items:
            if item.product.stock_quantity < item.quantity:
                return jsonify({'error': f'Insufficient stock for {item.product.name}'}), 400
        
        # Calculate total in cents for Stripe
        total_amount = sum(item.total_price for item in cart_items)
        amount_cents = int(total_amount * 100)
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='usd',
            metadata={
                'user_id': current_user_id,
                'cart_items_count': len(cart_items)
            }
        )
        
        # Create pending order
        order_items = [item.to_dict() for item in cart_items]
        
        order = Order(
            user_id=current_user_id,
            total_amount=total_amount,
            status=Order.STATUS_PENDING,
            stripe_payment_intent_id=intent['id'],
            items=json.dumps(order_items)
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'client_secret': intent['client_secret'],
            'order_id': order.id
        })
        
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': 'Payment processing error'}), 500
    except Exception as e:
        app.logger.error(f"Create payment intent error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/confirm-payment', methods=['POST'])
@jwt_required()
def confirm_payment():
    try:
        data = request.get_json()
        payment_intent_id = data.get('payment_intent_id')
        
        if not payment_intent_id:
            return jsonify({'error': 'Payment intent ID required'}), 400
        
        # Find the order
        order = Order.query.filter_by(stripe_payment_intent_id=payment_intent_id).first()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Retrieve payment intent from Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent['status'] == 'succeeded':
            # Update order status
            order.mark_completed()
            
            # Reduce stock for ordered items
            cart_items = CartItem.query.filter_by(user_id=order.user_id).all()
            for item in cart_items:
                item.product.reduce_stock(item.quantity)
            
            # Clear cart for the user
            CartItem.query.filter_by(user_id=order.user_id).delete()
            
            db.session.commit()
            
            return jsonify({
                'message': 'Payment successful',
                'order': order.to_dict()
            })
        else:
            order.mark_failed()
            db.session.commit()
            return jsonify({'error': 'Payment failed'}), 400
            
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error in confirm_payment: {str(e)}")
        return jsonify({'error': 'Payment verification failed'}), 500
    except Exception as e:
        app.logger.error(f"Confirm payment error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Order Routes
@app.route('/v1/orders', methods=['GET'])
@jwt_required()
def get_orders():
    try:
        current_user_id = get_jwt_identity()
        orders = Order.query.filter_by(user_id=current_user_id).order_by(Order.created_at.desc()).all()
        
        return jsonify({
            'orders': [order.to_dict() for order in orders]
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get orders error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Legacy route for backward compatibility
@app.route('/v1/checkout', methods=['POST'])
@jwt_required()
def legacy_checkout():
    try:
        current_user_id = get_jwt_identity()
        
        # Get all cart items for the user
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Calculate total
        total_amount = sum(item.total_price for item in cart_items)
        
        # Create order record (legacy route - keeping for backward compatibility)
        order_items = [item.to_dict() for item in cart_items]
        
        order = Order(
            user_id=current_user_id,
            total_amount=total_amount,
            status=Order.STATUS_COMPLETED,  # For legacy checkout without payment
            items=json.dumps(order_items)
        )
        
        # Clear cart
        CartItem.query.filter_by(user_id=current_user_id).delete()
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'message': 'Checkout successful',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Legacy checkout error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# System Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'message': 'Flask backend is running',
            'database': 'connected'
        }), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'message': 'Health check failed',
            'error': str(e)
        }), 503

@app.route('/admin/seed-products', methods=['POST'])
def seed_products():
    """Seed initial products - for development/testing"""
    try:
        # Check if products already exist
        if Product.query.count() > 0:
            return jsonify({'message': 'Products already exist'}), 200
        
        # Sample products with S3 image URLs (you can update these later)
        sample_products = [
            {
                'name': 'Wireless Headphones',
                'description': 'High-quality wireless headphones with noise cancellation',
                'price': 199.99,
                'category': 'Electronics',
                'stock_quantity': 50
            },
            {
                'name': 'Smart Watch',
                'description': 'Feature-rich smartwatch with health monitoring',
                'price': 299.99,
                'category': 'Electronics',
                'stock_quantity': 30
            },
            {
                'name': 'Coffee Maker',
                'description': 'Professional-grade coffee maker for home use',
                'price': 149.99,
                'category': 'Home & Kitchen',
                'stock_quantity': 25
            },
            {
                'name': 'Running Shoes',
                'description': 'Comfortable running shoes for all terrains',
                'price': 129.99,
                'category': 'Sports & Outdoors',
                'stock_quantity': 75
            },
            {
                'name': 'Backpack',
                'description': 'Durable travel backpack with multiple compartments',
                'price': 89.99,
                'category': 'Travel',
                'stock_quantity': 40
            }
        ]
        
        for product_data in sample_products:
            product = Product(**product_data)
            db.session.add(product)
        
        db.session.commit()
        
        return jsonify({'message': 'Products seeded successfully'}), 201
        
    except Exception as e:
        app.logger.error(f"Seed products error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to seed products'}), 500

# CLI command for database operations
@app.cli.command()
def init_db_command():
    """Initialize the database."""
    db.create_all()
    print('Initialized the database.')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=os.environ.get('FLASK_ENV') == 'development', host='0.0.0.0', port=port)
