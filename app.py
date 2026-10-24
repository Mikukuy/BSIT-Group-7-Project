from datetime import datetime
import re
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from models import Session, User, Transaction, Category, Budget, hash_password

root = tk.Tk()
root.title("MoneyMate - Login")
root.geometry("900x500")
root.configure(bg="#FFFFFF")

# Session state
current_user_id = None

INCOME_DEFAULTS = ["Allowance", "Salary/Wages", "Freelance/Side Job", "Scholarship/Grant", "Gift", "Other"]
EXPENSE_DEFAULTS = ["Food", "Transportation", "Bills", "School Supplies", "Shopping", "Other"]


def get_custom_categories(tx_type):
    """Custom categories of the logged-in user, read from the database."""
    session = Session()
    rows = (
        session.query(Category)
        .filter_by(user_id=current_user_id, type=tx_type)
        .order_by(Category.id)
        .all()
    )
    names = [c.name for c in rows]
    session.close()
    return names


def category_options(tx_type):
    """Default categories plus the user's custom ones."""
    defaults = INCOME_DEFAULTS if tx_type == "income" else EXPENSE_DEFAULTS
    return defaults + get_custom_categories(tx_type)


def get_budgets():
    """Budgets of the logged-in user as {category: limit}, read from the database."""
    session = Session()
    budgets = {
        b.category: b.limit_amount
        for b in session.query(Budget).filter_by(user_id=current_user_id).order_by(Budget.id).all()
    }
    session.close()
    return budgets


def user_transactions(session):
    """Transactions of the logged-in user. Works with or without a user_id column."""
    query = session.query(Transaction)
    if hasattr(Transaction, "user_id") and current_user_id is not None:
        query = query.filter_by(user_id=current_user_id)
    return query


# Login and Signup Functions
def check_signup():
    name = signup_name_entry.get().strip()
    email = signup_email_entry.get().strip().lower()
    password = signup_password_entry.get()

    if name in ("", "Username") or email in ("", "Email address") or password in ("", "Password"):
        messagebox.showerror("Error", "Please fill out all fields.")
        return

    if "@" not in email or "." not in email:
        messagebox.showerror("Error", "Please enter a valid email address.")
        return

    if len(password) < 8 or len(password) > 13:
        messagebox.showerror("Error", "Password must be 8 to 13 characters long.")
        return

    if len(name) < 3 or len(name) > 20:
        messagebox.showerror("Error", "Username must be 3 to 20 characters long.")
        return

    if not any(not c.isalnum() for c in password):
        messagebox.showerror("Error", "Password must include at least one special character.")
        return

    session = Session()
    existing = session.query(User).filter_by(email=email).first()
    if existing:
        session.close()
        messagebox.showerror("Error", "An account with that email already exists.")
        return

    session.add(User(full_name=name, email=email, password_hash=hash_password(password)))
    session.commit()
    session.close()

    messagebox.showinfo("Success", "Account created! Please log in.")
    show_login()


def check_login():
    global current_user_id
    email = username_entry.get().strip().lower()
    password = password_entry.get()

    session = Session()
    user = session.query(User).filter_by(email=email).first()
    full_name = user.full_name if user else None
    valid = user is not None and user.password_hash == hash_password(password)
    user_id = user.id if valid else None
    session.close()

    if valid:
        current_user_id = user_id
        root.withdraw()
        open_dashboard(full_name)
    else:
        messagebox.showerror("Error", "Invalid email or password.")


def clear_placeholder(event, entry, placeholder):
    if entry.get() == placeholder:
        entry.delete(0, tk.END)


def toggle_password_visibility(entry, button):
    if entry.cget("show") == "*":
        entry.config(show="")
        button.config(text="🙈")
    else:
        entry.config(show="*")
        button.config(text="👁")


def make_input_field(parent, icon_text, placeholder, is_password=False):
    frame = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#CCCCCC", highlightthickness=1)
    frame.pack(padx=60, pady=8, fill="x")

    icon = tk.Label(frame, text=icon_text, font=("Arial", 12), bg="#FFFFFF", fg="#000080")
    icon.pack(side="left", padx=(10, 5), pady=10)

    entry = tk.Entry(frame, font=("Montserrat", 11), border=0, show="*" if is_password else "")
    entry.insert(0, placeholder)
    entry.pack(side="left", fill="x", expand=True, pady=10)
    entry.bind("<FocusIn>", lambda event: clear_placeholder(event, entry, placeholder))

    if is_password:
        toggle_button = tk.Button(frame, text="👁", font=("Arial", 10), bg="#FFFFFF", fg="#000080", border=0)
        toggle_button.config(command=lambda: toggle_password_visibility(entry, toggle_button))
        toggle_button.pack(side="left", padx=(0, 10))

    return entry


