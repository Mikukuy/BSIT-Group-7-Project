"""Database models and non-destructive upgrades for the original MoneyMate database."""
from datetime import date, datetime
from pathlib import Path
from contextlib import closing
import hashlib
import hmac
import os
import sqlite3

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Float, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('MONEYMATE_DB_PATH', str(APP_DIR / 'moneymate.db'))).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine('sqlite:///' + DB_PATH.as_posix())
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    transactions = relationship('Transaction', back_populates='user')
    categories = relationship('Category', back_populates='user')

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    is_archived = Column(Boolean, nullable=False, default=False, server_default='0')
    user = relationship('User', back_populates='categories')

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    type = Column(String)
    category = Column(String)
    amount = Column(Float)  # Retained for compatibility with the original project.
    amount_cents = Column(Integer)
    date = Column(Date, default=date.today)
    notes = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    is_archived = Column(Boolean, nullable=False, default=False, server_default='0')
    user = relationship('User', back_populates='transactions')

class Budget(Base):
    __tablename__ = 'budgets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category = Column(String, nullable=False)
    month = Column(String, nullable=False)  # YYYY-MM
    limit_cents = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'category', 'month'),)

ITERATIONS = 600_000

def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'

def verify_password(password, stored):
    if stored.startswith('pbkdf2_sha256$'):
        try:
            _, rounds, salt, expected = stored.split('$')
            count = int(rounds)
            if not 100_000 <= count <= 2_000_000:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), count).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    # Original accounts keep working and are upgraded after a successful login.
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)

def initialize_database():
    """Back up before adding columns; never delete the user's database."""
    additions = {
        'transactions': {'amount_cents': 'INTEGER', 'is_archived': 'BOOLEAN NOT NULL DEFAULT 0'},
        'categories': {'is_archived': 'BOOLEAN NOT NULL DEFAULT 0'},
    }
    schema = inspect(engine)
    tables = schema.get_table_names()
    changes = []
    for table, columns in additions.items():
        if table in tables:
            existing = {c['name'] for c in schema.get_columns(table)}
            changes.extend((table, name, definition) for name, definition in columns.items() if name not in existing)
    legacy_budgets = False
    if 'budgets' in tables:
        budget_columns = {c['name'] for c in schema.get_columns('budgets')}
        legacy_budgets = not {'month', 'limit_cents'}.issubset(budget_columns)
    if (changes or legacy_budgets) and DB_PATH.exists():
        backup_dir = DB_PATH.parent / '.backups'
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f'moneymate-before-upgrade-{datetime.now():%Y%m%d-%H%M%S-%f}.db'
        with closing(sqlite3.connect(DB_PATH)) as source, closing(sqlite3.connect(backup)) as target:
            source.backup(target)
    with engine.begin() as conn:
        for table, name, definition in changes:
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'))
        if legacy_budgets:
            conn.execute(text('ALTER TABLE "budgets" RENAME TO "budgets_legacy"'))
            conn.execute(text(
                'CREATE TABLE "budgets" ('
                'id INTEGER NOT NULL PRIMARY KEY, '
                'user_id INTEGER NOT NULL, '
                'category VARCHAR NOT NULL, '
                'month VARCHAR NOT NULL, '
                'limit_cents INTEGER NOT NULL, '
                'CONSTRAINT uq_budgets_user_category_month UNIQUE (user_id, category, month), '
                'FOREIGN KEY(user_id) REFERENCES users (id))'
            ))
            conn.execute(
                text(
                    'INSERT INTO "budgets" (id, user_id, category, month, limit_cents) '
                    'SELECT id, user_id, category, :month, CAST(ROUND(limit_amount * 100) AS INTEGER) '
                    'FROM "budgets_legacy"'
                ),
                {'month': date.today().strftime('%Y-%m')},
            )
            conn.execute(text('DROP TABLE "budgets_legacy"'))
    Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine, expire_on_commit=False)
