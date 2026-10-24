"""MoneyMate desktop UI. Start with `python app.py`. Importing does not open a window."""
from collections import defaultdict
from datetime import date
from pathlib import Path
import json
import logging
import os
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageTk
from sqlalchemy.exc import SQLAlchemyError
from models import APP_DIR, initialize_database
from services import AuthSession, Store, ValidationError

THEMES = {
    'light': dict(bg='#F3F6FC', surface='#FFFFFF', inset='#F7F9FD', text='#142342', muted='#65738B', line='#DFE6F1', blue='#245BDB', hover='#1949B8', soft='#EAF0FF', nav='#122957', nav_text='#BBCBED', green='#087C62', red='#C43D50', amber='#946100', track='#E6ECF7'),
    'dark': dict(bg='#0C1424', surface='#152137', inset='#101B2E', text='#EDF3FF', muted='#A4B4CE', line='#2B3C56', blue='#507FF5', hover='#396AE5', soft='#23385D', nav='#101D34', nav_text='#B2C3E0', green='#54D6B0', red='#FF8796', amber='#F5CB72', track='#2A3D59'),
}

def cash(cents):
    return f'PHP {cents / 100:,.2f}'

def month_label(raw):
    return date.fromisoformat(raw + '-01').strftime('%B %Y')

