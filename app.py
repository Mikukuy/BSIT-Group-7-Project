import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from models import Session, User, hash_password
from tkinter import messagebox, ttk
from models import Session, User, Transaction, hash_password

root = tk.Tk()
root.title("MoneyMate - Login")
root.geometry("900x500")
root.configure(bg="#FFFFFF")

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
    email = username_entry.get().strip().lower()
    password = password_entry.get()

    session = Session()
    user = session.query(User).filter_by(email=email).first()
    full_name = user.full_name if user else None
    valid = user is not None and user.password_hash == hash_password(password)
    session.close()

    if valid:
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
        transactions = session.query(Transaction).order_by(Transaction.id.desc()).all()
        rows = [(t.id, str(t.date), t.type, t.category, t.amount) for t in transactions]
        session.close()

        total_income = sum(r[4] for r in rows if r[2] == "income")
        total_expense = sum(r[4] for r in rows if r[2] == "expense")
        balance = total_income - total_expense

    # Top Bar - MIGHT ADD MORE SOON
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

        income_types = ["Allowance", "Salary/Wages", "Freelance/Side Job", "Scholarship/Grant", "Gift", "Other"]
        expense_types = ["Food", "Transportation", "Bills", "School Supplies", "Shopping", "Other"]

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
                session = Session()
                session.add(Transaction(type=tx_type, category=category.get(), amount=value))
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
        for t in session.query(Transaction).order_by(Transaction.id.desc()).all():
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
# Categories Page - Placeholder for Future Implementation
    def show_categories_page():
        clear_content()
        tk.Label(content, text="Categories", font=("Montserrat", 20, "bold"),
                 fg="#000080", bg="#F4F7FB").pack(anchor="w", padx=30, pady=30)

    nav_items = [
        ("Dashboard", show_dashboard_page),
        ("Transactions", show_transactions_page),
        ("Categories", show_categories_page),
    ]

    for text, command in nav_items:
        tk.Button(sidebar, text=text, font=("Montserrat", 11), fg="#000080", bg="#FFFFFF",
                  activebackground="#E6EBFA", activeforeground="#000080", relief="flat",
                  anchor="w", padx=20, command=command).pack(fill="x", pady=2, ipady=8)

    show_dashboard_page()
    
show_login()

root.mainloop()