def clear_right_frame():
    for widget in right_frame.winfo_children():
        widget.destroy()


# Login UI
def show_login():
    global username_entry, password_entry
    clear_right_frame()

    welcome_label = tk.Label(right_frame, text="Welcome Back", font=("Montserrat", 20, "bold"), fg="#000080", bg="#FFFFFF")
    welcome_label.pack(anchor="w", padx=60, pady=(100, 5))

    subtitle_label = tk.Label(right_frame, text="Track your income, expenses, and build a better future.", font=("Montserrat", 10), fg="#666666", bg="#FFFFFF")
    subtitle_label.pack(anchor="w", padx=60, pady=(0, 30))

    username_entry = make_input_field(right_frame, "✉", "Email address")
    password_entry = make_input_field(right_frame, "🔒", "Password", is_password=True)

    login_button = tk.Button(right_frame, text="Log In", font=("Montserrat", 11, "bold"), bg="#000080", fg="white", relief="flat", command=check_login)
    login_button.pack(padx=60, pady=20, ipady=8, fill="x")

    def on_enter(event):
        login_button.config(bg="#0000A0")

    def on_leave(event):
        login_button.config(bg="#000080")

    login_button.bind("<Enter>", on_enter)
    login_button.bind("<Leave>", on_leave)

    switch_label = tk.Label(right_frame, text="Don't have an account? Sign Up", font=("Montserrat", 9, "underline"), fg="#000080", bg="#FFFFFF", cursor="hand2")
    switch_label.pack(pady=10)
    switch_label.bind("<Button-1>", lambda event: show_signup())


# Signup UI
def show_signup():
    global signup_name_entry, signup_email_entry, signup_password_entry
    clear_right_frame()

    title_label = tk.Label(right_frame, text="Create Your Account", font=("Montserrat", 20, "bold"), fg="#000080", bg="#FFFFFF")
    title_label.pack(anchor="w", padx=60, pady=(80, 5))

    subtitle_label = tk.Label(right_frame, text="Get started and take control of your finances today.", font=("Montserrat", 10), fg="#666666", bg="#FFFFFF")
    subtitle_label.pack(anchor="w", padx=60, pady=(0, 20))

    signup_name_entry = make_input_field(right_frame, "👤", "Username")
    signup_email_entry = make_input_field(right_frame, "✉", "Email address")
    signup_password_entry = make_input_field(right_frame, "🔒", "Password", is_password=True)

    signup_button = tk.Button(right_frame, text="Sign Up", font=("Montserrat", 11, "bold"), bg="#000080", fg="white", relief="flat", command=check_signup)
    signup_button.pack(padx=60, pady=20, ipady=8, fill="x")

    switch_label = tk.Label(right_frame, text="Already have an account? Log In", font=("Montserrat", 9, "underline"), fg="#000080", bg="#FFFFFF", cursor="hand2")
    switch_label.pack(pady=10)
    switch_label.bind("<Button-1>", lambda event: show_login())


# Left Side (Logo Panel)
left_frame = tk.Frame(root, bg="#FFFFFF", width=400)
left_frame.pack(side="left", fill="both", expand=True)

logo_image = Image.open("moneymate.jpg")
logo_image = logo_image.resize((600, 600))
logo_photo = ImageTk.PhotoImage(logo_image)

logo_label = tk.Label(left_frame, image=logo_photo, bg="#FFFFFF")
logo_label.pack(expand=True)
logo_label.image = logo_photo

# Divider
divider = tk.Frame(root, bg="#CCCCCC", width=1.5, height=850)
divider.pack(side="left")
divider.pack_propagate(False)

# Right Side (Login Panel)
right_frame = tk.Frame(root, bg="#FFFFFF", width=500)
right_frame.pack(side="right", fill="both", expand=True)