class MoneyMateApp:
    def __init__(self, root, settings_path=None):
        self.root = root
        self.settings_path = Path(settings_path or os.environ.get('MONEYMATE_SETTINGS_PATH', APP_DIR / 'app_data' / 'settings.json'))
        self.settings = {}
        try:
            self.settings = json.loads(self.settings_path.read_text())
        except (OSError, ValueError, AttributeError):
            self.settings = {}
        self.logo_images = {}
        self.theme = 'light'
        value = self.settings.get('theme')
        if value in THEMES:
            self.theme = value
        families = tkfont.families(root)
        self.font = 'Segoe UI' if 'Segoe UI' in families else 'DejaVu Sans'
        self.auth = AuthSession()
        self.store = Store(self.auth)
        self.page = 'Dashboard'
        self.modal = None
        self.auth_vars = {}
        self.auth_initial = {}
        self.auth_mode = 'login'
        self.budget_month = date.today().strftime('%Y-%m')
        self.overview_period = 'This month'
        self.notice = ''
        root.title('MoneyMate | Personal finance')
        root.geometry('1220x800')
        root.minsize(980, 680)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Control-n>', lambda e: self.transaction_dialog() if self.auth.user and not self.modal else None)
        root.bind('<Escape>', self.escape)
        self.configure_style()
        self.show_auth()

    @property
    def c(self):
        return THEMES[self.theme]

    def configure_style(self):
        c = self.c
        self.root.configure(bg=c['bg'])
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=(self.font, 10), background=c['surface'], foreground=c['text'])
        style.configure('TEntry', fieldbackground=c['inset'], foreground=c['text'], insertcolor=c['text'], bordercolor=c['line'], lightcolor=c['line'], darkcolor=c['line'], padding=9)
        style.map('TEntry', bordercolor=[('focus', c['blue'])])
        style.configure('TCombobox', fieldbackground=c['inset'], background=c['inset'], foreground=c['text'], arrowcolor=c['muted'], bordercolor=c['line'], padding=8)
        style.map('TCombobox', fieldbackground=[('readonly', c['inset'])], foreground=[('readonly', c['text'])], selectbackground=[('readonly', c['inset'])], selectforeground=[('readonly', c['text'])])
        self.root.option_add('*TCombobox*Listbox.background', c['surface'])
        self.root.option_add('*TCombobox*Listbox.foreground', c['text'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', c['blue'])
        style.configure('Treeview', background=c['surface'], fieldbackground=c['surface'], foreground=c['text'], rowheight=43, borderwidth=0, font=(self.font, 10))
        style.configure('Treeview.Heading', background=c['inset'], foreground=c['muted'], relief='flat', padding=(10, 12), font=(self.font, 9, 'bold'))
        style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
        style.map('Treeview', background=[('selected', c['soft'])], foreground=[('selected', c['text'])])
        style.map('Treeview.Heading', background=[('active', c['soft'])])
        style.configure('Vertical.TScrollbar', background=c['track'], troughcolor=c['bg'], borderwidth=0, arrowcolor=c['muted'])
        style.configure('Horizontal.TScrollbar', background=c['track'], troughcolor=c['bg'], borderwidth=0, arrowcolor=c['muted'])

    def frame(self, parent, bg=None, border=False, **kw):
        return tk.Frame(parent, bg=bg or self.c['surface'], highlightbackground=self.c['line'], highlightthickness=1 if border else 0, **kw)

    def label(self, parent, text, size=10, color=None, bold=False, bg=None, **kw):
        return tk.Label(parent, text=text, font=(self.font, size, 'bold' if bold else 'normal'), bg=bg or parent.cget('bg'), fg=color or self.c['text'], **kw)

    def button(self, parent, text, command, kind='primary', **kw):
        c = self.c
        bg, fg, active = (c['blue'], '#FFFFFF', c['hover']) if kind == 'primary' else (c['soft'], c['blue'], c['track'])
        if kind == 'danger':
            bg, fg, active = c['red'], c['bg'] if self.theme == 'dark' else '#FFFFFF', c['red']
        if kind == 'ghost':
            bg, fg, active = parent.cget('bg'), c['muted'], c['track']
        b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=active, activeforeground=fg, relief='flat', borderwidth=0, font=(self.font, 10, 'bold'), padx=16, pady=10, cursor='hand2', highlightthickness=1, highlightbackground=bg, highlightcolor=c['blue'], **kw)
        b.bind('<Return>', lambda e: (b.invoke(), 'break')[1])
        b.bind('<Enter>', lambda e: b.configure(bg=active))
        b.bind('<Leave>', lambda e: b.configure(bg=bg))
        return b

    def resolve_logo_path(self, filename, settings_key=None):
        configured = None
        if settings_key:
            configured = self.settings.get(settings_key)
        if configured is None and settings_key in {'logo', 'sidebar_logo'}:
            configured = self.settings.get('logo') if settings_key == 'sidebar_logo' else self.settings.get('sidebar_logo')
        if configured:
            candidate = Path(configured).expanduser()
            if candidate.is_absolute():
                return candidate
            for base in (APP_DIR, APP_DIR / 'app_data'):
                resolved = base / candidate
                if resolved.exists():
                    return resolved
            return APP_DIR / candidate
        return APP_DIR / filename

    def brand_logo(self, parent, filename, width, settings_key=None):
        resolved = self.resolve_logo_path(filename, settings_key)
        key = (str(resolved), width)
        if key not in self.logo_images:
            with Image.open(resolved) as source:
                image = source.convert('RGBA')
            height = round(image.height * width / image.width)
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            self.logo_images[key] = ImageTk.PhotoImage(image, master=self.root)
        return tk.Label(parent, image=self.logo_images[key], bg=parent.cget('bg'), bd=0)

    def notify(self, text):
        self.notice = text
        if hasattr(self, 'status') and self.status.winfo_exists():
            self.status.configure(text=text)

    def safe(self, callback):
        try:
            return callback()
        except ValidationError as exc:
            self.alert('Please check your information', str(exc))
        except SQLAlchemyError:
            logging.exception('Database operation failed')
            self.alert('Unable to save', 'The database is unavailable. No changes were committed. Please try again.')
        return None

    def ask(self, title, text, action='Continue', danger=False):
        previous = self.modal
        parent = previous if previous and previous.winfo_exists() else self.root
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=self.c['surface'])
        dialog.resizable(False, False)
        dialog.transient(parent)
        body = self.frame(dialog)
        body.pack(fill='both', expand=True, padx=26, pady=24)
        self.label(body, title, 16, bold=True).pack(anchor='w', pady=(0, 10))
        self.label(body, text, 10, color=self.c['muted'], wraplength=410, justify='left').pack(anchor='w', pady=(0, 24))
        answer = [False]
        def done(value=False):
            answer[0] = value
            dialog.destroy()
        row = self.frame(body)
        row.pack(fill='x')
        cancel = self.button(row, 'Cancel', lambda: done(False), 'secondary')
        cancel.pack(side='left')
        self.button(row, action, lambda: done(True), 'danger' if danger else 'primary').pack(side='right')
        dialog.protocol('WM_DELETE_WINDOW', done)
        dialog.bind('<Escape>', lambda e: done(False))
        dialog.bind('<Return>', lambda e: done(False) if dialog.focus_get() == cancel else None)
        self.center(dialog, 470)
        dialog.grab_set()
        cancel.focus_set()
        dialog.wait_window()
        if previous and previous.winfo_exists():
            previous.grab_set()
        return answer[0]

    def alert(self, title, text):
        previous = self.modal
        parent = previous if previous and previous.winfo_exists() else self.root
        win = tk.Toplevel(parent)
        win.title(title)
        win.configure(bg=self.c['surface'])
        win.transient(parent)
        win.resizable(False, False)
        body = self.frame(win)
        body.pack(padx=26, pady=24, fill='both', expand=True)
        self.label(body, title, 16, bold=True).pack(anchor='w', pady=(0, 12))
        self.label(body, text, wraplength=400, justify='left', color=self.c['muted']).pack(anchor='w', pady=(0, 20))
        b = self.button(body, 'OK', win.destroy)
        b.pack(anchor='e')
        win.bind('<Return>', lambda e: win.destroy())
        win.bind('<Escape>', lambda e: win.destroy())
        self.center(win, 460)
        win.grab_set()
        b.focus_set()
        win.wait_window()
        if previous and previous.winfo_exists():
            previous.grab_set()

    def center(self, win, width):
        win.update_idletasks()
        height = win.winfo_reqheight()
        x = max(0, self.root.winfo_x() + (self.root.winfo_width() - width) // 2)
        y = max(0, self.root.winfo_y() + (self.root.winfo_height() - height) // 2)
        win.geometry(f'{width}x{height}+{x}+{y}')

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def auth_dirty(self):
        return any(v.get() != self.auth_initial.get(k, '') for k, v in self.auth_vars.items())

    def leave_auth(self):
        return not self.auth_dirty() or self.ask('Discard unsaved information?', 'Your form has not been submitted. Discard these changes?', 'Discard changes')

    def toggle_theme(self):
        if self.modal:
            return
        # Preserve auth drafts and visibility state while changing the appearance.
        draft = {k: v.get() for k, v in self.auth_vars.items()} if not self.auth.user else {}
        initial = dict(self.auth_initial)
        self.theme = 'dark' if self.theme == 'light' else 'light'
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.settings_path.with_suffix('.tmp')
            temp.write_text(json.dumps({'theme': self.theme}))
            temp.replace(self.settings_path)
        except OSError:
            self.notice = 'Theme changed for this session; the preference could not be saved.'
        self.configure_style()
        if self.auth.user:
            self.render_shell()
        else:
            self.show_auth(self.auth_mode, draft)
            self.auth_initial = initial

    def show_auth(self, mode='login', draft=None):
        self.clear()
        self.auth_mode = mode
        self.auth_vars = {}
        outer = self.frame(self.root, self.c['bg'])
        outer.pack(fill='both', expand=True)
        outer.columnconfigure(0, weight=5, uniform='auth')
        outer.columnconfigure(1, weight=6, uniform='auth')
        outer.rowconfigure(0, weight=1)
        brand = self.frame(outer, self.c['nav'])
        brand.grid(row=0, column=0, sticky='nsew')
        self.brand_logo(brand, 'icon logo white.png', 400, settings_key='logo').place(relx=0.5, rely=0.5, anchor='center')
        right = self.frame(outer, self.c['bg'])
        right.grid(row=0, column=1, sticky='nsew')
        self.button(right, 'Light mode' if self.theme == 'dark' else 'Dark mode', self.toggle_theme, 'ghost').pack(anchor='e', padx=24, pady=20)
        form = self.frame(right, self.c['bg'])
        form.pack(expand=True, fill='x', padx=44, pady=(0, 35))
        self.label(form, 'START FRESH' if mode == 'signup' else 'WELCOME BACK', 9, self.c['blue'], True).pack(anchor='w', pady=(0, 10))
        self.label(form, 'Create your account' if mode == 'signup' else 'Your money, in view.', 24, bold=True).pack(anchor='w')
        self.label(form, 'Build better money habits with MoneyMate.' if mode == 'signup' else 'Log in to pick up where you left off.', color=self.c['muted']).pack(anchor='w', pady=(8, 22))
        fields = [('name', 'Full name')] if mode == 'signup' else []
        fields += [('email', 'Email address'), ('password', 'Password')]
        if mode == 'signup':
            fields += [('confirm', 'Confirm password')]
        first = None
        for key, label in fields:
            self.label(form, label, 10, bold=True).pack(anchor='w', pady=(7, 5))
            v = tk.StringVar(value=(draft or {}).get(key, ''))
            self.auth_vars[key] = v
            entry = ttk.Entry(form, textvariable=v, show='*' if key in ('password', 'confirm') else '')
            entry.pack(fill='x')
            entry.bind('<Return>', lambda e: self.submit_auth())
            first = first or entry
        visible = tk.BooleanVar(value=False)
        def toggle_password():
            for widget in form.winfo_children():
                if isinstance(widget, ttk.Entry) and str(widget.cget('textvariable')) in [str(self.auth_vars[k]) for k in ('password', 'confirm') if k in self.auth_vars]:
                    widget.configure(show='' if visible.get() else '*')
        tk.Checkbutton(form, text='Show password', variable=visible, command=toggle_password, highlightthickness=0, bg=self.c['bg'], fg=self.c['muted'], selectcolor=self.c['surface'], activebackground=self.c['bg'], activeforeground=self.c['text'], font=(self.font, 9)).pack(anchor='w', pady=(8, 8))
        if mode == 'signup':
            self.label(form, '8–128 characters, including a special character.', 9, self.c['muted']).pack(anchor='w', pady=(0, 8))
        self.button(form, 'Create account' if mode == 'signup' else 'Log in', self.submit_auth).pack(fill='x', pady=(10, 8))
        if mode == 'signup':
            self.button(form, 'Cancel and return to login', lambda: self.switch_auth('login'), 'secondary').pack(fill='x')
        else:
            self.button(form, 'New here? Create an account', lambda: self.switch_auth('signup'), 'ghost').pack(fill='x')
        self.label(form, 'Your data stays on this computer.', 9, self.c['muted']).pack(pady=(16, 0))
        self.auth_initial = {k: v.get() for k, v in self.auth_vars.items()}
        first.focus_set()

    def switch_auth(self, mode):
        if self.leave_auth():
            self.show_auth(mode)

    def submit_auth(self):
        def operation():
            values = {k: v.get() for k, v in self.auth_vars.items()}
            if self.auth_mode == 'signup':
                self.store.signup(values['name'], values['email'], values['password'], values['confirm'])
                self.show_auth('login', {'email': values['email']})
                self.alert('Account created', 'Your account is ready. Log in to start tracking your money.')
            else:
                self.store.login(values['email'], values['password'])
                for var in self.auth_vars.values():
                    var.set('')
                self.auth_vars.clear()
                self.auth_initial.clear()
                self.page, self.notice = 'Dashboard', 'You are logged in. Your records are private to this account.'
                self.overview_period = 'This month'
                self.budget_month = date.today().strftime('%Y-%m')
                self.render_shell()
        self.safe(operation)

    def render_shell(self):
        self.auth.require_user()
        self.clear()
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        sidebar = self.frame(self.root, self.c['nav'], width=212)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.pack_propagate(False)
        logo = self.frame(sidebar, self.c['nav'])
        logo.pack(fill='x', padx=22, pady=(30, 38))
        self.brand_logo(logo, 'white logo.png', 168, settings_key='sidebar_logo').pack(anchor='w')
        self.label(sidebar, 'WORKSPACE', 8, '#8EA8D3', True).pack(anchor='w', padx=24, pady=(0, 12))
        for i, name in enumerate(['Dashboard', 'Transactions', 'Budgets', 'Categories', 'Archive']):
            active = self.page == name
            bg = '#264B8D' if active else self.c['nav']
            b = tk.Button(sidebar, text=f'{["◈", "≡", "▤", "▦", "↶"][i]}    {name}', command=lambda n=name: self.navigate(n), anchor='w', bg=bg, fg='#FFFFFF' if active else self.c['nav_text'], activebackground='#264B8D', activeforeground='#FFFFFF', relief='flat', borderwidth=0, font=(self.font, 11, 'bold' if active else 'normal'), highlightthickness=0, padx=15, pady=13, cursor='hand2')
            b.pack(fill='x', padx=12, pady=3)
        bottom = self.frame(sidebar, self.c['nav'])
        bottom.pack(side='bottom', fill='x', padx=18, pady=24)
        self.button(bottom, 'Light mode' if self.theme == 'dark' else 'Dark mode', self.toggle_theme, 'secondary').pack(fill='x', pady=(0, 16))
        self.label(bottom, self.auth.user.name, 11, '#FFFFFF', True, wraplength=175, justify='left').pack(anchor='w')
        self.label(bottom, self.auth.user.email, 9, '#BBCBED', wraplength=175, justify='left').pack(anchor='w', pady=(5, 12))
        tk.Button(bottom, text='Log out', command=self.logout, bg=self.c['nav'], fg='#BBCBED', activebackground='#264B8D', activeforeground='#FFFFFF', relief='flat', font=(self.font, 10), anchor='w', highlightthickness=0, padx=0, cursor='hand2').pack(fill='x')
        main = self.frame(self.root, self.c['bg'])
        main.grid(row=0, column=1, sticky='nsew')
        header = self.frame(main, self.c['surface'])
        header.pack(fill='x')
        self.label(header, 'Personal finance  /  ' + self.page, 10, self.c['muted']).pack(side='left', padx=28, pady=19)
        self.label(header, date.today().strftime('%a, %d %b %Y'), 10, self.c['muted']).pack(side='right', padx=28)
        self.status = self.label(main, self.notice or 'Ready.  Ctrl+N adds a transaction.  Escape closes an open form.', 9, self.c['muted'], anchor='w')
        self.status.pack(side='bottom', fill='x', padx=28, pady=(6, 12))
        # Every page scrolls at smaller window sizes; wheel bindings are scoped to this canvas.
        holder = self.frame(main, self.c['bg'])
        holder.pack(fill='both', expand=True)
        canvas = tk.Canvas(holder, bg=self.c['bg'], highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient='vertical', command=canvas.yview)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        self.body = self.frame(canvas, self.c['bg'])
        window = canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        self.root.unbind('<MouseWheel>')
        self.root.unbind('<Button-4>')
        self.root.unbind('<Button-5>')
        def wheel(e):
            if self.modal or isinstance(e.widget, (ttk.Treeview, ttk.Combobox)):
                return
            if self.body.winfo_reqheight() > canvas.winfo_height():
                delta = (-1 if e.num == 4 else 1) if getattr(e, 'num', None) in (4, 5) else (-1 if e.delta > 0 else 1)
                canvas.yview_scroll(delta * 3, 'units')
        self.root.bind('<MouseWheel>', wheel)
        self.root.bind('<Button-4>', wheel)
        self.root.bind('<Button-5>', wheel)
        method = {'Dashboard': self.dashboard, 'Transactions': self.transactions_page, 'Budgets': self.budgets_page, 'Categories': self.categories_page, 'Archive': lambda: self.transactions_page(True)}[self.page]
        self.safe(method)

    def navigate(self, name):
        if not self.modal:
            self.page = name
            self.render_shell()

    def title(self, title, subtitle, action=None):
        row = self.frame(self.body, self.c['bg'])
        row.pack(fill='x', padx=28, pady=(26, 22))
        if action:
            self.button(row, action[0], action[1]).pack(side='right', padx=(16, 0))
        left = self.frame(row, self.c['bg'])
        left.pack(side='left', fill='x', expand=True)
        self.label(left, title, 25, bold=True).pack(anchor='w')
        self.label(left, subtitle, 10, self.c['muted'], wraplength=600, justify='left').pack(anchor='w', pady=(7, 0))

    def card(self, parent, label, value, note='', blue=False):
        bg = self.c['blue'] if blue else self.c['surface']
        card = self.frame(parent, bg, border=not blue)
        self.label(card, label.upper(), 9, '#DFE9FF' if blue else self.c['muted'], True).pack(anchor='w', padx=20, pady=(20, 10))
        value_label = self.label(card, cash(value), 23, '#FFFFFF' if blue else self.c['text'], True)
        value_label.pack(anchor='w', padx=20)
        def fit_value(event):
            size = 23
            while size > 12 and tkfont.Font(family=self.font, size=size, weight='bold').measure(cash(value)) > max(80, event.width - 42):
                size -= 1
            value_label.configure(font=(self.font, size, 'bold'))
        card.bind('<Configure>', fit_value)
        self.label(card, note, 9, '#DFE9FF' if blue else self.c['muted']).pack(anchor='w', padx=20, pady=(10, 20))
        return card

    def cards(self, items):
        row = self.frame(self.body, self.c['bg'])
        row.pack(fill='x', padx=28, pady=(0, 22))
        for i, args in enumerate(items):
            row.columnconfigure(i, weight=1, uniform='cards')
            self.card(row, *args).grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 8, 0 if i == len(items)-1 else 8))

    def dashboard(self):
        user = self.auth.user.name.split()[0]
        self.title(f'Hello, {user}.', 'A clear picture of your money. One good habit at a time.', ('+ Add transaction', self.transaction_dialog))
        period_row = self.frame(self.body, self.c['bg'])
        period_row.pack(fill='x', padx=28, pady=(0, 15))
        period = tk.StringVar(value=self.overview_period)
        combo = ttk.Combobox(period_row, textvariable=period, values=['This month', 'All time'], state='readonly', width=16)
        combo.pack(side='right')
        combo.bind('<<ComboboxSelected>>', lambda e: self.change_period(period.get()))
        label = month_label(date.today().strftime('%Y-%m')) if self.overview_period == 'This month' else 'All recorded dates'
        self.label(period_row, label, 11, self.c['muted'], True).pack(side='left')
        rows = self.store.transactions()
        if self.overview_period == 'This month':
            month = date.today().strftime('%Y-%m')
            rows = [t for t in rows if t['date'].strftime('%Y-%m') == month]
        income = sum(t['cents'] for t in rows if t['type'] == 'income')
        expense = sum(t['cents'] for t in rows if t['type'] == 'expense')
        self.cards([('Net balance', income-expense, 'Income minus expenses', True), ('Money in', income, 'Recorded income', False), ('Money out', expense, 'Recorded expenses', False)])
        middle = self.frame(self.body, self.c['bg'])
        middle.pack(fill='x', padx=28, pady=(0, 22))
        middle.columnconfigure(0, weight=3, uniform='middle')
        middle.columnconfigure(1, weight=2, uniform='middle')
        spending = self.frame(middle, border=True)
        spending.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self.label(spending, 'Where your money goes', 13, bold=True).pack(anchor='w', padx=20, pady=(20, 4))
        self.label(spending, 'Expense breakdown for the selected period', 9, self.c['muted']).pack(anchor='w', padx=20)
        groups = defaultdict(int)
        for t in rows:
            if t['type'] == 'expense':
                groups[t['category']] += t['cents']
        donut = tk.Canvas(spending, height=185, bg=self.c['surface'], highlightthickness=0)
        donut.pack(fill='x', padx=18, pady=12)
        def draw(e=None):
            donut.delete('all')
            x, y, d = 12, 12, 150
            palette = [self.c['blue'], '#4E9BE8', '#68B9C7', '#8977DC', '#A2B7DE']
            pairs = sorted(groups.items(), key=lambda kv: kv[1], reverse=True)
            if len(pairs) > 5:
                pairs = pairs[:4] + [('Other categories', sum(v for _, v in pairs[4:]))]
            donut.create_oval(x, y, x+d, y+d, fill=self.c['track'], outline='')
            start = 90
            for i, (cat, amt) in enumerate(pairs):
                extent = -360 * amt / expense if expense else 0
                if abs(extent) >= 359.99:
                    donut.create_oval(x, y, x+d, y+d, fill=palette[i], outline='')
                else:
                    donut.create_arc(x, y, x+d, y+d, start=start, extent=extent, fill=palette[i], outline=self.c['surface'], width=2)
                start += extent
                yy = 26 + i*29
                donut.create_oval(184, yy-4, 191, yy+3, fill=palette[i], outline='')
                short = cat if len(cat) <= 18 else cat[:16] + '…'
                donut.create_text(201, yy, text=short, anchor='w', fill=self.c['muted'], font=(self.font, 9))
                donut.create_text(max(330, donut.winfo_width()-8), yy, text=f'{amt/expense:.0%}', anchor='e', fill=self.c['text'], font=(self.font, 9, 'bold'))
            donut.create_oval(x+20, y+20, x+d-20, y+d-20, fill=self.c['surface'], outline='')
            donut.create_text(x+d/2, y+d/2-7, text=f'{len(groups)}', fill=self.c['text'], font=(self.font, 24, 'bold'))
            donut.create_text(x+d/2, y+d/2+20, text='categories', fill=self.c['muted'], font=(self.font, 9))
            if not groups:
                donut.create_text(190, 70, text='No expenses yet.\nYour breakdown starts here.', anchor='w', fill=self.c['muted'], font=(self.font, 10))
        donut.bind('<Configure>', draw)
        budget_card = self.frame(middle, border=True)
        budget_card.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self.label(budget_card, 'Your monthly plan', 13, bold=True).pack(anchor='w', padx=20, pady=(20, 5))
        self.label(budget_card, 'Current month · active records only', 9, self.c['muted']).pack(anchor='w', padx=20, pady=(0, 10))
        budgets = self.store.budgets(date.today().strftime('%Y-%m'))
        if not budgets:
            self.label(budget_card, 'Give every peso a purpose.', 12, bold=True).pack(anchor='w', padx=20, pady=(18, 6))
            self.label(budget_card, 'Set a category budget to get started.', 9, self.c['muted']).pack(anchor='w', padx=20)
        else:
            for b in budgets[:3]:
                _, spent = self.store.budget_status(b.category, b.month)
                self.progress(budget_card, b.category, spent, b.limit_cents, compact=True)
        self.button(budget_card, 'Manage budgets  →', lambda: self.navigate('Budgets'), 'ghost').pack(anchor='w', padx=10, pady=(8, 12))
        recent = self.frame(self.body, border=True)
        recent.pack(fill='x', padx=28, pady=(0, 20))
        head = self.frame(recent)
        head.pack(fill='x', padx=20, pady=(12, 6))
        self.label(head, 'Recent activity', 13, bold=True).pack(side='left')
        self.button(head, 'View all  →', lambda: self.navigate('Transactions'), 'ghost').pack(side='right')
        self.make_table(recent, rows[:4], 4)
        if not rows:
            self.label(recent, 'No transactions in this period. Add your first income or expense.', color=self.c['muted']).pack(pady=(0, 20))

    def change_period(self, value):
        self.overview_period = value
        self.render_shell()

    def make_table(self, parent, rows, height=8):
        frame = self.frame(parent)
        frame.pack(fill='both', expand=True, padx=12, pady=(6, 12))
        table = ttk.Treeview(frame, columns=('date','category','type','notes','amount'), show='headings', height=height, selectmode='extended')
        for col, title, width, anchor in [('date','DATE',105,'w'),('category','CATEGORY',150,'w'),('type','TYPE',85,'w'),('notes','NOTE',190,'w'),('amount','AMOUNT',155,'e')]:
            table.heading(col, text=title, anchor=anchor)
            table.column(col, width=width, minwidth=80, anchor=anchor, stretch=col in ('category','notes'))
        y = ttk.Scrollbar(frame, orient='vertical', command=table.yview)
        x = ttk.Scrollbar(frame, orient='horizontal', command=table.xview)
        table.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        table.grid(row=0, column=0, sticky='nsew')
        y.grid(row=0, column=1, sticky='ns')
        x.grid(row=1, column=0, sticky='ew')
        table.tag_configure('income', foreground=self.c['green'])
        table.tag_configure('expense', foreground=self.c['text'])
        self.fill_table(table, rows)
        return table

    def fill_table(self, table, rows):
        table.delete(*table.get_children())
        for t in rows:
            table.insert('', 'end', iid=str(t['id']), values=(str(t['date']), t['category'], t['type'].capitalize(), t['notes'], ('+ ' if t['type']=='income' else '− ') + cash(t['cents'])), tags=(t['type'],))

    def transactions_page(self, archived=False):
        self.title('Archive' if archived else 'Transactions', 'Archived records are excluded from all totals. Restore them whenever you need.' if archived else 'All your income and expenses, with room to correct a mistake.', None if archived else ('+ Add transaction', self.transaction_dialog))
        card = self.frame(self.body, border=True)
        card.pack(fill='both', expand=True, padx=28, pady=(0, 20))
        toolbar = self.frame(card)
        toolbar.pack(fill='x', padx=20, pady=18)
        self.search_var = tk.StringVar()
        self.type_var = tk.StringVar(value='All types')
        self.period_var = tk.StringVar(value='All dates')
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=29)
        search.pack(side='left', fill='x', expand=True, padx=(0, 12))
        self.label(card, 'Search by category, note, date, or amount', 9, self.c['muted']).pack(anchor='w', padx=20)
        for variable, choices in [(self.type_var, ['All types','Income','Expense']), (self.period_var,['All dates','This month'])]:
            ttk.Combobox(toolbar, textvariable=variable, values=choices, state='readonly', width=13).pack(side='left', padx=(0, 8))
        self.button(toolbar, 'Reset', self.reset_filters, 'ghost').pack(side='right')
        rows = self.store.transactions(archived)
        self.tx_rows = {t['id']: t for t in rows}
        table = self.make_table(card, rows, 7)
        self.transaction_table = table
        count = self.label(card, '', 9, self.c['muted'])
        count.pack(anchor='w', padx=20, pady=(0, 8))
        def refresh(*_):
            q = self.search_var.get().casefold().strip()
            selected = [t for t in rows if (self.type_var.get() == 'All types' or t['type'] == self.type_var.get().lower()) and (self.period_var.get() == 'All dates' or t['date'].strftime('%Y-%m') == date.today().strftime('%Y-%m')) and (not q or q in f"{t['category']} {t['notes']} {t['date']} {t['cents']/100:.2f}".casefold())]
            self.fill_table(table, selected)
            count.configure(text=f'{len(selected)} record(s)' + (' · No matching records. Clear filters or add a transaction.' if not selected else ' · Select a row to manage it.'))
        for v in (self.search_var, self.type_var, self.period_var):
            v.trace_add('write', refresh)
        refresh()
        row = self.frame(card)
        row.pack(fill='x', padx=20, pady=(0, 20))
        if archived:
            self.button(row, 'Restore selected', lambda: self.archive_selected(table, False), 'secondary').pack(side='left')
        else:
            self.button(row, 'Edit selected', lambda: self.edit_selected(table), 'secondary').pack(side='left')
            self.button(row, 'Archive selected', lambda: self.archive_selected(table, True), 'ghost').pack(side='left', padx=8)
            table.bind('<Double-1>', lambda e: self.edit_selected(table))
        self.button(row, 'Clear selection', lambda: table.selection_remove(*table.selection()), 'ghost').pack(side='right')
        self.label(self.body, 'Nothing is permanently deleted. Use Archive to undo a removal.' if not archived else 'Restoring a record puts it back in your totals and budget calculations.', 9, self.c['muted']).pack(anchor='w', padx=28)

    def reset_filters(self):
        self.search_var.set('')
        self.type_var.set('All types')
        self.period_var.set('All dates')

    def edit_selected(self, table):
        selected = table.selection()
        if len(selected) != 1:
            self.alert('Select one transaction', 'Choose exactly one record to edit.')
            return
        self.transaction_dialog(self.tx_rows[int(selected[0])])

    def archive_selected(self, table, archived):
        ids = [int(i) for i in table.selection()]
        if not ids:
            self.alert('Select a transaction', 'Choose at least one record first.')
            return
        action = 'Archive' if archived else 'Restore'
        if self.ask(f'{action} {len(ids)} transaction(s)?', 'Archived records leave your totals and can be restored later.' if archived else 'These records will return to your transactions and financial totals.', action):
            def operation():
                self.store.archive_transactions(ids, archived)
                self.notice = f'{len(ids)} transaction(s) {"archived. Restore them from Archive." if archived else "restored."}'
                self.render_shell()
            self.safe(operation)

    def progress(self, parent, category, spent, limit, compact=False):
        part = self.frame(parent)
        part.pack(fill='x', padx=20, pady=8 if compact else 12)
        row = self.frame(part)
        row.pack(fill='x')
        pct = spent/limit if limit else 0
        color = self.c['red'] if pct > 1 else self.c['amber'] if pct >= .8 else self.c['blue']
        self.label(row, category, 10, bold=True).pack(side='left')
        self.label(row, f'{pct:.0%}', 10, color, True).pack(side='right')
        bar = tk.Canvas(part, height=7, bg=self.c['track'], highlightthickness=0)
        bar.pack(fill='x', pady=(8, 6))
        def draw(e):
            bar.delete('all')
            bar.create_rectangle(0, 0, e.width * min(pct, 1), 7, fill=color, outline='')
        bar.bind('<Configure>', draw)
        detail = (f'{cash(spent)} of {cash(limit)}') if not compact else f'{cash(spent)} spent'
        self.label(part, detail, 9, self.c['muted']).pack(anchor='w')
        if not compact:
            self.label(part, f'{cash(max(0, limit-spent))} remaining' if spent <= limit else f'{cash(spent-limit)} over budget', 9, color).pack(anchor='w', pady=(4, 0))

    def budgets_page(self):
        self.title('Make a plan.', 'Monthly limits that stay saved. Warnings help you decide, without blocking actual spending.', ('+ Set budget', self.budget_dialog))
        filters = self.frame(self.body, self.c['bg'])
        filters.pack(fill='x', padx=28, pady=(0, 18))
        self.label(filters, 'Budget month', bold=True).pack(side='left', padx=(0, 12))
        variable = tk.StringVar(value=self.budget_month)
        # Include saved/future periods by providing an editable field validated on Apply.
        month = ttk.Entry(filters, textvariable=variable, width=12)
        month.pack(side='left', padx=(0, 10))
        self.button(filters, 'Apply', lambda: self.apply_month(variable.get()), 'secondary').pack(side='left')
        self.label(filters, 'YYYY-MM', 9, self.c['muted']).pack(side='left', padx=12)
        budgets = self.store.budgets(self.budget_month)
        total = sum(b.limit_cents for b in budgets)
        spent = sum(t['cents'] for t in self.store.transactions() if t['type']=='expense' and t['date'].strftime('%Y-%m') == self.budget_month)
        budgeted = sum(self.store.budget_status(b.category, b.month)[1] for b in budgets)
        self.cards([('Planned budget', total, month_label(self.budget_month), True), ('All monthly spending', spent, 'Includes unbudgeted categories', False), ('Budget remaining', total-budgeted, 'Across budgeted categories', False)])
        panel = self.frame(self.body, border=True)
        panel.pack(fill='x', padx=28, pady=(0, 20))
        self.label(panel, 'Category budgets', 13, bold=True).pack(anchor='w', padx=20, pady=(20, 5))
        self.label(panel, 'On track below 80% · Near limit at 80% · Over budget above 100%', 9, self.c['muted']).pack(anchor='w', padx=20, pady=(0, 12))
        if not budgets:
            self.label(panel, 'No budgets for this month yet.', 13, bold=True).pack(padx=20, pady=(24, 8))
            self.label(panel, 'Start with the category you spend on most.', color=self.c['muted']).pack(pady=(0, 25))
        for b in budgets:
            block = self.frame(panel)
            block.pack(fill='x', pady=(0, 12))
            actions = self.frame(block)
            actions.pack(side='right', padx=20)
            self.button(actions, 'Edit', lambda row=b: self.budget_dialog(row), 'secondary').pack(side='left', padx=(0, 8))
            self.button(actions, 'Remove', lambda row=b: self.remove_budget(row), 'ghost').pack(side='left')
            area = self.frame(block)
            area.pack(side='left', fill='x', expand=True)
            _, used = self.store.budget_status(b.category, b.month)
            self.progress(area, b.category, used, b.limit_cents)

    def apply_month(self, month):
        from services import valid_month
        def operation():
            self.budget_month = valid_month(month.strip())
            self.render_shell()
        self.safe(operation)

    def remove_budget(self, row):
        if self.ask('Remove this budget?', f'Remove the {row.category} limit for {month_label(row.month)}? Your transactions will stay saved.', 'Remove budget', True):
            def operation():
                self.store.remove_budget(row.id)
                self.notice = 'Budget removed. Your transaction history is unchanged.'
                self.render_shell()
            self.safe(operation)

    def categories_page(self):
        self.title('Your own categories.', 'Organize money in a way that makes sense to you.', ('+ Add category', self.category_dialog))
        self.label(self.body, 'Custom categories appear in transaction forms and expense budget choices.', 10, self.c['muted']).pack(anchor='w', padx=28, pady=(0, 18))
        custom = self.store.custom_categories()
        row = self.frame(self.body, self.c['bg'])
        row.pack(fill='x', padx=28, pady=(0, 20))
        for i, kind in enumerate(['income','expense']):
            row.columnconfigure(i, weight=1, uniform='categories')
            panel = self.frame(row, border=True)
            panel.grid(row=0, column=i, sticky='nsew', padx=(0, 10) if i==0 else (10, 0))
            self.label(panel, kind.capitalize() + ' categories', 14, bold=True).pack(anchor='w', padx=20, pady=(22, 14))
            from services import BUILT_INS
            for name in BUILT_INS[kind]:
                item = self.frame(panel)
                item.pack(fill='x', padx=20, pady=8)
                self.label(item, name, 10).pack(side='left')
                self.label(item, 'Built-in', 8, self.c['muted']).pack(side='right')
            self.label(panel, 'YOUR CATEGORIES', 8, self.c['blue'], True).pack(anchor='w', padx=20, pady=(24, 10))
            own = [c for c in custom if c.type==kind]
            for category in own:
                item = self.frame(panel)
                item.pack(fill='x', padx=20, pady=4)
                self.label(item, category.name, 10).pack(side='left')
                self.button(item, 'Remove', lambda c=category: self.remove_category(c), 'ghost').pack(side='right')
            if not own:
                self.label(panel, 'No custom categories yet.', 10, self.c['muted']).pack(anchor='w', padx=20)
            self.label(panel, 'Historical transactions keep their category.', 9, self.c['muted']).pack(anchor='w', padx=20, pady=22)

    def remove_category(self, row):
        if self.ask('Remove category?', f'{row.name} will be hidden from new transaction choices. Existing records and budgets stay unchanged. Add the same name again to bring it back.', 'Remove category'):
            def operation():
                self.store.remove_category(row.id)
                self.notice = 'Category removed from new choices. Add it again to restore it.'
                self.render_shell()
            self.safe(operation)

    def transaction_dialog(self, existing=None):
        if self.modal or not self.auth.user:
            return
        dialog = FormDialog(self, 'Edit transaction' if existing else 'Add transaction', 'Changes stay in this form until you save.')
        kind = dialog.combo('type', 'Transaction type', ['Expense','Income'], existing['type'].capitalize() if existing else 'Expense')
        categories = self.store.categories(kind.get().lower())
        if existing and existing['category'] not in categories:
            categories.append(existing['category'])
        category = dialog.combo('category', 'Category', categories, existing['category'] if existing else categories[0])
        def type_change(e):
            options = self.store.categories(kind.get().lower())
            dialog.fields['category'].configure(values=options)
            category.set(options[0])
        dialog.fields['type'].bind('<<ComboboxSelected>>', type_change)
        dialog.entry('amount', 'Amount (PHP)', f"{existing['cents']/100:.2f}" if existing else '')
        dialog.entry('date', 'Date (YYYY-MM-DD)', str(existing['date']) if existing else date.today().isoformat())
        dialog.entry('notes', 'Note (optional, up to 300 characters)', existing['notes'] if existing else '')
        def save():
            values = dialog.values()
            args = (values['type'].lower(), values['category'], values['amount'], values['date'], values['notes'])
            result = self.store.save_transaction(*args, transaction_id=existing['id'] if existing else None)
            if result.get('over_budget'):
                if not self.ask('This goes over your budget', f"Your {values['category']} spending would reach {cash(result['projected'])}, above a {cash(result['limit'])} limit. Save this expense anyway?", 'Save expense'):
                    return
                self.store.save_transaction(*args, transaction_id=existing['id'] if existing else None, allow_over_budget=True)
            self.notice = 'Transaction updated.' if existing else 'Transaction saved.'
            dialog.finish()
            self.render_shell()
        dialog.complete(save, 'Save changes' if existing else 'Save transaction', focus='amount')

    def budget_dialog(self, existing=None):
        if self.modal:
            return
        dialog = FormDialog(self, 'Edit budget' if existing else 'Set a monthly budget', 'Set a limit. Your transactions will never be blocked.')
        options = self.store.categories('expense')
        if existing and existing.category not in options:
            options.append(existing.category)
        dialog.combo('category', 'Expense category', options, existing.category if existing else options[0])
        dialog.entry('month', 'Budget month (YYYY-MM)', existing.month if existing else self.budget_month)
        if existing:
            dialog.fields['category'].configure(state='disabled')
            dialog.fields['month'].configure(state='disabled')
        dialog.entry('amount', 'Budget limit (PHP)', f'{existing.limit_cents/100:.2f}' if existing else '')
        def save():
            values = dialog.values()
            if not existing and any(b.category == values['category'] for b in self.store.budgets(values['month'])):
                if not self.ask('Replace existing budget?', 'This category already has a budget for the selected month. Replace its limit?', 'Replace limit'):
                    return
            self.store.save_budget(values['category'], values['month'], values['amount'])
            self.budget_month = values['month']
            self.notice = 'Budget saved for ' + month_label(self.budget_month) + '.'
            dialog.finish()
            self.render_shell()
        dialog.complete(save, 'Save budget', focus='amount')

    def category_dialog(self):
        if self.modal:
            return
        dialog = FormDialog(self, 'Add a category', 'It will be available as soon as you save.')
        dialog.entry('name', 'Category name')
        dialog.combo('type', 'Category type', ['Expense','Income'], 'Expense')
        def save():
            values = dialog.values()
            self.store.add_category(values['name'], values['type'].lower())
            self.notice = 'Category added. It is ready to use in your forms.'
            dialog.finish()
            self.render_shell()
        dialog.complete(save, 'Save category', focus='name')

    def logout(self):
        if self.modal:
            self.modal.cancel()
            return
        if self.ask('Log out of MoneyMate?', 'Your saved records will stay on this computer. You will return to the login screen.', 'Log out'):
            self.auth.logout()
            self.notice = ''
            self.auth_vars.clear()
            self.auth_initial.clear()
            self.tx_rows = {}
            self.page = 'Dashboard'
            self.show_auth()

    def escape(self, event=None):
        if self.modal:
            self.modal.cancel()
        elif not self.auth.user and self.auth_mode == 'signup':
            self.switch_auth('login')

    def close(self):
        if self.modal:
            self.modal.cancel()
            return
        if not self.auth.user and not self.leave_auth():
            return
        if self.auth.user and not self.ask('Close MoneyMate?', 'All saved records are safe. Your login session will end.', 'Close application'):
            return
        self.auth.logout()
        self.root.destroy()

