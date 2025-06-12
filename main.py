"""
Main Entry Point for Chat Application

This module serves as the entry point for the chat application framework.
It reads the configuration from .config.yml to determine which chatbot
interface to load and run.

Supported Chatbot Types:
    - basic: Simple chat interface without memory
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

import importlib.util

import streamlit as st
import yaml
from box import Box
from pyprojroot import here


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
    Dynamically load the appropriate chatbot module based on type.
    
    Args:
        chatbot_type (str): Type of chatbot to load (basic, agentic, semantic, langgraph)
        
    Returns:
        module: The loaded chatbot module
        
    Raises:
        ImportError: If the chatbot module cannot be imported
        FileNotFoundError: If the chatbot file doesn't exist
    """
    # Map chatbot types to their corresponding files
    chatbot_files = {
        'basic': 'basic_ui_chat.py',
        'basic_memory': 'basic_ui_chat_with_memory.py',
        'agentic': 'agentic_ui_chat.py', 
        'semantic': 'semantic_ui_chat.py',
        'langgraph': 'langgraph_ui_chat.py'
    }
    
    if chatbot_type not in chatbot_files:
        st.error(f"❌ Unknown chatbot type: {chatbot_type}")
        st.error(f"Available types: {', '.join(chatbot_files.keys())}")
        st.stop()
    
    # Check if it's a plugin or root level file
    module_path = here(f'chatbots/{chatbot_files[chatbot_type]}')
    
    try:
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(f"{chatbot_type}_chatbot", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        st.error(f"❌ Error loading chatbot module '{chatbot_type}': {e}")
        st.stop()


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
        # pages = {
        #     "Basic Chat with no LTM": ("chatbots/basic_ui_chat.py", "\U0001F4AC"),
        #     "Basic Chat with LTM": ("chatbots/basic_ui_chat_with_memory.py", "\U0001F4AC"),
        #     "Agentic Chat with LTM": ("chatbots/agentic_ui_chat.py", "\U0001F4AC"),
        #     "Semantic Chat with LTM": ("chatbots/semantic_ui_chat.py", "\U0001F4AC"),
        #     "LangGraph Chat with LTM": ("chatbots/langgraph_ui_chat.py", "\U0001F4AC")
        # }
        #
        # nav_items = [
        #     st.Page(path, title=name, icon=icon, default=(name == "Chat"))
        #     for name, (path, icon) in pages.items()
        # ]
        # ui = st.navigation({"Chat": nav_items}, expanded=False)
        # ui.run()
            
    except Exception as e:
        st.error(f"❌ Application error: {e}")
        st.error("Please check your configuration and try again")


if __name__ == "__main__":
    main()