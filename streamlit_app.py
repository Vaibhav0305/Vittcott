import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("VITTCOTT_BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Vittcott AI Assistant", layout="wide")
st.title("🤖 Vittcott AI Investing Assistant")

st.markdown("""
Welcome to **Vittcott**! Ask finance questions, get AI-powered explanations, and explore stock/mutual fund data.\
*This is an educational tool, not real financial advice.*
""")

# --- Sidebar: Portfolio ---
st.sidebar.header("Your Portfolio (optional)")


# --- Portfolio State Initialization ---
if "stocks" not in st.session_state:
    st.session_state.stocks = []
if "mutual_funds" not in st.session_state:
    st.session_state.mutual_funds = []
if "cash" not in st.session_state:
    st.session_state.cash = 0
if "stock_name" not in st.session_state:
    st.session_state.stock_name = ""
if "stock_qty" not in st.session_state:
    st.session_state.stock_qty = 1
if "mf_name" not in st.session_state:
    st.session_state.mf_name = ""
if "mf_amt" not in st.session_state:
    st.session_state.mf_amt = 1

def add_stock():
    name = st.session_state.stock_name.strip()
    qty = st.session_state.stock_qty
    if name:
        st.session_state.stocks.append({"name": name, "quantity": qty})
        st.session_state.stock_name = ""
        st.session_state.stock_qty = 1

def add_mf():
    name = st.session_state.mf_name.strip()
    amt = st.session_state.mf_amt
    if name:
        st.session_state.mutual_funds.append({"name": name, "amount": amt})
        st.session_state.mf_name = ""
        st.session_state.mf_amt = 1

st.sidebar.subheader("Stocks")
stock_name = st.sidebar.text_input("Stock name (e.g., TCS)", key="stock_name")
stock_qty = st.sidebar.number_input("Quantity", min_value=1, step=1, key="stock_qty")
st.sidebar.button("Add Stock", on_click=add_stock)

if st.session_state.stocks:
    for i, s in enumerate(st.session_state.stocks):
        col1, col2, col3 = st.sidebar.columns([2, 1, 1])
        col1.write(f"{s['name']} (x{s['quantity']})")
        if col2.button("Edit", key=f"edit_stock_{i}"):
            st.session_state["stock_name"] = s["name"]
            st.session_state["stock_qty"] = s["quantity"]
            st.session_state.stocks.pop(i)
            st.experimental_rerun()
        if col3.button("Remove", key=f"remove_stock_{i}"):
            st.session_state.stocks.pop(i)
            st.experimental_rerun()

st.sidebar.subheader("Mutual Funds")
mf_name = st.sidebar.text_input("Mutual Fund name (e.g., SBI Bluechip)", key="mf_name")
mf_amt = st.sidebar.number_input("Amount Invested", min_value=1, step=1, key="mf_amt")
st.sidebar.button("Add Mutual Fund", on_click=add_mf)

if st.session_state.mutual_funds:
    for i, m in enumerate(st.session_state.mutual_funds):
        col1, col2, col3 = st.sidebar.columns([2, 1, 1])
        col1.write(f"{m['name']} (₹{m['amount']})")
        if col2.button("Edit", key=f"edit_mf_{i}"):
            st.session_state["mf_name"] = m["name"]
            st.session_state["mf_amt"] = m["amount"]
            st.session_state.mutual_funds.pop(i)
            st.experimental_rerun()
        if col3.button("Remove", key=f"remove_mf_{i}"):
            st.session_state.mutual_funds.pop(i)
            st.experimental_rerun()

st.sidebar.subheader("Cash")
st.session_state.cash = st.sidebar.number_input("Cash (₹)", min_value=0, step=100, value=st.session_state.cash, key="cash_input")

# Build portfolio dict for backend
portfolio_dict = {
    "stocks": st.session_state.stocks,
    "mutual_funds": st.session_state.mutual_funds,
    "cash": st.session_state.cash
}

# --- Tabs ---
tab1, tab2 = st.tabs(["💬 AI Chat", "📈 Stock/Mutual Fund Lookup"])

# --- Tab 1: AI Chat ---
with tab1:
    st.subheader("Chat with Vittcott AI")
    import time
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    user_input = st.text_area("Ask a question about investing, SIPs, or your portfolio:", key="ai_input")
    if st.button("Send", key="ai_send") and user_input.strip():
        st.session_state.chat_history.append(("user", user_input))
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/api/ai/ask",
                    json={"query": user_input, "portfolio": portfolio_dict},
                    timeout=30
                )
                if resp.status_code == 200:
                    ai_text = resp.json().get("response_text", "(No response)")
                else:
                    ai_text = f"Error: {resp.text}"
            except Exception as e:
                ai_text = f"Error: {e}"
        # Streaming effect: display AI response letter by letter
        st.session_state.chat_history.append(("ai", ""))
        ai_index = len(st.session_state.chat_history) - 1
        placeholder = st.empty()
        streamed = ""
        for char in ai_text:
            streamed += char
            st.session_state.chat_history[ai_index] = ("ai", streamed)
            # Redraw chat
            with placeholder.container():
                for role, msg in st.session_state.chat_history:
                    if role == "user":
                        st.markdown(f"**You:** {msg}")
                    else:
                        st.markdown(f"**Vittcott AI:** {msg}")
            time.sleep(0.004)
        placeholder.empty()
    # Display chat (final, after streaming)
    for role, msg in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"**You:** {msg}")
        else:
            st.markdown(f"**Vittcott AI:** {msg}")
    if st.button("Clear chat", key="ai_clear"):
        st.session_state.chat_history = []

# --- Tab 2: Stock/Mutual Fund Lookup ---
with tab2:
    st.subheader("Stock/Mutual Fund Data")
    symbol = st.text_input("Enter stock or mutual fund symbol (e.g., TCS, INFY, SBIN)", key="symbol_input")
    if st.button("Get Quote", key="quote_btn") and symbol.strip():
        with st.spinner("Fetching data..."):
            try:
                resp = requests.get(f"{BACKEND_URL}/api/finance/quote", params={"symbol": symbol})
                if resp.status_code == 200:
                    data = resp.json()
                    st.write(f"**Symbol:** {data.get('symbol')}")
                    st.write(f"**Price:** {data.get('price')}")
                    st.write(f"**Change:** {data.get('change', 'N/A')}")
                    st.write(f"**Candles:**")
                    st.dataframe(data.get("candles", []))
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")
st.caption("Vittcott AI — Educational investing assistant. Backend: FastAPI, Frontend: Streamlit. © 2025")
