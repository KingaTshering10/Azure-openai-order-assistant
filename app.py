"""Streamlit UI for the local mock order assistant."""
import streamlit as st
from assistant_core import Settings, answer_order_query

st.set_page_config(page_title="Azure Order Assistant", page_icon="📦")
st.title("Azure Order Assistant")
st.caption("Ask about mock order 123456789. The sample dates are historical training data.")
try:
    settings = Settings.load()
except ValueError as error:
    st.info(str(error))
    st.stop()

st.sidebar.caption("Start the local order API in a second terminal before asking for order details.")
if st.sidebar.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()
if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tools"):
            with st.expander("Tool activity"):
                st.json(message["tools"])

if query := st.chat_input("When is demo order 123456789 expected to arrive?"):
    if not query.strip():
        st.stop()
    with st.chat_message("user"):
        st.markdown(query)
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    try:
        with st.spinner("Checking the question..."):
            result = answer_order_query(query, conversation=history, settings=settings)
    except Exception:
        st.error("The request could not be completed. Check Azure settings, deployment access, quota, and connectivity.")
    else:
        st.session_state.messages.extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": result.answer, "tools": result.tool_events},
        ])
        with st.chat_message("assistant"):
            st.markdown(result.answer)
            if result.tool_events:
                with st.expander("Tool activity"):
                    st.json(result.tool_events)
