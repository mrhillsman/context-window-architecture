"""
Basic Streamlit Chat Application with Google Gemini API

This module provides a simple chat interface that integrates with Google's Gemini AI model
without persistent memory features. The application uses the google-generativeai library
to communicate with Gemini and provides a clean, user-friendly Streamlit interface.

Features:
    - Real-time chat with Google Gemini 2.0 Flash model
    - Session-based conversation (no persistence between app restarts)
    - API key configuration through UI or environment variables
    - Error handling with user-friendly messages
    - Chat statistics and connection status
    - Clear chat history functionality

Environment Setup:
    Option 1: Set environment variable
        export GEMINI_API_KEY="your-api-key-here"
    
    Option 2: Enter the API key through the sidebar interface

Usage:
    streamlit run basic_ui_chat.py

API Key Setup:
    1. Visit https://aistudio.google.com/app/apikey
    2. Create a new API key
    3. Set it via environment variable or sidebar input
"""

import os
from datetime import datetime
from box import Box
import yaml
from pyprojroot import here

from google import genai
import streamlit as st

from ollama import Client
from utils.ollama_manager import OllamaManager


with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))

def init_session_state() -> None:
    """
    Initialize Streamlit session state variables for the chat application.
    
    This function sets up the necessary session state variables if they don't
    already exist, ensuring the application starts with a clean state.
    
    Session State Variables:
        - messages (list): Chat message history
        - gemini_api_key (str): User's Gemini API key
        - model (GenerativeModel): Initialized Gemini model instance
        - chat (ChatSession): Active chat session with the model
    
    Returns:
        None
    """
    # Initialize empty message history for storing chat conversations
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Try to get API key from environment, fallback to empty string
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    # Initialize chat session holder
    if 'chat' not in st.session_state:
        st.session_state.chat = None

    # Set the session ID using UUID
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

    # Initialize ollama manager
    if 'ollama' not in st.session_state:
        st.session_state.ollama = None


def initialize_gemini(api_key: str) -> bool:
    """
    Initialize the Gemini model with the provided API key.

    This function configures the Google Generative AI library with the user's
    API key and creates a new model instance and chat session.

    Args:
        api_key (str): The Google Gemini API key for authentication

    Returns:
        bool: True if the initialization is successful, False otherwise

    Raises:
        Exception: Catches and handles any initialization errors gracefully

    Side Effects:
        - Updates st.session_state.model with initialized model
        - Updates st.session_state.chat with new chat session
        - Displays error messages in Streamlit interface on failure
    """
    if not api_key:
        return False

    try:
        # Configure the Google Generative AI library with the provided API key
        st.session_state.chat = genai.Client(api_key=api_key)

        return True

    except Exception as e:
        # Display user-friendly error message in the Streamlit interface
        st.error(f"Failed to initialize Gemini: {str(e)}")
        return False


def get_gemini_response(prompt: str) -> str:
    """
    Send a message to the Gemini model and retrieve the response.
    
    This function handles the core interaction with the Gemini API,
    including error handling for common failure scenarios.
    
    Args:
        prompt (str): The user's message/question to send to Gemini
        
    Returns:
        str: The model's response text or an error message
        
    Error Handling:
        - API_KEY_INVALID: Invalid or expired API key
        - RATE_LIMIT_EXCEEDED: Too many requests in a short time
        - SAFETY: Content blocked by safety filters
        - General exceptions: Network issues, timeouts, etc.
    """
    # Ensure chat session is properly initialized
    if not st.session_state.chat:
        return "❌ Chat session not initialized. Please check your API key."

    try:
        # Send the user's message to Gemini and get the response
        # The chat session maintains conversation context automatically
        response = st.session_state.chat.models.generate_content(
            model=config.llm_config.chat_model,
            contents=prompt
        )
        return response.text

    except Exception as e:
        # Convert technical errors to user-friendly messages
        error_msg = f"❌ Error: {str(e)}"

        # Handle specific common error cases with helpful guidance
        if "API_KEY_INVALID" in str(e):
            error_msg = "❌ Invalid API key. Please check your API key in the sidebar."
        elif "RATE_LIMIT_EXCEEDED" in str(e):
            error_msg = "⏱️ Rate limit exceeded. Please wait a moment and try again."
        elif "SAFETY" in str(e):
            error_msg = "⚠️ Response blocked due to safety settings. Please try rephrasing your message."

        return error_msg


