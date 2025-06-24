"""
Authentication Wrapper for Streamlit Applications

This module provides a simple wrapper for adding Google OIDC authentication
to any Streamlit chatbot application.
"""

import streamlit as st
from utils.auth_manager import AuthManager
from utils.user_manager import UserManager
from utils.sqldb_manager import SQLManager
from box import Box
import yaml
from pyprojroot import here

with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))


def require_auth(func):
    """
    Decorator to require authentication before running the main function.
    
    Args:
        func: The main function to wrap
        
    Returns:
        Wrapped function that checks authentication first
    """
    def wrapper(*args, **kwargs):
        # Initialize managers if not already done
        if 'sqldb_manager' not in st.session_state:
            st.session_state.sqldb_manager = SQLManager(f'{config.db.sql.dir}/{config.db.sql.file}')
        
        if 'user_manager' not in st.session_state:
            st.session_state.user_manager = UserManager(st.session_state.sqldb_manager)
        
        # Initialize auth manager with user manager if not already done
        if 'auth_manager' not in st.session_state:
            st.session_state.auth_manager = AuthManager(st.session_state.user_manager)
        
        auth_manager = st.session_state.auth_manager
        
        # Handle OAuth callback if present
        handle_oauth_callback(auth_manager)
        
        # Check if OAuth is enabled and user is not authenticated
        if config.oauth_config.enabled and not auth_manager.is_authenticated():
            auth_manager.render_login_page()
            return
        
        # If authenticated or OAuth disabled, run the original function
        return func(*args, **kwargs)
    
    return wrapper


def handle_oauth_callback(auth_manager):
    """Handle OAuth callback from URL parameters."""
    # Check if we have OAuth callback parameters
    query_params = st.query_params
    
    if 'code' in query_params and 'state' in query_params:
        # Construct the callback URL manually
        code = query_params['code']
        state = query_params['state']
        
        # Create a mock URL for the callback
        callback_url = f"?code={code}&state={state}"
        
        if auth_manager.handle_oauth_callback(callback_url):
            st.success("✅ Authentication successful!")
            # Clear the URL parameters
            st.query_params.clear()
            st.rerun()
        else:
            st.error("❌ Authentication failed!")
            st.query_params.clear()


def render_auth_sidebar():
    """Render authentication information in the sidebar."""
    if 'auth_manager' not in st.session_state:
        # Initialize managers if needed
        if 'sqldb_manager' not in st.session_state:
            st.session_state.sqldb_manager = SQLManager(f'{config.db.sql.dir}/{config.db.sql.file}')
        
        if 'user_manager' not in st.session_state:
            st.session_state.user_manager = UserManager(st.session_state.sqldb_manager)
        
        st.session_state.auth_manager = AuthManager(st.session_state.user_manager)
    
    auth_manager = st.session_state.auth_manager
    
    if config.oauth_config.enabled:
        auth_manager.render_user_info()


def init_auth_session_state():
    """Initialize authentication-related session state variables."""
    # Initialize managers
    if 'sqldb_manager' not in st.session_state:
        st.session_state.sqldb_manager = SQLManager(f'{config.db.sql.dir}/{config.db.sql.file}')
    
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager(st.session_state.sqldb_manager)
    
    if 'auth_manager' not in st.session_state:
        st.session_state.auth_manager = AuthManager(st.session_state.user_manager) 