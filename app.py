import streamlit as st

st.set_page_config(page_title="MoneyMate", page_icon="moneymate.jpg", layout="wide")

# Custom CSS for styling :)
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

# title
with st.container(border=True):

    left, center, right = st.columns([1, 2, 1])

with center:
    st.image("moneymate_horizontal.jpg", width=1200, )

    st.markdown(
        "<p style='color: #000080; text-align: center; "
        "font-family: Montserrat, sans-serif; font-size: 30px; "
        "margin: 0 0 50px 0;'>"
        "Track your income, expenses, and budget all in one place."
        "</p>",
        unsafe_allow_html=True
)

st.markdown("<hr style='border: 2px solid #000080;'>", unsafe_allow_html=True)

# add income section
st.markdown(
    "<h3 style='color: #000080; text-align: left; "
    "font-family: Montserrat, sans-serif; font-size: 28px;'>"
    "Enter your income amount (₱):</h3>",
    unsafe_allow_html=True
)

# income input
income = st.number_input(
    "Enter your income amount (₱):",
    min_value=0.0,
    step=1.0
)

if st.button("Add Income"):
    st.success(f"Income added: ₱{income:,.2f}")