class FormDialog(tk.Toplevel):
    def __init__(self, app, title, subtitle):
        super().__init__(app.root)
        self.app = app
        app.modal = self
        self.vars, self.fields = {}, {}
        self.title(title)
        self.configure(bg=app.c['surface'])
        self.resizable(False, False)
        self.transient(app.root)
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self.bind('<Escape>', lambda e: self.cancel())
        self.body = app.frame(self)
        self.body.pack(fill='both', expand=True, padx=28, pady=24)
        app.label(self.body, title, 21, bold=True).pack(anchor='w')
        app.label(self.body, subtitle, 10, app.c['muted'], wraplength=435, justify='left').pack(anchor='w', pady=(8, 18))

    def entry(self, key, label, value=''):
        self.app.label(self.body, label, 10, bold=True).pack(anchor='w', pady=(8, 5))
        var = tk.StringVar(value=value)
        field = ttk.Entry(self.body, textvariable=var)
        field.pack(fill='x')
        self.vars[key], self.fields[key] = var, field
        return var

    def combo(self, key, label, options, value):
        self.app.label(self.body, label, 10, bold=True).pack(anchor='w', pady=(8, 5))
        var = tk.StringVar(value=value)
        field = ttk.Combobox(self.body, textvariable=var, values=options, state='readonly')
        field.pack(fill='x')
        self.vars[key], self.fields[key] = var, field
        return var

    def values(self):
        return {k: v.get() for k, v in self.vars.items()}

    def complete(self, save, label, focus=None):
        self.initial = self.values()
        self.app.label(self.body, 'Cancel or Esc leaves your saved records unchanged.', 9, self.app.c['muted']).pack(anchor='w', pady=(20, 14))
        row = self.app.frame(self.body)
        row.pack(fill='x')
        self.app.button(row, 'Cancel', self.cancel, 'secondary').pack(side='left')
        self.app.button(row, label, lambda: self.app.safe(save)).pack(side='right')
        self.bind('<Control-Return>', lambda e: self.app.safe(save))
        self.app.center(self, 510)
        self.grab_set()
        self.fields[focus or next(iter(self.fields))].focus_set()

    def cancel(self):
        if self.values() != getattr(self, 'initial', {}) and not self.app.ask('Discard unsaved changes?', 'Nothing has been saved. Discard your edits and close this form?', 'Discard changes'):
            return
        self.finish()

    def finish(self):
        self.grab_release()
        self.app.modal = None
        self.destroy()
        self.app.root.focus_set()


def main():
    initialize_database()
    root = tk.Tk()
    app = MoneyMateApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
