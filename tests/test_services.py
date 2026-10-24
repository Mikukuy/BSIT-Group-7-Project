"""Regression checks. All databases live in a temporary directory."""
import hashlib
from contextlib import closing
from datetime import date
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

TEMP = tempfile.TemporaryDirectory()
os.environ['MONEYMATE_DB_PATH'] = str(Path(TEMP.name) / 'test.db')
from models import initialize_database, Session, User, Budget, Category, Transaction, engine
from services import AuthSession, Store, ValidationError, money_cents
initialize_database()

class FinanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth = AuthSession()
        cls.store = Store(cls.auth)
        cls.store.signup('Test Member', 'member@example.test', 'StrongPass!123', 'StrongPass!123')
        cls.store.signup('Other Member', 'other@example.test', 'StrongPass!123', 'StrongPass!123')

    @classmethod
    def tearDownClass(cls):
        engine.dispose()
        TEMP.cleanup()

    def setUp(self):
        self.store.login('member@example.test', 'StrongPass!123')
        with Session.begin() as db:
            for model in (Transaction, Budget, Category):
                db.query(model).delete()

    def test_amount_validation(self):
        self.assertEqual(money_cents('1,250.50'), 125050)
        self.assertEqual(money_cents('0.01'), 1)
        for invalid in ('nan', 'NaN', 'inf', '-1', '0', '', 'abc', '1.239', '1000000.01', '1,2', '1e3'):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                money_cents(invalid)

    def test_categories_are_shared_and_persistent(self):
        self.store.add_category('Fitness', 'expense')
        self.assertIn('Fitness', self.store.categories('expense'))
        self.store.save_budget('Fitness', '2026-10', '500')
        self.store.save_transaction('expense','Fitness','100','2026-10-23')
        self.auth.logout()
        self.store.login('member@example.test', 'StrongPass!123')
        self.assertIn('Fitness', self.store.categories('expense'))
        self.assertEqual(self.store.budget_status('Fitness', '2026-10'), (50000,10000))

    def test_account_isolation_and_logout(self):
        tx = self.store.save_transaction('income','Allowance','1000','2026-10-23')['id']
        self.store.save_budget('Food','2026-10','200')
        self.store.add_category('Fitness', 'expense')
        self.auth.logout()
        with self.assertRaises(ValidationError):
            self.store.transactions()
        self.store.login('other@example.test','StrongPass!123')
        self.assertEqual(self.store.transactions(), [])
        self.assertEqual(self.store.budgets('2026-10'), [])
        self.assertNotIn('Fitness',self.store.categories('expense'))
        with self.assertRaises(ValidationError):
            self.store.archive_transactions([tx])
        with self.assertRaises(ValidationError):
            self.store.save_transaction('income','Allowance','2','2026-10-23',transaction_id=tx)

    def test_budget_warning_does_not_save_until_confirmed(self):
        self.store.save_budget('Food','2026-10','200')
        response = self.store.save_transaction('expense','Food','250','2026-10-23')
        self.assertTrue(response['over_budget'])
        self.assertEqual(self.store.transactions(), [])
        self.store.save_transaction('expense','Food','250','2026-10-23',allow_over_budget=True)
        self.assertEqual(len(self.store.transactions()),1)

    def test_archive_restore_and_edit_recalculate(self):
        self.store.save_transaction('income','Allowance','1000','2026-10-23')
        tx = self.store.save_transaction('expense','Food','150','2026-10-23')['id']
        def balance():
            return sum(t['cents'] * (1 if t['type']=='income' else -1) for t in self.store.transactions())
        self.assertEqual(balance(),85000)
        self.store.save_transaction('expense','Food','200','2026-10-23',transaction_id=tx)
        self.assertEqual(balance(),80000)
        self.store.archive_transactions([tx])
        self.assertEqual(balance(),100000)
        self.assertEqual(len(self.store.transactions(True)),1)
        self.store.archive_transactions([tx],False)
        self.assertEqual(balance(),80000)

    def test_removed_category_preserves_history(self):
        self.store.add_category('Fitness','expense')
        tx=self.store.save_transaction('expense','Fitness','100','2026-10-23')['id']
        cat=self.store.custom_categories()[0]
        self.store.remove_category(cat.id)
        self.assertNotIn('Fitness',self.store.categories('expense'))
        self.assertEqual(self.store.transactions()[0]['category'],'Fitness')
        self.store.save_transaction('expense','Fitness','110','2026-10-23',transaction_id=tx)
        self.store.add_category('Fitness','expense')
        self.assertIn('Fitness',self.store.categories('expense'))

    def test_password_upgrade_keeps_old_account(self):
        with Session.begin() as db:
            db.add(User(full_name='Legacy Account',email='legacy@example.test',password_hash=hashlib.sha256(b'OldPass!123').hexdigest()))
        self.store.login('legacy@example.test','OldPass!123')
        with Session() as db:
            user=db.query(User).filter_by(email='legacy@example.test').one()
            self.assertTrue(user.password_hash.startswith('pbkdf2_sha256$'))
        self.auth.logout()
        self.store.login('legacy@example.test','OldPass!123')

    def test_persists_across_python_process(self):
        self.store.save_budget('Food','2026-10','200')
        self.store.add_category('Fitness','expense')
        self.store.save_transaction('expense','Fitness','20','2026-10-23')
        script="from services import AuthSession,Store; s=Store(AuthSession()); s.login('member@example.test','StrongPass!123'); assert s.budgets('2026-10')[0].limit_cents==20000; assert 'Fitness' in s.categories('expense'); assert s.transactions()[0]['cents']==2000"
        subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],check=True,env=os.environ.copy())

    def test_original_schema_upgrade_is_idempotent_and_backed_up(self):
        old=Path(TEMP.name)/'legacy.db'
        with closing(sqlite3.connect(old)) as db:
            db.executescript("CREATE TABLE users(id INTEGER PRIMARY KEY,full_name VARCHAR NOT NULL,email VARCHAR UNIQUE NOT NULL,password_hash VARCHAR NOT NULL); CREATE TABLE categories(id INTEGER PRIMARY KEY,name VARCHAR NOT NULL,type VARCHAR,user_id INTEGER); CREATE TABLE transactions(id INTEGER PRIMARY KEY,type VARCHAR,category VARCHAR,amount FLOAT,date DATE,notes VARCHAR,user_id INTEGER); CREATE TABLE budgets(id INTEGER PRIMARY KEY,category VARCHAR NOT NULL,limit_amount FLOAT NOT NULL,user_id INTEGER); INSERT INTO users VALUES(1,'Old User','old@example.test','hash'); INSERT INTO transactions VALUES(1,'expense','Food',1.25,'2026-10-23',NULL,1); INSERT INTO budgets VALUES(1,'Food',125.50,1);")
        env=dict(os.environ,MONEYMATE_DB_PATH=str(old))
        code="from datetime import date; from models import initialize_database,Session,Transaction,Budget; initialize_database(); initialize_database(); s=Session(); t=s.get(Transaction,1); b=s.get(Budget,1); assert t.amount==1.25 and t.is_archived==False; assert b.limit_cents==12550 and b.month==date.today().strftime('%Y-%m'); s.close()"
        subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=env,check=True)
        with closing(sqlite3.connect(old)) as db:
            columns = [row[1] for row in db.execute('PRAGMA table_info(budgets)')]
            self.assertIn('month', columns)
            self.assertIn('limit_cents', columns)
            self.assertEqual(db.execute('SELECT limit_cents FROM budgets WHERE id=1').fetchone()[0], 12550)
        backups=list((old.parent/'.backups').glob('*.db'))
        self.assertEqual(len(backups),1)
        with closing(sqlite3.connect(backups[0])) as db:
            self.assertEqual(db.execute('SELECT amount FROM transactions').fetchone()[0],1.25)
            self.assertNotIn('is_archived',[r[1] for r in db.execute('pragma table_info(transactions)')])
            self.assertEqual(db.execute('SELECT limit_amount FROM budgets').fetchone()[0],125.5)

if __name__ == '__main__':
    unittest.main()
