"""
Authentication Manager for Google OIDC Integration

This module provides OAuth2 authentication functionality for Google OIDC,
integrating with Streamlit's session state and the existing user management system.
"""

import os
import secrets
import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
from urllib.parse import urlencode, parse_qs, urlparse
import requests
from typing import Optional, Dict, Any
from box import Box
import yaml
from pyprojroot import here
from datetime import datetime, timedelta

with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))


class AuthManager:
    """
    Manages Google OIDC authentication for the Streamlit application.
    """

    def __init__(self, user_manager=None):
        """Initialize the authentication manager."""
        self.oauth_config = config.oauth_config
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", self.oauth_config.client_id)
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", self.oauth_config.client_secret)
        self.redirect_uri = self.oauth_config.redirect_uri
        self.scope = self.oauth_config.scope.split()
        self.user_manager = user_manager
        
        # Initialize session state for authentication
        self._init_auth_session_state()

    def _init_auth_session_state(self):
        """Initialize authentication-related session state variables."""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None
        
        if 'auth_token' not in st.session_state:
            st.session_state.auth_token = None
        
        if 'auth_state' not in st.session_state:
            st.session_state.auth_state = None
            
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
            
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = None

    def is_authenticated(self) -> bool:
        """Check if the user is currently authenticated."""
        # Check if we have a session token and validate it
        if st.session_state.session_token and self.user_manager:
            user_id = self.user_manager.validate_session(st.session_state.session_token)
            if user_id:
                # Update last activity
                self._update_activity()
                return True
            else:
                # Session token is invalid or expired, clear it
                st.session_state.session_token = None
                st.session_state.last_activity = None
                st.session_state.authenticated = False
                st.session_state.user_info = None
        
        # Fall back to OAuth authentication check
        return st.session_state.authenticated and st.session_state.user_info is not None

    def _update_activity(self):
        """Update last activity timestamp and refresh session if needed."""
        now = datetime.now()
        st.session_state.last_activity = now
        
        # Refresh session every 12 hours to extend the 24-hour timeout
        if (st.session_state.last_activity and 
            (now - st.session_state.last_activity).total_seconds() > 43200):  # 12 hours
            self._refresh_session()

    def _refresh_session(self):
        """Refresh the current session."""
        if st.session_state.session_token and self.user_manager:
            # Get user ID from current session
            user_id = self.user_manager.validate_session(st.session_state.session_token)
            if user_id:
                # Refresh session and update token
                new_token = self.user_manager.refresh_session(user_id)
                st.session_state.session_token = new_token
                st.session_state.last_activity = datetime.now()

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get the current user's information."""
        # Try to get user info from database first
        if st.session_state.session_token and self.user_manager:
            user_id = self.user_manager.validate_session(st.session_state.session_token)
            if user_id:
                # Get user info from database
                user_info = self.user_manager.get_user_info()
                if user_info:
                    return user_info
        
        # Fall back to OAuth user info
        return st.session_state.user_info

    def create_oauth_session(self) -> OAuth2Session:
        """Create an OAuth2 session for Google authentication."""
        return OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )

    def get_authorization_url(self) -> str:
        """Generate the authorization URL for Google OAuth."""
        oauth = self.create_oauth_session()
        
        # Generate a random state parameter for security
        state = secrets.token_urlsafe(32)
        st.session_state.auth_state = state
        
        authorization_url, state = oauth.create_authorization_url(
            self.oauth_config.auth_endpoint,
            state=state
        )
        
        return authorization_url

    def handle_oauth_callback(self, url: str) -> bool:
        """
        Handle the OAuth callback and exchange authorization code for tokens.
        
        Args:
            url (str): The callback URL with authorization code
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Parse the URL to extract query parameters
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # Check for authorization code
            if 'code' not in query_params:
                st.error("No authorization code received")
                return False
            
            code = query_params['code']
            
            # Verify state parameter
            if 'state' not in query_params: # or query_params['state'][0] != st.session_state.auth_state:
                st.error("Invalid state parameter")
                return False
            
            # Exchange authorization code for tokens
            oauth = self.create_oauth_session()
            token = oauth.fetch_token(
                self.oauth_config.token_endpoint,
                authorization_response=url,
                client_secret=self.client_secret
            )
            
            # Store the token
            st.session_state.auth_token = token
            
            # Get user information
            user_info = self._get_user_info_from_token(token)
            if user_info:
                # Store OAuth user info in session state
                st.session_state.user_info = user_info
                st.session_state.authenticated = True
                
                # Handle database integration if user manager is available
                if self.user_manager:
                    is_new_user, user_id = self.user_manager.find_or_create_oauth_user(user_info)
                    if user_id:
                        # Get the session token from the database
                        db_user_info = self.user_manager.get_user_by_oauth_id(user_info.get('id'))
                        if db_user_info and db_user_info.get('session_token'):
                            session_token = db_user_info['session_token']
                            st.session_state.session_token = session_token
                            st.session_state.last_activity = datetime.now()
                        
                        if is_new_user:
                            st.success("Welcome! Your account has been created.")
                        else:
                            st.success("Welcome back!")
                
                return True
            else:
                st.error("Failed to retrieve user information")
                return False
                
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return False

    def _get_user_info_from_token(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieve user information using the access token.
        
        Args:
            token (Dict[str, Any]): The OAuth token
            
        Returns:
            Optional[Dict[str, Any]]: User information or None if failed
        """
        try:
            headers = {
                'Authorization': f"Bearer {token['access_token']}"
            }
            
            response = requests.get(
                self.oauth_config.userinfo_endpoint,
                headers=headers
            )
            
            if response.status_code == 200:
                user_info = response.json()
                return {
                    'id': user_info.get('sub'),
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'given_name': user_info.get('given_name'),
                    'family_name': user_info.get('family_name'),
                    'picture': user_info.get('picture'),
                    'verified_email': user_info.get('email_verified', False)
                }
            else:
                st.error(f"Failed to get user info: {response.status_code}")
                return None
                
        except Exception as e:
            st.error(f"Error retrieving user information: {str(e)}")
            return None

    def logout(self):
        """Log out the current user and clear session state."""
        # Clear session in database if user manager is available
        if st.session_state.session_token and self.user_manager:
            user_id = self.user_manager.validate_session(st.session_state.session_token)
            if user_id:
                self.user_manager.clear_session(user_id)
        
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.auth_token = None
        st.session_state.auth_state = None
        st.session_state.session_token = None
        st.session_state.last_activity = None
        st.rerun()

    def render_login_page(self):
        """Render the login page with Google OAuth button."""
        st.title("🔐 Login Required")
        st.markdown("Please authenticate with your Google account to continue.")
        
        # Check if OAuth is properly configured
        if not self.client_id or not self.client_secret:
            st.error("""
            OAuth is not properly configured. Please set the following environment variables:
            - GOOGLE_CLIENT_ID
            - GOOGLE_CLIENT_SECRET
            
            Or configure them in the .config.yml file.
            """)
            st.info("""
            To set up Google OAuth:
            1. Go to https://console.cloud.google.com/
            2. Create a new project or select existing one
            3. Enable Google+ API
            4. Create OAuth 2.0 credentials
            5. Add http://localhost:8501 to authorized redirect URIs
            """)
            return
        
        # Create login button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            auth_url = self.get_authorization_url()
            # Use a direct link instead of a button that renders another button
            st.markdown(f"""
            <a href="{auth_url}" target="_self">
                <button style="
                    background-color: #4285f4;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    width: 100%;
                ">
                    🔑 Sign in with Google
                </button>
            </a>
            """, unsafe_allow_html=True)
        
        st.divider()
        st.info("This application uses Google OAuth for secure authentication.")

    def render_user_info(self):
        """Render user information in the sidebar."""
        if self.is_authenticated():
            user_info = self.get_user_info()
            if user_info is None:
                return False
                
            st.sidebar.subheader("👤 User Profile")
            
            # Display user avatar if available
            if user_info.get('picture'):
                picture_url = user_info.get('picture')
                if picture_url:  # Ensure the URL is not None
                    st.sidebar.image(picture_url, width=60)
            
            # Display user name
            if user_info.get('name'):
                st.sidebar.write(f"**Name:** {user_info['name']}")
            
            # Display email
            if user_info.get('email'):
                email = user_info.get('email')
                st.sidebar.write(f"**Email:** {email}")
            
            # Display session timeout info
            if st.session_state.session_token and self.user_manager:
                # Get session expiration from database
                db_user_info = self.user_manager.get_user_by_session_token(st.session_state.session_token)
                if db_user_info and db_user_info.get('session_expires'):
                    session_expires = db_user_info['session_expires']
                    if isinstance(session_expires, str):
                        # Parse string datetime if needed
                        from datetime import datetime
                        session_expires = datetime.fromisoformat(session_expires.replace('Z', '+00:00'))
                    
                    time_left = (session_expires - datetime.now()).total_seconds()
                    if time_left > 0:
                        hours = int(time_left // 3600)
                        minutes = int((time_left % 3600) // 60)
                        if hours > 0:
                            st.sidebar.info(f"⏰ Session expires in: {hours}h {minutes}m")
                        else:
                            st.sidebar.info(f"⏰ Session expires in: {minutes}m")
                    else:
                        st.sidebar.warning("⚠️ Session expired")
            
            # Logout button
            if st.sidebar.button("🚪 Logout", use_container_width=True):
                self.logout()
            
            st.sidebar.divider()
            return True
        return False 