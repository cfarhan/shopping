from datetime import datetime
import uuid
from database import db

class Order(db.Model):
    """Order model for completed purchases"""
    
    __tablename__ = 'orders'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Store order items as JSON for simplicity (can be normalized later)
    items = db.Column(db.Text, nullable=False)

    # Indexes
    __table_args__ = (
        db.Index('idx_order_user', 'user_id'),
        db.Index('idx_order_status', 'status'),
        db.Index('idx_order_payment_intent', 'stripe_payment_intent_id'),
        db.Index('idx_order_created', 'created_at'),
    )

    # Order status constants
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'

    VALID_STATUSES = [STATUS_PENDING, STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED, STATUS_REFUNDED]

    def to_dict(self):
        """Convert order to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total_amount': float(self.total_amount),
            'status': self.status,
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'items': self.items
        }

    @property
    def is_completed(self):
        """Check if order is completed"""
        return self.status == self.STATUS_COMPLETED

    @property
    def is_pending(self):
        """Check if order is pending"""
        return self.status == self.STATUS_PENDING

    def mark_completed(self):
        """Mark order as completed"""
        self.status = self.STATUS_COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_failed(self):
        """Mark order as failed"""
        self.status = self.STATUS_FAILED
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f'<Order {self.id}: ${self.total_amount} ({self.status})>' 