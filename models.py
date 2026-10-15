from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date

engine = create_engine("sqlite:///moneymate.db")
Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    type = Column(String)  # "income" or "expense"
    category = Column(String)
    amount = Column(Float)
    date = Column(Date, default=date.today)
    notes = Column(String, nullable=True)

import hashlib

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)