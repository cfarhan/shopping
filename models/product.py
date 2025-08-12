from datetime import datetime
import uuid
from database import db

class Product(db.Model):
    """Product model for storing shop products"""
    
    __tablename__ = 'products'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        db.Index('idx_product_category', 'category'),
        db.Index('idx_product_active', 'is_active'),
        db.Index('idx_product_name', 'name'),
    )

    def to_dict(self):
        """Convert product to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'category': self.category,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'stock_quantity': self.stock_quantity,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @property
    def is_in_stock(self):
        """Check if product is in stock"""
        return self.stock_quantity > 0

    def reduce_stock(self, quantity):
        """Reduce stock quantity"""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            return True
        return False

    def __repr__(self):
        return f'<Product {self.name}: ${self.price}>' 