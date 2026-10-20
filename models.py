from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import date
import hashlib

engine = create_engine("sqlite:///moneymate.db")
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    transactions = relationship("Transaction", back_populates="user")
    categories = relationship("Category", back_populates="user")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)  # "income" or "expense"
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="categories")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    type = Column(String)  # "income" or "expense"
    category = Column(String)  # Stores the category name
    amount = Column(Float)
    date = Column(Date, default=date.today)
    notes = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="transactions")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)