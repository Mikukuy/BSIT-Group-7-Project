"""Account-scoped operations, validation, and calculations, independent of Tkinter."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from sqlalchemy import select
from models import Session, User, Transaction, Category, Budget, hash_password, verify_password

BUILT_INS = {
    'income': ['Allowance', 'Salary/Wages', 'Freelance/Side Job', 'Scholarship/Grant', 'Gift', 'Other'],
    'expense': ['Food', 'Transportation', 'Bills', 'School Supplies', 'Shopping', 'Other'],
}

class ValidationError(ValueError):
    pass

@dataclass(frozen=True)
class Identity:
    id: int
    name: str
    email: str

class AuthSession:
    """An explicit local login session. No account data is retained after logout."""
    def __init__(self):
        self.user = None
    def login(self, identity):
        self.user = identity
    def logout(self):
        self.user = None
    def require_user(self):
        if self.user is None:
            raise ValidationError('Your session has ended. Please log in again.')
        return self.user.id

def money_cents(raw):
    try:
        # Commas must be valid thousands separators, not arbitrary decimal edits.
        value = str(raw).strip()
        if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?', value):
            raise ValidationError('Enter a positive amount with at most two decimal places, for example 1,250.50.')
        amount = Decimal(value.replace(',', ''))
        if not amount.is_finite() or amount <= 0 or amount > Decimal('1000000'):
            raise ValidationError('Amount must be above zero and no more than PHP 1,000,000.')
        return int(amount * 100)
    except InvalidOperation:
        raise ValidationError('Enter a valid amount.') from None

def parse_date(raw):
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        raise ValidationError('Use a valid date in YYYY-MM-DD format.') from None

def valid_month(month):
    if not re.fullmatch(r'\d{4}-\d{2}', month or ''):
        raise ValidationError('Use YYYY-MM for the budget month.')
    parse_date(month + '-01')
    return month

def tx_cents(tx):
    if tx.amount_cents is not None:
        return tx.amount_cents
    # Existing records are read without changing their original amount.
    return int((Decimal(str(tx.amount)) * 100).quantize(Decimal('1')))

class Store:
    def __init__(self, auth):
        self.auth = auth

    def signup(self, name, email, password, confirm):
        name, email = ' '.join(name.split()), email.strip().lower()
        if not 3 <= len(name) <= 40:
            raise ValidationError('Name must contain 3 to 40 characters.')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValidationError('Enter a valid email address.')
        if not 8 <= len(password) <= 128 or not any(not c.isalnum() and not c.isspace() for c in password):
            raise ValidationError('Use 8 to 128 characters and at least one special character.')
        if password != confirm:
            raise ValidationError('The passwords do not match.')
        with Session.begin() as db:
            if db.scalar(select(User).where(User.email == email)):
                raise ValidationError('An account with this email already exists.')
            db.add(User(full_name=name, email=email, password_hash=hash_password(password)))

    def login(self, email, password):
        with Session.begin() as db:
            user = db.scalar(select(User).where(User.email == email.strip().lower()))
            if user is None or not verify_password(password, user.password_hash):
                raise ValidationError('Email or password is incorrect.')
            if not user.password_hash.startswith('pbkdf2_sha256$'):
                user.password_hash = hash_password(password)
            identity = Identity(user.id, user.full_name, user.email)
        self.auth.login(identity)
        return identity

    def categories(self, kind):
        uid = self.auth.require_user()
        with Session() as db:
            custom = db.scalars(select(Category).where(Category.user_id == uid, Category.type == kind, Category.is_archived == False).order_by(Category.name)).all()
            return BUILT_INS[kind] + [c.name for c in custom if c.name.casefold() not in {n.casefold() for n in BUILT_INS[kind]}]

    def custom_categories(self):
        uid = self.auth.require_user()
        with Session() as db:
            return db.scalars(select(Category).where(Category.user_id == uid, Category.is_archived == False).order_by(Category.type, Category.name)).all()

    def add_category(self, name, kind):
        uid = self.auth.require_user()
        name = ' '.join(name.split())
        if not 2 <= len(name) <= 32 or not any(c.isalpha() for c in name):
            raise ValidationError('Use a category name with 2 to 32 characters and at least one letter.')
        if kind not in BUILT_INS:
            raise ValidationError('Select Income or Expense.')
        if name.casefold() in {c.casefold() for c in self.categories(kind)}:
            raise ValidationError('This category already exists for this type.')
        with Session.begin() as db:
            previous = next((c for c in db.scalars(select(Category).where(Category.user_id == uid, Category.type == kind)) if c.name.casefold() == name.casefold()), None)
            if previous:
                previous.is_archived = False
            else:
                db.add(Category(name=name, type=kind, user_id=uid))

    def remove_category(self, category_id):
        uid = self.auth.require_user()
        with Session.begin() as db:
            row = db.scalar(select(Category).where(Category.id == category_id, Category.user_id == uid))
            if row is None:
                raise ValidationError('Category was not found in your account.')
            row.is_archived = True

    def transactions(self, archived=False):
        uid = self.auth.require_user()
        with Session() as db:
            rows = db.scalars(select(Transaction).where(Transaction.user_id == uid, Transaction.is_archived == archived).order_by(Transaction.date.desc(), Transaction.id.desc())).all()
            return [dict(id=t.id, type=t.type, category=t.category, cents=tx_cents(t), date=t.date, notes=t.notes or '') for t in rows]

    def save_transaction(self, kind, category, amount, day, notes='', transaction_id=None, allow_over_budget=False):
        uid = self.auth.require_user()
        if kind not in BUILT_INS:
            raise ValidationError('Select Income or Expense.')
        cents, day = money_cents(amount), parse_date(day)
        notes = notes.strip()
        if len(notes) > 300:
            raise ValidationError('Keep notes within 300 characters.')
        with Session.begin() as db:
            row = None
            if transaction_id is not None:
                row = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == uid, Transaction.is_archived == False))
                if row is None:
                    raise ValidationError('Transaction was not found in your account.')
            # A removed category may remain on its existing transaction when editing.
            if category not in self.categories(kind) and not (row and row.category == category and row.type == kind):
                raise ValidationError('Choose an available category.')
            if kind == 'expense' and not allow_over_budget:
                limit, spent = self.budget_status(category, day.strftime('%Y-%m'), transaction_id)
                if limit is not None and spent + cents > limit:
                    return {'over_budget': True, 'limit': limit, 'projected': spent + cents}
            if row is None:
                row = Transaction(user_id=uid)
                db.add(row)
            row.type, row.category = kind, category
            row.amount_cents, row.amount = cents, cents / 100
            row.date, row.notes = day, notes
            db.flush()
            return {'id': row.id}

    def archive_transactions(self, ids, archived=True):
        uid = self.auth.require_user()
        with Session.begin() as db:
            rows = db.scalars(select(Transaction).where(Transaction.user_id == uid, Transaction.id.in_(ids))).all()
            if len(rows) != len(set(ids)):
                raise ValidationError('One or more selected records are unavailable in your account.')
            for row in rows:
                row.is_archived = archived

    def budgets(self, month):
        uid = self.auth.require_user()
        valid_month(month)
        with Session() as db:
            return db.scalars(select(Budget).where(Budget.user_id == uid, Budget.month == month).order_by(Budget.category)).all()

    def budget_status(self, category, month, excluding=None):
        rows = self.transactions()
        spent = sum(t['cents'] for t in rows if t['type'] == 'expense' and t['category'] == category and t['date'].strftime('%Y-%m') == month and t['id'] != excluding)
        budget = next((b for b in self.budgets(month) if b.category == category), None)
        return (budget.limit_cents if budget else None), spent

    def save_budget(self, category, month, amount):
        uid = self.auth.require_user()
        cents, month = money_cents(amount), valid_month(month)
        if category not in self.categories('expense') and category not in [b.category for b in self.budgets(month)]:
            raise ValidationError('Choose an available expense category.')
        with Session.begin() as db:
            row = db.scalar(select(Budget).where(Budget.user_id == uid, Budget.category == category, Budget.month == month))
            if row:
                row.limit_cents = cents
            else:
                db.add(Budget(user_id=uid, category=category, month=month, limit_cents=cents))

    def remove_budget(self, budget_id):
        uid = self.auth.require_user()
        with Session.begin() as db:
            row = db.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == uid))
            if row is None:
                raise ValidationError('Budget was not found in your account.')
            db.delete(row)
