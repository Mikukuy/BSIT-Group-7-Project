"""Run with a desktop display or xvfb-run. Uses only a temporary database."""
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
TEMP = tempfile.TemporaryDirectory()
os.environ['MONEYMATE_DB_PATH'] = str(Path(TEMP.name) / 'gui.db')
os.environ['MONEYMATE_SETTINGS_PATH'] = str(Path(TEMP.name) / 'settings.json')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import initialize_database, engine
from app import MoneyMateApp
initialize_database()
root = tk.Tk()
errors = []
root.report_callback_exception = lambda *args: errors.append(args)
app = MoneyMateApp(root)
alerts = []
app.alert = lambda title, message: alerts.append((title,message))
root.update()
app.switch_auth('signup')
app.auth_vars['name'].set('Draft Name')
app.toggle_theme()
assert app.auth_vars['name'].get() == 'Draft Name' and app.auth_dirty()
ask = app.ask
app.ask = lambda *a,**k: False
app.switch_auth('login')
assert app.auth_mode == 'signup'
app.ask = lambda *a,**k: True
app.switch_auth('login')
assert app.auth_mode == 'login'
app.ask = ask
app.store.signup('Demo Member','demo@example.test','SamplePass!123','SamplePass!123')
app.store.signup('Other Member','other@example.test','SamplePass!123','SamplePass!123')
app.auth_vars['email'].set('demo@example.test')
app.auth_vars['password'].set('SamplePass!123')
app.submit_auth()
assert app.auth.user and not app.auth_vars
from datetime import date
month = date.today().strftime('%Y-%m')
app.store.save_budget('Food',month,'3000')
app.store.add_category('Fitness','expense')
for kind,category,amount,notes in [('income','Allowance','12000','Monthly allowance'),('expense','Food','1850','Meals and groceries'),('expense','Transportation','650','Campus commute'),('expense','Fitness','400','Workout class'),('income','Freelance/Side Job','2500','Design project')]:
    app.store.save_transaction(kind,category,amount,date.today().isoformat(),notes,allow_over_budget=True)
preview = Path(os.environ['MONEYMATE_PREVIEW_DIR']) if os.environ.get('MONEYMATE_PREVIEW_DIR') else None
if preview:
    preview.mkdir(parents=True,exist_ok=True)
def capture(name):
    root.update()
    if preview:
        from PIL import ImageGrab
        ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(preview / (name+'.png'))
for theme in ['light','dark']:
    if app.theme != theme:
        app.toggle_theme()
    for page in ['Dashboard','Transactions','Budgets','Categories','Archive']:
        app.navigate(page)
        root.update()
        capture(theme+'-'+page.lower())
    app.navigate('Transactions')
    app.transaction_dialog()
    dialog = app.modal
    capture(theme+'-transaction-form')
    dialog.vars['amount'].set('99.50')
    app.ask = lambda *a,**k: False
    dialog.cancel()
    assert app.modal is dialog and dialog.vars['amount'].get()=='99.50'
    app.ask = lambda *a,**k: True
    dialog.cancel()
    assert app.modal is None and len(app.store.transactions())==5
    app.ask = ask
    app.budget_dialog()
    assert 'Fitness' in app.modal.fields['category']['values']
    app.modal.cancel()
    assert app.modal is None
    app.category_dialog()
    app.modal.cancel()
app.transaction_dialog()
app.modal.vars['category'].set('Food')
app.modal.vars['amount'].set('5000')
app.ask = lambda *a,**k: False
def buttons(widget):
    for child in widget.winfo_children():
        if isinstance(child,tk.Button):
            yield child
        yield from buttons(child)
next(b for b in buttons(app.modal) if b.cget('text')=='Save transaction').invoke()
assert len(app.store.transactions())==5 and app.modal is not None
app.ask = lambda *a,**k: True
app.modal.cancel()
app.ask = ask
def cancel_confirmation():
    dialogs=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel)]
    assert dialogs
    next(b for b in buttons(dialogs[-1]) if b.cget('text')=='Cancel').invoke()
root.after(80,cancel_confirmation)
assert not app.ask('Cancel check','This operation must not proceed.','Continue')
def escape_confirmation():
    win=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel)][-1]
    win.focus_force()
    win.event_generate('<Escape>')
root.after(80,escape_confirmation)
assert not app.ask('Escape check','Escape must cancel.','Continue')
# Exercise actual UI saves, editing, and reversible archive operations.
def click(label):
    next(b for b in buttons(app.modal or root) if b.cget('text') == label).invoke()
app.ask = lambda *a,**k: True
app.category_dialog()
app.modal.vars['name'].set('Learning')
click('Save category')
assert app.modal is None and 'Learning' in app.store.categories('expense')
app.budget_dialog()
app.modal.vars['category'].set('Learning')
app.modal.vars['amount'].set('1000')
click('Save budget')
assert app.modal is None and app.store.budget_status('Learning',month)[0] == 100000
app.transaction_dialog()
app.modal.vars['category'].set('Learning')
app.modal.vars['amount'].set('100')
click('Save transaction')
assert app.modal is None and len(app.store.transactions()) == 6
record=next(t for t in app.store.transactions() if t['category']=='Learning')
app.transaction_dialog(record)
app.modal.vars['amount'].set('125')
click('Save changes')
assert next(t for t in app.store.transactions() if t['id']==record['id'])['cents']==12500
app.navigate('Transactions')
app.transaction_table.selection_set(str(record['id']))
app.ask = lambda *a,**k: False
app.archive_selected(app.transaction_table,True)
assert len(app.store.transactions())==6
app.ask = lambda *a,**k: True
app.archive_selected(app.transaction_table,True)
assert len(app.store.transactions())==5 and len(app.store.transactions(True))==1
app.navigate('Archive')
app.transaction_table.selection_set(str(record['id']))
app.archive_selected(app.transaction_table,False)
assert len(app.store.transactions())==6 and not app.store.transactions(True)
app.ask = lambda *a,**k: False
app.close()
assert root.winfo_exists() and app.auth.user
app.ask = ask

app.ask = lambda *a,**k: False
app.logout()
assert app.auth.user
app.ask = lambda *a,**k: True
app.logout()
assert app.auth.user is None and app.auth_mode=='login' and app.tx_rows=={}
assert all(v.get()=='' for v in app.auth_vars.values())
app.ask = ask
capture('dark-login')
app.auth_vars['email'].set('other@example.test')
app.auth_vars['password'].set('SamplePass!123')
app.submit_auth()
assert not app.store.transactions() and not app.store.budgets(month)
assert 'Fitness' not in app.store.categories('expense')
app.navigate('Transactions')
root.geometry('980x680')
root.update()
capture('minimum-empty-transactions')
app.ask = lambda *a,**k: True
app.logout()
app.switch_auth('signup')
root.update()
capture('minimum-signup')
assert not alerts, alerts
assert not errors, errors
root.destroy()
engine.dispose()
TEMP.cleanup()
print('GUI smoke checks passed: both themes, five pages, draft preservation, form cancellation, budget warning cancellation, Escape handling, logout cancellation, session clearing, account switch, and minimum window size.')
