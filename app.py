import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from models import Session, User, hash_password

root = tk.Tk()
root.title("MoneyMate - Login")
root.geometry("900x500")
root.configure(bg="#FFFFFF")

# Login and Signup Functions
def check_signup():
    name = signup_name_entry.get().strip()
    email = signup_email_entry.get().strip().lower()
    password = signup_password_entry.get()

    if name in ("", "Full Name") or email in ("", "Email address") or password in ("", "Password"):
        messagebox.showerror("Error", "Please fill out all fields.")
        return

    if "@" not in email or "." not in email:
        messagebox.showerror("Error", "Please enter a valid email address.")
        return

    if len(password) < 6:
        messagebox.showerror("Error", "Password must be at least 6 characters.")
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
        messagebox.showinfo("Success", f"Welcome, {full_name}!")
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

    signup_name_entry = make_input_field(right_frame, "👤", "Full Name")
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

show_login()

root.mainloop()