def initialize_ollama():
    try:
        # Create a new instance of the ollama wrapper class
        st.session_state.ollama = OllamaManager(
            host=config.ollama.host,
            model=config.ollama.chat_model,
            options=dict(config.ollama.options)
        )

        return True

    except Exception as e:
        # Display user-friendly error message in the Streamlit interface
        st.error(f"Failed to initialize Ollama: {str(e)}")
        return False


def get_ollama_response(prompt: str) -> str:
    try:
        messages = []

        for message in st.session_state.messages:
            messages.append({"role": message["role"], "content": message["content"]})

        messages.append({"role": "user", "content": prompt})

        response = st.session_state.ollama.chat(messages)

        return response.message.content
    except Exception as e:
        # Return the error message
        return f"❌ Error: {str(e)}"


def main() -> None:
    """
    Main application function that sets up and runs the Streamlit chat interface.
    
    This function orchestrates the entire application, including
    - Page configuration and layout setup
    - Sidebar with settings and controls
    - Main chat interface with message display
    - Chat input handling and response generation
    
    The function handles the complete user interaction flow from API key
    configuration to sending messages and displaying responses.

    Returns:
        None
    """
    # Configure the Streamlit page with title, icon, and layout
    st.set_page_config(
        page_title="Basic Chat no LTM",
        page_icon="💬",
        layout="wide"
    )

    # Initialize all session state variables
    init_session_state()

    # === SIDEBAR CONFIGURATION ===
    with st.sidebar:
        st.title("⚙️ Settings")
        st.info("Chatbot: Basic")

        # API Key Configuration Section
        st.subheader("🔑 API Configuration")
        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Get your API key from https://aistudio.google.com/app/apikey"
        )

        # Handle API key changes and reinitialize if necessary
        if api_key != st.session_state.gemini_api_key:
            st.session_state.gemini_api_key = api_key
            if api_key:
                if initialize_gemini(api_key):
                    st.success("✅ Gemini initialized successfully")
                else:
                    st.error("❌ Failed to initialize Gemini")

        # Initialize on the first load if an API key exists but the model isn't initialized
        if api_key and not config.ollama.enabled:
            initialize_gemini(api_key)
        else:
            initialize_ollama()

        # Display API key status and guidance
        if not api_key:
            st.warning("⚠️ Please enter your Gemini API key")
            st.info("💡 You can also set GEMINI_API_KEY environment variable")
        elif st.session_state.chat:
            st.success("✅ Connected to Gemini")

        st.divider()

        # Chat Controls Section
        st.subheader("💬 Chat Controls")

        # Clear chat history button with confirmation
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            # Reinitialize the chat session to start fresh
            if st.session_state.chat:
                st.session_state.chat = None
            st.rerun()

        # Display chat statistics
        st.divider()
        st.subheader("📊 Chat Statistics")
        st.metric("Total Messages", len(st.session_state.messages))

        # Model and session information
        st.divider()
        st.caption(f"Model: {config.llm_config.chat_model}")
        st.caption(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Connection status indicator
        if st.session_state.chat:
            st.caption("🟢 Connected")
        else:
            st.caption("🔴 Disconnected")

    # === MAIN CHAT INTERFACE ===
    st.title("💬 Basic Chat no LTM")
    st.markdown("A simple chat interface powered by Google Gemini")

    # Display all previous chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input handling
    # The walrus operator := captures the input while checking if it exists
    if prompt := st.chat_input("Type your message here..." if api_key or config.ollama.enabled else "Please set your API key first"):
        # Validate prerequisites before processing the message
        if not st.session_state.gemini_api_key and not config.ollama.enabled:
            st.error("❌ Please configure your Gemini API key in the sidebar")
        elif not st.session_state.chat and not config.ollama.enabled:
            st.error("❌ Gemini not initialized. Please check your API key.")
        else:
            # Add a user message to the chat history
            # st.session_state.messages.append({"role": "user", "content": prompt})

            # Display a user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    if config.ollama.enabled:
                        response = get_ollama_response(prompt)
                    else:
                        # Get a response from the Gemini model
                        response = get_gemini_response(prompt)
                    st.markdown(response)

            # Add prompt and response to chat history for context
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": response})
            print(st.session_state.messages)


# Entry point for the application
if __name__ == "__main__":
    main()