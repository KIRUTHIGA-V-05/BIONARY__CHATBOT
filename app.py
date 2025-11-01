import streamlit as st
from query_pipeline import handle_user_query

st.set_page_config(page_title="Club Knowledge Search Agent", layout="centered")

st.title("🎓 Club Knowledge Search Agent")
st.caption("Ask anything about past club events — powered by Gemini + Neon RAG backend")

# Text input
user_input = st.text_input("Your question:")

if user_input:
    with st.spinner("Thinking..."):
        try:
            answer = handle_user_query(user_input)
            st.markdown(f"**Answer:** {answer}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")