from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import logging
import uuid

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# Initialize extensions
db = SQLAlchemy(app)
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
    app.logger.info(f"Request: {request.method} {request.url}")
    app.logger.info(f"Headers: {dict(request.headers)}")
    if request.is_json:
        app.logger.info(f"JSON Body: {request.get_json()}")

@app.after_request
def log_response_info(response):
    app.logger.info(f"Response Status: {response.status_code}")
    return response

# Models
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with cart items
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class CartItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'price': self.price,
            'quantity': self.quantity,
            'total': self.price * self.quantity,
            'added_at': self.added_at.isoformat()
        }

class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Store order items as JSON for simplicity
    items = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'total_amount': self.total_amount,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'items': self.items
        }

# Routes
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
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/addToCart', methods=['POST'])
@jwt_required()
def add_to_cart():
    try:
        current_user_id = get_jwt_identity()
        app.logger.info(f"AddToCart request from user_id: {current_user_id}")
        
        # Log the raw request data
        raw_data = request.get_data(as_text=True)
        app.logger.info(f"Raw request data: {raw_data}")
        
        data = request.get_json()
        app.logger.info(f"Parsed JSON data: {data}")
        
        if not data or not data.get('product_name') or not data.get('price'):
            app.logger.error(f"Missing required fields. Data received: {data}")
            return jsonify({'error': 'Product name and price are required'}), 400
        
        product_name = data['product_name']
        price = float(data['price'])
        quantity = int(data.get('quantity', 1))
        
        app.logger.info(f"Processing: product_name={product_name}, price={price}, quantity={quantity}")
        
        if price <= 0 or quantity <= 0:
            app.logger.error(f"Invalid price or quantity: price={price}, quantity={quantity}")
            return jsonify({'error': 'Price and quantity must be positive'}), 400
        
        # Check if item already exists in cart
        existing_item = CartItem.query.filter_by(
            user_id=current_user_id,
            product_name=product_name
        ).first()
        
        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
            existing_item.price = price  # Update price in case it changed
        else:
            # Create new cart item
            cart_item = CartItem(
                user_id=current_user_id,
                product_name=product_name,
                price=price,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        # Get updated cart
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        cart_total = sum(item.price * item.quantity for item in cart_items)
        
        app.logger.info(f"Cart updated successfully. Total items: {len(cart_items)}, Total: ${cart_total}")
        
        return jsonify({
            'message': 'Item added to cart successfully',
            'cart_items': [item.to_dict() for item in cart_items],
            'cart_total': cart_total
        }), 200
        
    except ValueError as ve:
        app.logger.error(f"ValueError in addToCart: {str(ve)}")
        return jsonify({'error': 'Invalid price or quantity format'}), 400
    except Exception as e:
        app.logger.error(f"Exception in addToCart: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/v1/checkout', methods=['POST'])
@jwt_required()
def checkout():
    try:
        current_user_id = get_jwt_identity()
        
        # Get all cart items for the user
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Calculate total
        total_amount = sum(item.price * item.quantity for item in cart_items)
        
        # Create order record
        import json
        order_items = [item.to_dict() for item in cart_items]
        
        order = Order(
            user_id=current_user_id,
            total_amount=total_amount,
            items=json.dumps(order_items)
        )
        
        # Clear cart
        CartItem.query.filter_by(user_id=current_user_id).delete()
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'message': 'Checkout successful',
            'order': {
                'id': order.id,
                'total_amount': order.total_amount,
                'status': order.status,
                'items': order_items,
                'created_at': order.created_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Helper routes
@app.route('/v1/cart', methods=['GET'])
@jwt_required()
def get_cart():
    try:
        current_user_id = get_jwt_identity()
        cart_items = CartItem.query.filter_by(user_id=current_user_id).all()
        cart_total = sum(item.price * item.quantity for item in cart_items)
        
        return jsonify({
            'cart_items': [item.to_dict() for item in cart_items],
            'cart_total': cart_total
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

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
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask backend is running'}), 200

@app.route('/admin/reset-db', methods=['POST'])
def reset_database():
    """Drop all tables and recreate them - USE WITH CAUTION!"""
    try:
        app.logger.info("Dropping all database tables...")
        db.drop_all()
        app.logger.info("Creating all database tables...")
        db.create_all()
        app.logger.info("Database reset completed successfully!")
        return jsonify({'message': 'Database reset successfully'}), 200
    except Exception as e:
        app.logger.error(f"Database reset failed: {str(e)}")
        return jsonify({'error': f'Database reset failed: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
