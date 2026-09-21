import streamlit as st
from models import Session, Transaction

session = Session()

st.set_page_config(page_title="MoneyMate", page_icon="moneymate.jpg", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFFFFF;
    }
    .stButton>button {
        background-color: #000080;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Moneymate Logo and Description
with st.container(border=True):
    left, center, right = st.columns([1, 2, 1])

    with center:
        st.image("moneymate_horizontal.jpg", width=1200)

        st.markdown(
            "<p style='color: #000080; text-align: center; "
            "font-family: Montserrat, sans-serif; font-size: 30px; "
            "margin: 0 0 50px 0;'>"
            "Track your income, expenses, and budget all in one place."
            "</p>",
            unsafe_allow_html=True
        )

st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)

# Income Input Textbox
st.markdown(
    "<h3 style='color: #000080; text-align: left; "
    "font-family: Montserrat, sans-serif; font-size: 28px;'>"
    "Enter your income amount (₱):</h3>",
    unsafe_allow_html=True
)

income = st.number_input(
    "Enter your income amount (₱):",
    min_value=0.0,
    step=1.0
)

st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)

# Add Income Button
if st.button("Add Income"):
    new_entry = Transaction(type="income", category="Income", amount=income)
    session.add(new_entry)
    session.commit()
    st.success(f"Added ₱{income:.2f} to your income!")

# Transaction History
st.markdown("<h3 style='color: #000080; font-family: Montserrat, sans-serif; font-size: 28px;'>Transaction History</h3>", unsafe_allow_html=True)
transactions = session.query(Transaction).all()

for t in transactions:
    st.markdown(f"<p style='color: #000080;'>{t.date} — {t.category} — ₱{t.amount:.2f}</p>", unsafe_allow_html=True)

st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)