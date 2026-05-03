import uuid
import hashlib
from database import SessionLocal, User
import random

def generate_fake_upi():
    """Generate fake UPI ID - @mlbfd"""
    random_num = random.randint(100000, 999999)
    return f"user{random_num}@mlbfd"

def hash_pin(pin):
    """Hash PIN for security"""
    return hashlib.sha256(pin.encode()).hexdigest()

def register_user(pin):
    """Register new user with fake UPI"""
    db = SessionLocal()
    
    user_id = str(uuid.uuid4())
    fake_upi = generate_fake_upi()
    pin_hash = hash_pin(pin)
    
    new_user = User(
        id=user_id,
        fake_upi_id=fake_upi,
        pin_hash=pin_hash,
        balance=100000  # 1 Lakh
    )
    
    db.add(new_user)
    db.commit()
    db.close()
    
    return {
        "user_id": user_id,
        "fake_upi_id": fake_upi,
        "balance": 100000
    }

def verify_pin(user_id, pin):
    """Verify user PIN"""
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    
    if not user:
        return False
    return user.pin_hash == hash_pin(pin)

def get_user_balance(user_id):
    """Get user balance"""
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    
    return user.balance if user else None

def update_balance(user_id, amount):
    """Update user balance"""
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.balance += amount
        db.commit()
    db.close()
