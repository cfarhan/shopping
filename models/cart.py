from datetime import datetime
import uuid
from database import db

class CartItem(db.Model):
    """Cart item model for user shopping carts"""
    
    __tablename__ = 'cart_items'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', backref='cart_items', lazy=True)

    # Indexes
    __table_args__ = (
        db.Index('idx_cart_user_product', 'user_id', 'product_id'),
        db.UniqueConstraint('user_id', 'product_id', name='uq_user_product'),
    )

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return float(self.product.price) * self.quantity

    def to_dict(self):
        """Convert cart item to dictionary for API responses"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name,
            'product_description': self.product.description,
            'price': float(self.product.price),
            'quantity': self.quantity,
            'total': self.total_price,
            'added_at': self.added_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'product': self.product.to_dict()
        }

    def __repr__(self):
        return f'<CartItem {self.product.name} x{self.quantity}>' 