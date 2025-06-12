"""
Letta Chat Interface

This module provides a chat interface enhanced with letta.

Features:
    - ...

Usage:
    This module is loaded automatically by main.py when chatbot.type is set to "letta"
"""

import streamlit as st
from datetime import datetime


def main() -> None:
    """
    Main function for the Letta Chat interface.
    """
    st.set_page_config(
        page_title="Letta Chat",
        page_icon="",
        layout="wide"
    )

    with st.sidebar:
        st.title("⚙️ Settings")
        st.info(" Chatbot: Letta")

    st.title(" Letta Chat Interface")
    st.markdown("Chat with letta capabilities")

    st.info(" Letta chatbot interface coming soon!")
    st.markdown("""
    This interface will include:
    - ...
    """)


if __name__ == "__main__":
    main()