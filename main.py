"""
Main Entry Point for Chat Application

This module serves as the entry point for the chat application framework.
It reads the configuration from .config.yml to determine which chatbot
interface to load and run.

Supported Chatbot Types:
    - basic: Simple chat interface without memory
    - basic_memory: Chat interface with long-term memory
    - agentic: Advanced chat with memory and agent capabilities  
    - semantic: Chat with semantic search and retrieval
    - langgraph: Chat using LangGraph framework

Configuration:
    Set the chatbot type in .config.yml under chatbot.type

Usage:
    streamlit run main.py

The application will automatically load the appropriate chatbot interface
based on the configuration setting.
"""

import importlib
import streamlit as st
import yaml
from box import Box
from pyprojroot import here

# Import authentication utilities
from utils.auth_wrapper import require_auth, init_auth_session_state


def load_config() -> Box:
    """
    Load configuration from the .config.yml file.
    
    Returns:
        Box: Configuration object with easy dot notation access
        
    Raises:
        FileNotFoundError: If .config.yml is not found
        yaml.YAMLError: If the YAML file is malformed
    """
    config_path = here('.config.yml')
    try:
        with open(config_path, 'r') as file:
            config = Box(yaml.safe_load(file))
        return config
    except FileNotFoundError:
        st.error("❌ Configuration file '.config.yml' not found in project root")
        st.stop()
    except yaml.YAMLError as e:
        st.error(f"❌ Error parsing configuration file: {e}")
        st.stop()


def load_chatbot_module(chatbot_type: str):
    """
    Dynamically load a chatbot module based on the type.
    
    Args:
        chatbot_type (str): The type of chatbot to load
        
    Returns:
        module: The loaded chatbot module
        
    Raises:
        ImportError: If the chatbot module cannot be loaded
    """
    # Map chatbot types to their module paths
    chatbot_modules = {
        "basic": "chatbots.basic_ui_chat",
        "basic_memory": "chatbots.basic_ui_chat_with_memory",
        "agentic": "chatbots.agentic_ui_chat",
        "semantic": "chatbots.semantic_ui_chat",
        "langgraph": "chatbots.langgraph_ui_chat",
        "letta": "chatbots.letta_ui_chat"
    }
    
    if chatbot_type not in chatbot_modules:
        st.error(f"❌ Unsupported chatbot type: {chatbot_type}")
        st.error(f"Supported types: {', '.join(chatbot_modules.keys())}")
        st.stop()
    
    try:
        # Import the module dynamically
        module_name = chatbot_modules[chatbot_type]
        module = importlib.import_module(module_name)
        return module
    except ImportError as e:
        st.error(f"❌ Failed to load chatbot module '{chatbot_type}': {e}")
        st.stop()


@require_auth
def main():
    """
    Main entry point that loads the appropriate chatbot based on configuration.
    """
    try:
        # Load configuration
        config = load_config()
        
        # Get the chatbot type from config
        chatbot_type = config.chatbot.type
        
        # Load and run the appropriate chatbot module
        chatbot_module = load_chatbot_module(chatbot_type)
        
        # Run the chatbot's main function
        if hasattr(chatbot_module, 'main'):
            chatbot_module.main()
        else:
            st.error(f"❌ Chatbot module '{chatbot_type}' does not have a main() function")
            st.stop()
            
    except Exception as e:
        st.error(f"❌ Application error: {e}")
        st.error("Please check your configuration and try again")


if __name__ == "__main__":
    # Initialize authentication session state
    init_auth_session_state()
    
    # Run the main application
    main()