# Dashboard UI
def open_dashboard(full_name):
    dashboard = tk.Toplevel(root)
    dashboard.title("MoneyMate - Dashboard")
    dashboard.geometry("1100x720")
    dashboard.configure(bg="#F4F7FB")
    dashboard.protocol("WM_DELETE_WINDOW", root.destroy)

    # Sidebar
    sidebar = tk.Frame(dashboard, bg="#FFFFFF", width=220)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    tk.Label(sidebar, text="MoneyMate", font=("Montserrat", 14, "bold"),
             fg="#000080", bg="#FFFFFF").pack(pady=30)

    # Main Contents Area
    content = tk.Frame(dashboard, bg="#F4F7FB")
    content.pack(side="right", fill="both", expand=True)

    def clear_content():
        for widget in content.winfo_children():
            widget.destroy()

    def show_dashboard_page():
        clear_content()

        # Pull Data from the Database
        session = Session()
        transactions = user_transactions(session).order_by(Transaction.id.desc()).all()
        rows = [(t.id, str(t.date), t.type, t.category, t.amount) for t in transactions]
        session.close()

        total_income = sum(r[4] for r in rows if r[2] == "income")
        total_expense = sum(r[4] for r in rows if r[2] == "expense")
        balance = total_income - total_expense

        # Top Bar
        topbar = tk.Frame(content, bg="#F4F7FB")
        topbar.pack(fill="x", padx=30, pady=(20, 0))
        initials = "".join(w[0] for w in full_name.split()[:2]).upper()
        tk.Label(topbar, text=initials, font=("Montserrat", 10, "bold"), fg="white",
                 bg="#000080", width=4, height=2).pack(side="right")

        # Greeting Text - Dashboard
        tk.Label(content, text=f"Hello, {full_name}!", font=("Montserrat", 20, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(15, 0))
        tk.Label(content, text="Here's your financial overview for today.", font=("Montserrat", 11),
                 fg="#666666", bg="#F4F7FB").pack(anchor="w", padx=30)

        # Statistics Cards - Dashboard
        def stat_card(parent, title, value):
            card = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
            tk.Label(card, text=title, font=("Montserrat", 10), fg="#666666",
                     bg="#FFFFFF").pack(anchor="w", padx=20, pady=(12, 0))
            tk.Label(card, text=value, font=("Montserrat", 18, "bold"), fg="#000080",
                     bg="#FFFFFF").pack(anchor="w", padx=20, pady=(0, 12))
            return card

        cards = tk.Frame(content, bg="#F4F7FB")
        cards.pack(fill="x", padx=30, pady=15)
        card_data = [
            ("Total Balance", f"₱ {balance:,.2f}"),
            ("Income", f"₱ {total_income:,.2f}"),
            ("Total Expenses", f"₱ {total_expense:,.2f}"),
        ]
        for i, (title, value) in enumerate(card_data):
            cards.columnconfigure(i, weight=1, uniform="card")
            stat_card(cards, title, value).grid(row=0, column=i, sticky="ew",
                                                padx=(0 if i == 0 else 10, 0))

        # Middle Row: Spending Overview and Recent Transactions
        middle = tk.Frame(content, bg="#F4F7FB")
        middle.pack(fill="x", padx=30)
        middle.columnconfigure(0, weight=1, uniform="mid")
        middle.columnconfigure(1, weight=1, uniform="mid")

        # Spending Overview (Donut Graph) - Canvas
        spend = tk.Frame(middle, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
        spend.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(spend, text="Spending Overview", font=("Montserrat", 11, "bold"),
                 fg="#000080", bg="#FFFFFF").pack(anchor="w", padx=20, pady=(15, 5))

        body = tk.Frame(spend, bg="#FFFFFF")
        body.pack(fill="x", padx=20, pady=(0, 15))

        canvas = tk.Canvas(body, width=170, height=170, bg="#FFFFFF", highlightthickness=0)
        canvas.pack(side="left")

        by_cat = {}
        for r in rows:
            if r[2] == "expense":
                by_cat[r[3]] = by_cat.get(r[3], 0) + r[4]
        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        palette = ["#0B5ED7", "#2F80ED", "#5B9CF2", "#8DB8F7", "#B9D3FA", "#DCE8FC"]

        if total_expense > 0:
            start = 90
            for i, (cat, amt) in enumerate(sorted_cats):
                extent = max(-359.99, -360 * amt / total_expense)
                canvas.create_arc(15, 15, 155, 155, start=start, extent=extent,
                                  style="arc", width=26, outline=palette[i % len(palette)])
                start += extent
        else:
            canvas.create_arc(15, 15, 155, 155, start=0, extent=359.99,
                              style="arc", width=26, outline="#E6EBFA")

        canvas.create_text(85, 78, text=f"₱{total_expense:,.0f}", font=("Montserrat", 12, "bold"), fill="#000080")
        canvas.create_text(85, 98, text="Total spent", font=("Montserrat", 8), fill="#666666")

        legend = tk.Frame(body, bg="#FFFFFF")
        legend.pack(side="left", padx=(20, 0), fill="x", expand=True)
        if sorted_cats:
            for i, (cat, amt) in enumerate(sorted_cats[:6]):
                pct = amt / total_expense * 100
                line = tk.Frame(legend, bg="#FFFFFF")
                line.pack(fill="x", pady=2)
                tk.Label(line, text="●", fg=palette[i % len(palette)], bg="#FFFFFF").pack(side="left")
                tk.Label(line, text=cat, font=("Montserrat", 9), fg="#000080",
                         bg="#FFFFFF").pack(side="left", padx=6)
                tk.Label(line, text=f"{pct:.0f}%", font=("Montserrat", 9, "bold"),
                         fg="#000080", bg="#FFFFFF").pack(side="right")
        else:
            tk.Label(legend, text="No expenses yet.", font=("Montserrat", 9),
                     fg="#666666", bg="#FFFFFF").pack(anchor="w")

        # Recent Transactions - Dashboard
        recent = tk.Frame(middle, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
        recent.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        header = tk.Frame(recent, bg="#FFFFFF")
        header.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(header, text="Recent Transactions", font=("Montserrat", 11, "bold"),
                 fg="#000080", bg="#FFFFFF").pack(side="left")
        see_all = tk.Label(header, text="See All", font=("Montserrat", 9, "underline"),
                           fg="#000080", bg="#FFFFFF", cursor="hand2")
        see_all.pack(side="right")
        see_all.bind("<Button-1>", lambda e: show_transactions_page())

        if rows:
            for r in rows[:4]:
                line = tk.Frame(recent, bg="#FFFFFF")
                line.pack(fill="x", padx=20, pady=4)
                left = tk.Frame(line, bg="#FFFFFF")
                left.pack(side="left")
                tk.Label(left, text=r[3], font=("Montserrat", 10), fg="#000080",
                         bg="#FFFFFF").pack(anchor="w")
                tk.Label(left, text=r[1], font=("Montserrat", 8), fg="#888888",
                         bg="#FFFFFF").pack(anchor="w")
                is_income = r[2] == "income"
                tk.Label(line, text=f"{'+' if is_income else '-'} ₱{r[4]:,.2f}",
                         font=("Montserrat", 10, "bold"),
                         fg="#16A34A" if is_income else "#DC2626",
                         bg="#FFFFFF").pack(side="right")
        else:
            tk.Label(recent, text="No transactions yet.", font=("Montserrat", 9),
                     fg="#666666", bg="#FFFFFF").pack(anchor="w", padx=20, pady=10)

        tk.Button(recent, text="+ Add Transaction", font=("Montserrat", 10, "bold"),
                  fg="white", bg="#000080", activebackground="#1A1AA0", activeforeground="white",
                  relief="flat", command=show_transactions_page).pack(anchor="e", padx=20, pady=(10, 15), ipadx=10, ipady=4)

        # Transaction History Table - Dashboard
        tk.Label(content, text="Transaction History", font=("Montserrat", 12, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(15, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                        foreground="#000080", rowheight=26, font=("Montserrat", 9), borderwidth=0)
        style.configure("Treeview.Heading", background="#F4F7FB", foreground="#000080",
                        font=("Montserrat", 9, "bold"), relief="flat")

        table = ttk.Treeview(content, columns=("ID", "Date", "Type", "Category", "Amount"),
                             show="headings", height=4)
        for col, width in [("ID", 50), ("Date", 120), ("Type", 100), ("Category", 160), ("Amount", 120)]:
            table.heading(col, text=col if col != "Amount" else "Amount (₱)")
            table.column(col, width=width, anchor="w")
        for r in rows[:4]:
            table.insert("", "end", values=(r[0], r[1], r[2].capitalize(), r[3], f"{r[4]:,.2f}"))
        table.pack(fill="x", padx=30, pady=(0, 20))

    def show_transactions_page():
        clear_content()

        income_types = category_options("income")
        expense_types = category_options("expense")

        tk.Label(content, text="Transactions", font=("Montserrat", 20, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(30, 10))

        # Forms Row
        forms = tk.Frame(content, bg="#F4F7FB")
        forms.pack(fill="x", padx=30)
        forms.columnconfigure(0, weight=1, uniform="f")
        forms.columnconfigure(1, weight=1, uniform="f")

        def build_form(column, title, options, tx_type):
            box = tk.Frame(forms, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
            box.grid(row=0, column=column, sticky="nsew",
                     padx=(0, 10) if column == 0 else (10, 0))

            tk.Label(box, text=title, font=("Montserrat", 12, "bold"),
                     fg="#000080", bg="#FFFFFF").pack(anchor="w", padx=20, pady=(15, 5))

            tk.Label(box, text="Category", font=("Montserrat", 9), fg="#666666",
                     bg="#FFFFFF").pack(anchor="w", padx=20)
            category = ttk.Combobox(box, values=options, state="readonly", font=("Montserrat", 10))
            category.current(0)
            category.pack(fill="x", padx=20, pady=(2, 10), ipady=4)

            tk.Label(box, text="Amount (₱)", font=("Montserrat", 9), fg="#666666",
                     bg="#FFFFFF").pack(anchor="w", padx=20)
            amount = tk.Entry(box, font=("Montserrat", 10), relief="solid", bd=1)
            amount.pack(fill="x", padx=20, pady=(2, 15), ipady=6)

            def save():
                try:
                    value = float(amount.get().replace(",", ""))
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid amount.")
                    return
                if value <= 0 or value > 1000000:
                    messagebox.showerror("Error", "Amount must be above 0 and not more than ₱1,000,000.")
                    return

                # Budget warning (this month's spending in the chosen category)
                chosen = category.get()
                budgets = get_budgets()
                if tx_type == "expense" and chosen in budgets:
                    now = datetime.now()
                    chk = Session()
                    spent = sum(
                        t.amount
                        for t in user_transactions(chk).filter_by(type="expense", category=chosen).all()
                        if t.date.month == now.month and t.date.year == now.year
                    )
                    chk.close()
                    if spent + value > budgets[chosen]:
                        messagebox.showwarning(
                            "Budget Warning",
                            f"This will go over your ₱{budgets[chosen]:,.2f} budget for {chosen}.",
                        )

                session = Session()
                tx = Transaction(type=tx_type, category=chosen, amount=value)
                if hasattr(Transaction, "user_id"):
                    tx.user_id = current_user_id
                session.add(tx)
                session.commit()
                session.close()
                show_transactions_page()

            tk.Button(box, text=f"Add {tx_type.capitalize()}", font=("Montserrat", 10, "bold"),
                      fg="white", bg="#000080", activebackground="#1A1AA0",
                      activeforeground="white", relief="flat",
                      command=save).pack(fill="x", padx=20, pady=(0, 20), ipady=6)

        build_form(0, "Add Income", income_types, "income")
        build_form(1, "Add Expense", expense_types, "expense")

        # Table of All Transactions - TreeView
        tk.Label(content, text="All Transactions", font=("Montserrat", 12, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(20, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                        foreground="#000080", rowheight=26, font=("Montserrat", 9), borderwidth=0)
        style.configure("Treeview.Heading", background="#F4F7FB", foreground="#000080",
                        font=("Montserrat", 9, "bold"), relief="flat")

        table_frame = tk.Frame(content, bg="#F4F7FB")
        table_frame.pack(fill="both", expand=True, padx=30)

        table = ttk.Treeview(table_frame, columns=("ID", "Date", "Type", "Category", "Amount"),
                             show="headings", height=6)
        for col, width in [("ID", 50), ("Date", 120), ("Type", 100), ("Category", 160), ("Amount", 120)]:
            table.heading(col, text=col if col != "Amount" else "Amount (₱)")
            table.column(col, width=width, anchor="w")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        table.pack(side="left", fill="both", expand=True)

        session = Session()
        for t in user_transactions(session).order_by(Transaction.id.desc()).all():
            table.insert("", "end", iid=str(t.id),
                         values=(t.id, str(t.date), t.type.capitalize(), t.category, f"{t.amount:,.2f}"))
        session.close()

        # Delete Selected Transaction Function
        def delete_selected():
            selected = table.selection()
            if not selected:
                messagebox.showwarning("Delete", "Select a transaction first.")
                return
            if not messagebox.askyesno("Delete", "Delete the selected transaction?"):
                return
            session = Session()
            for iid in selected:
                entry = session.query(Transaction).filter_by(id=int(iid)).first()
                if entry:
                    session.delete(entry)
            session.commit()
            session.close()
            show_transactions_page()

        tk.Button(content, text="Delete Selected", font=("Montserrat", 10, "bold"),
                  fg="white", bg="#B91C1C", activebackground="#991B1B",
                  activeforeground="white", relief="flat",
                  command=delete_selected).pack(anchor="e", padx=30, pady=15, ipadx=10, ipady=4)

    # Budget Management Page
    def show_budget_page():
        clear_content()
        now = datetime.now()
        budgets = get_budgets()

        expense_opts = category_options("expense")

        # This month's spending per category
        session = Session()
        spent_by_cat = {}
        for t in user_transactions(session).filter_by(type="expense").all():
            if t.date.month == now.month and t.date.year == now.year:
                spent_by_cat[t.category] = spent_by_cat.get(t.category, 0) + t.amount
        session.close()

        total_budget = sum(budgets.values())
        total_spent = sum(spent_by_cat.get(c, 0) for c in budgets)
        remaining = total_budget - total_spent
        daily_avg = total_spent / now.day

        tk.Label(content, text="Budget Management", font=("Montserrat", 20, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(30, 0))
        tk.Label(content, text=f"Plan your budget and track your spending. ({now.strftime('%B %Y')})",
                 font=("Montserrat", 11), fg="#666666", bg="#F4F7FB").pack(anchor="w", padx=30)

        # Stat cards
        def budget_card(parent, title, value, color):
            card = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
            tk.Label(card, text=title, font=("Montserrat", 10), fg="#666666",
                     bg="#FFFFFF").pack(anchor="w", padx=20, pady=(12, 0))
            tk.Label(card, text=value, font=("Montserrat", 16, "bold"), fg=color,
                     bg="#FFFFFF").pack(anchor="w", padx=20, pady=(0, 12))
            return card

        cards = tk.Frame(content, bg="#F4F7FB")
        cards.pack(fill="x", padx=30, pady=15)
        card_data = [
            ("Total Budget", f"₱ {total_budget:,.2f}", "#000080"),
            ("Total Spent", f"₱ {total_spent:,.2f}", "#000080"),
            ("Remaining", f"₱ {remaining:,.2f}", "#16A34A" if remaining >= 0 else "#DC2626"),
            ("Daily Average", f"₱ {daily_avg:,.2f}", "#000080"),
        ]
        for i, (title, value, color) in enumerate(card_data):
            cards.columnconfigure(i, weight=1, uniform="bcard")
            budget_card(cards, title, value, color).grid(row=0, column=i, sticky="ew",
                                                         padx=(0 if i == 0 else 10, 0))

        # Main row: budget categories (left) and set budget form (right)
        main = tk.Frame(content, bg="#F4F7FB")
        main.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        main.columnconfigure(0, weight=3, uniform="bmain")
        main.columnconfigure(1, weight=2, uniform="bmain")

        # Budget categories with progress bars
        cats = tk.Frame(main, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
        cats.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(cats, text="Budget Categories", font=("Montserrat", 12, "bold"),
                 fg="#000080", bg="#FFFFFF").pack(anchor="w", padx=20, pady=(15, 5))

        def draw_bar(event, bar, pct, color):
            bar.delete("fill")
            bar.create_rectangle(0, 0, event.width * min(pct, 100) / 100, 8,
                                 fill=color, width=0, tags="fill")

        if not budgets:
            tk.Label(cats, text="No budgets set yet. Set one on the right.",
                     font=("Montserrat", 10), fg="#666666", bg="#FFFFFF").pack(anchor="w", padx=20, pady=10)

        for cat, limit in budgets.items():
            spent = spent_by_cat.get(cat, 0)
            pct = spent / limit * 100 if limit else 0
            color = "#DC2626" if pct > 100 else "#F59E0B" if pct >= 80 else "#2F80ED"

            row = tk.Frame(cats, bg="#FFFFFF")
            row.pack(fill="x", padx=20, pady=6)
            top = tk.Frame(row, bg="#FFFFFF")
            top.pack(fill="x")
            tk.Label(top, text=cat, font=("Montserrat", 10, "bold"), fg="#000080",
                     bg="#FFFFFF").pack(side="left")
            tk.Label(top, text=f"{pct:.0f}%", font=("Montserrat", 10, "bold"), fg=color,
                     bg="#FFFFFF").pack(side="right")
            tk.Label(row, text=f"₱{spent:,.2f} / ₱{limit:,.2f}", font=("Montserrat", 9),
                     fg="#666666", bg="#FFFFFF").pack(anchor="w")
            bar = tk.Canvas(row, height=8, bg="#E6EBFA", highlightthickness=0)
            bar.pack(fill="x", pady=(4, 0))
            bar.bind("<Configure>", lambda e, b=bar, p=pct, c=color: draw_bar(e, b, p, c))

        tk.Label(cats, text="Blue: on track   Orange: 80% or more   Red: over budget",
                 font=("Montserrat", 8), fg="#888888", bg="#FFFFFF").pack(anchor="w", padx=20, pady=(10, 15))

        # Set budget form
        form = tk.Frame(main, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
        form.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(form, text="Set Budget", font=("Montserrat", 12, "bold"),
                 fg="#000080", bg="#FFFFFF").pack(anchor="w", padx=20, pady=(15, 5))

        tk.Label(form, text="Expense Category", font=("Montserrat", 9), fg="#666666",
                 bg="#FFFFFF").pack(anchor="w", padx=20)
        b_cat_cb = ttk.Combobox(form, values=expense_opts, state="readonly", font=("Montserrat", 10))
        b_cat_cb.current(0)
        b_cat_cb.pack(fill="x", padx=20, pady=(2, 10), ipady=4)

        tk.Label(form, text="Budget Limit (₱)", font=("Montserrat", 9), fg="#666666",
                 bg="#FFFFFF").pack(anchor="w", padx=20)
        b_limit_entry = tk.Entry(form, font=("Montserrat", 10), relief="solid", bd=1)
        b_limit_entry.pack(fill="x", padx=20, pady=(2, 15), ipady=6)

        def set_budget():
            try:
                val = float(b_limit_entry.get().replace(",", ""))
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid amount.")
                return
            if val <= 0 or val > 1000000:
                messagebox.showerror("Error", "Budget must be above 0 and not more than ₱1,000,000.")
                return
            session = Session()
            existing = session.query(Budget).filter_by(
                user_id=current_user_id, category=b_cat_cb.get()
            ).first()
            if existing:
                existing.limit_amount = val
            else:
                session.add(Budget(user_id=current_user_id, category=b_cat_cb.get(), limit_amount=val))
            session.commit()
            session.close()
            show_budget_page()

        def remove_budget():
            cat = b_cat_cb.get()
            if cat not in budgets:
                messagebox.showwarning("Remove Budget", f"No budget is set for {cat}.")
                return
            session = Session()
            session.query(Budget).filter_by(user_id=current_user_id, category=cat).delete()
            session.commit()
            session.close()
            show_budget_page()

        tk.Button(form, text="Save Budget", font=("Montserrat", 10, "bold"),
                  fg="white", bg="#000080", activebackground="#1A1AA0",
                  activeforeground="white", relief="flat",
                  command=set_budget).pack(fill="x", padx=20, pady=(0, 8), ipady=6)
        tk.Button(form, text="Remove Budget", font=("Montserrat", 10, "bold"),
                  fg="white", bg="#B91C1C", activebackground="#991B1B",
                  activeforeground="white", relief="flat",
                  command=remove_budget).pack(fill="x", padx=20, pady=(0, 20), ipady=6)

    # Categories Page
    def show_categories_page():
        clear_content()

        tk.Label(content, text="Categories", font=("Montserrat", 20, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(30, 5))
        tk.Label(content, text="Create and manage your own income and expense categories.",
                 font=("Montserrat", 10), fg="#666666", bg="#F4F7FB").pack(anchor="w", padx=30, pady=(0, 20))

        main = tk.Frame(content, bg="#F4F7FB")
        main.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # Add Category Form
        form = tk.Frame(main, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
        form.pack(fill="x", pady=(0, 20))

        tk.Label(form, text="Add New Category", font=("Montserrat", 12, "bold"),
                 fg="#000080", bg="#FFFFFF").pack(anchor="w", padx=20, pady=(15, 10))

        tk.Label(form, text="Category Name", font=("Montserrat", 9), fg="#666666",
                 bg="#FFFFFF").pack(anchor="w", padx=20)

        name_var = tk.StringVar()
        name_entry = tk.Entry(form, textvariable=name_var, font=("Montserrat", 10),
                              relief="solid", bd=1)
        name_entry.pack(fill="x", padx=20, pady=(5, 10), ipady=6)

        # Limit input to 20 characters
        def limit_name(*args):
            value = name_var.get()
            if len(value) > 20:
                name_var.set(value[:20])

        name_var.trace_add("write", limit_name)

        tk.Label(form, text="Type", font=("Montserrat", 9), fg="#666666",
                 bg="#FFFFFF").pack(anchor="w", padx=20)

        type_var = tk.StringVar(value="expense")
        type_frame = tk.Frame(form, bg="#FFFFFF")
        type_frame.pack(anchor="w", padx=20, pady=(5, 10))

        tk.Radiobutton(type_frame, text="Expense", variable=type_var, value="expense",
                       bg="#FFFFFF", fg="#000080", activebackground="#FFFFFF",
                       font=("Montserrat", 9)).pack(side="left", padx=(0, 15))
        tk.Radiobutton(type_frame, text="Income", variable=type_var, value="income",
                       bg="#FFFFFF", fg="#000080", activebackground="#FFFFFF",
                       font=("Montserrat", 9)).pack(side="left")

        def add_category():
            # Normalize spaces, then validate the whole input
            name = " ".join(name_var.get().split())

            if len(name) < 3 or len(name) > 20:
                messagebox.showerror("Invalid Category", "Category name must contain 3 to 20 characters.")
                return

            # Letters and numbers allowed, must start with a letter, single spaces between words
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*(?: [A-Za-z0-9]+)*", name):
                messagebox.showerror(
                    "Invalid Category",
                    "Use letters, numbers, and single spaces only. The name must start with a letter.",
                )
                return

            category_type = type_var.get()
            defaults = INCOME_DEFAULTS if category_type == "income" else EXPENSE_DEFAULTS

            # Case-insensitive duplicate check against built-in and custom categories
            taken = defaults + get_custom_categories(category_type)
            if any(item.casefold() == name.casefold() for item in taken):
                messagebox.showerror("Duplicate Category", "This category already exists for this type.")
                return

            session = Session()
            session.add(Category(name=name, type=category_type, user_id=current_user_id))
            session.commit()
            session.close()

            name_var.set("")
            refresh_categories()
            messagebox.showinfo("Success", f"{name} was added to your {category_type} categories.")

        tk.Button(form, text="Add Category", font=("Montserrat", 10, "bold"),
                  fg="white", bg="#000080", activebackground="#1A1AA0",
                  activeforeground="white", relief="flat",
                  command=add_category).pack(anchor="w", padx=20, pady=(0, 20), ipadx=12, ipady=5)

        # Category lists
        lists = tk.Frame(main, bg="#F4F7FB")
        lists.pack(fill="both", expand=True)
        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(1, weight=1)

        def remove_category(name, category_type):
            if not messagebox.askyesno("Remove Category", f"Remove '{name}' from your custom categories?"):
                return
            session = Session()
            session.query(Category).filter_by(
                user_id=current_user_id, type=category_type, name=name
            ).delete()
            if category_type == "expense":
                session.query(Budget).filter_by(user_id=current_user_id, category=name).delete()
            session.commit()
            session.close()
            refresh_categories()

        def refresh_categories():
            for widget in lists.winfo_children():
                widget.destroy()

            for column, category_type in enumerate(("income", "expense")):
                panel = tk.Frame(lists, bg="#FFFFFF", highlightbackground="#DDE3F0", highlightthickness=1)
                panel.grid(row=0, column=column, sticky="nsew",
                           padx=(0, 10) if column == 0 else (10, 0))

                tk.Label(panel, text=category_type.capitalize() + " Categories",
                         font=("Montserrat", 11, "bold"), fg="#000080",
                         bg="#FFFFFF").pack(anchor="w", padx=15, pady=(15, 10))

                defaults = INCOME_DEFAULTS if category_type == "income" else EXPENSE_DEFAULTS
                for name in defaults:
                    tk.Label(panel, text=f"{name}  •  Built-in", font=("Montserrat", 9),
                             fg="#666666", bg="#FFFFFF").pack(anchor="w", padx=15, pady=3)

                custom = get_custom_categories(category_type)
                for name in custom:
                    row = tk.Frame(panel, bg="#FFFFFF")
                    row.pack(fill="x", padx=15, pady=3)
                    tk.Label(row, text=name, font=("Montserrat", 9), fg="#000080",
                             bg="#FFFFFF").pack(side="left")
                    tk.Button(row, text="Remove", font=("Montserrat", 8), fg="#B91C1C",
                              bg="#FFFFFF", relief="flat",
                              command=lambda n=name, t=category_type: remove_category(n, t)
                              ).pack(side="right")

                if not custom:
                    tk.Label(panel, text="No custom categories yet.", font=("Montserrat", 9),
                             fg="#888888", bg="#FFFFFF").pack(anchor="w", padx=15, pady=8)

        refresh_categories()

    nav_items = [
        ("Dashboard", show_dashboard_page),
        ("Transactions", show_transactions_page),
        ("Budgets", show_budget_page),
        ("Categories", show_categories_page),
    ]

    for text, command in nav_items:
        tk.Button(sidebar, text=text, font=("Montserrat", 11), fg="#000080", bg="#FFFFFF",
                  activebackground="#E6EBFA", activeforeground="#000080", relief="flat",
                  anchor="w", padx=20, command=command).pack(fill="x", pady=2, ipady=8)

    def log_out():
        global current_user_id
        if not messagebox.askyesno("Log Out", "Log out of MoneyMate?"):
            return
        current_user_id = None
        dashboard.destroy()
        root.deiconify()
        show_login()

    tk.Button(sidebar, text="Log Out", font=("Montserrat", 11), fg="#B91C1C", bg="#FFFFFF",
              activebackground="#FDECEC", activeforeground="#B91C1C", relief="flat",
              anchor="w", padx=20, command=log_out).pack(side="bottom", fill="x", pady=(0, 20), ipady=8)

    show_dashboard_page()


show_login()

root.mainloop()