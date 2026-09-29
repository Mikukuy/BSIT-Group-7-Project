import streamlit as st
import pandas as pd
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
    [data-testid="stMetricValue"] {
    color: #000080 !important;
    }
[data-testid="stMetricLabel"] {
    color: #000080 !important;
    }
[data-testid="stSidebar"] {
    color: #000080 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# MoneyMate Sidebar Template
with st.sidebar:
    st.markdown(
        "<h2 style='color': white; font-family: Montserrat, sans-serif; text-align: center;'>MoneyMate</h2>",
        unsafe_allow_html=True
    )
    page = st.radio(
        "Navigation",
        ["Dashboard", "Transactions", "Categories", "Reports", "Settings"],
        label_visibility="collapsed"
    )
# MoneyMate Logo and Description
with st.container(border=True):
    left, center, right = st.columns([1, 2, 1])

    with center:
        st.image("moneymate_horizontal.jpg", width=1200)

        st.markdown(
            "<p style='color: #000080; text-align: center; "
            "font-family: Montserrat, sans-serif; font-size: 28px; "
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

income_col, expense_col = st.columns(2)

# Income Section
with income_col:
    with st.container(border=True):
        st.markdown(
            "<h3 style='color: #000080; font-family: Montserrat, sans-serif; font-size: 28px; text-decoration: underline;'>Add Income</h3>",
            unsafe_allow_html=True
        )

        income_type = st.selectbox(
            "Select income type:",
            ["Allowance", "Salary/Wages", "Freelance/Side Job", "Scholarship/Grant", "Gift", "Other"]
        )

        income = st.number_input(
            "Enter your income amount (₱):",
            min_value=0.0,
            max_value=1000000.0,
            step=100.0
        )

        if st.button("Add Income"):
            new_entry = Transaction(type="income", category=income_type, amount=income)
            session.add(new_entry)
            session.commit()
            st.success(f"Added ₱{income:.2f} from {income_type}!")

# Expense Section
with expense_col:
    with st.container(border=True):
        st.markdown(
            "<h3 style='color: #000080; font-family: Montserrat, sans-serif; font-size: 28px; text-decoration: underline;'>Add Expense</h3>",
            unsafe_allow_html=True
        )

        expense_type = st.selectbox(
            "Select expense category:",
            ["Food", "Transportation", "Bills", "School Supplies", "Shopping", "Other"]
        )

        expense = st.number_input(
            "Enter your expense amount (₱):",
            min_value=0.0,
            max_value=1000000.0,
            step=100.0,
            key="expense_input"
        )

        if st.button("Add Expense"):
            new_entry = Transaction(type="expense", category=expense_type, amount=expense)
            session.add(new_entry)
            session.commit()
            st.success(f"Added ₱{expense:.2f} to {expense_type}!")

st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)

# Transaction History
st.markdown("<h3 style='color: #000080; font-family: Montserrat, sans-serif; font-size: 28px; text-decoration: underline;'>Transaction History</h3>", unsafe_allow_html=True)

transactions = session.query(Transaction).all()

data = []
for t in transactions:
    data.append({
        "ID": t.id,
        "Date": t.date,
        "Type": t.type.capitalize(),
        "Category": t.category,
        "Amount (₱)": f"{t.amount:,.2f}"
    })

df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True, hide_index=True)

# Delete Option
if transactions:
    delete_id = st.selectbox(
        "Select a transaction ID to delete:",
        [t.id for t in transactions]
    )
    if st.button("Delete Selected Transaction"):
        entry_to_delete = session.query(Transaction).filter_by(id=delete_id).first()
        session.delete(entry_to_delete)
        session.commit()
        st.rerun()

st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)

# Transaction Summary
st.markdown("<h3 style='color: #000080; font-family: Montserrat, sans-serif; font-size: 28px;'>Transaction Summary</h3>", unsafe_allow_html=True)

transactions = session.query(Transaction).all()
total_income = sum(t.amount for t in transactions if t.type == "income")
total_expense = sum(t.amount for t in transactions if t.type == "expense")
balance = total_income - total_expense

sum_col1, sum_col2, sum_col3 = st.columns(3)
with sum_col1:
    st.metric("Total Income", f"₱{total_income:,.2f}")
with sum_col2:
    st.metric("Total Expenses", f"₱{total_expense:,.2f}")
with sum_col3:
    st.metric("Remaining Balance", f"₱{balance:,.2f}")
   
st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)

# Expense Summary Chart
st.markdown("<h3 style='color: #000080; font-family: Montserrat, sans-serif; font-size: 28px;'>Expense Summary Chart</h3>", unsafe_allow_html=True)

expense_data = {}
for t in transactions:
    if t.type == "expense":
        expense_data[t.category] = expense_data.get(t.category, 0) + t.amount

if expense_data:
    chart_df = pd.DataFrame(list(expense_data.items()), columns=["Category", "Amount"])
    chart_df = chart_df.set_index("Category")
    st.bar_chart(chart_df)
else:
    st.write("No expense data available to display the chart.")