import math
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from utils.sqldb_manager import SQLManager


class UserManager:
    """
    Manages user-related operations, including retrieving user information and user ID
    from the database. Enhanced to support OAuth authentication and session management.
    """

    def __init__(self, sql_manager: SQLManager):
        """
        Initializes the UserManager with a database manager.

        Args:
            sql_manager (SQLManager): The database manager instance to execute queries.
        """
        self.sql_manager = sql_manager
        self.user_info = self.get_user_info()
        self.user_id = self.get_user_id()

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves user information from the database, filtering out empty values, None, and NaN.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing user information with valid values,
            or None if no user is found.
        """
        query = "SELECT * FROM user_info LIMIT 1;"
        user = self.sql_manager.execute_query(query, fetch_one=True)
        if user:
            # Map all columns including new OAuth fields
            user_info = {
                "id": user[0],
                "user_id": user[1] if len(user) > 1 else None,
                "email": user[2] if len(user) > 2 else None,
                "name": user[3] if len(user) > 3 else None,
                "given_name": user[4] if len(user) > 4 else None,
                "family_name": user[5] if len(user) > 5 else None,
                "picture": user[6] if len(user) > 6 else None,
                "verified_email": user[7] if len(user) > 7 else False,
                "last_login": user[8] if len(user) > 8 else None,
                "session_token": user[9] if len(user) > 9 else None,
                "session_expires": user[10] if len(user) > 10 else None
            }
            return {k: v for k, v in user_info.items() if v not in (None, "") and not (isinstance(v, float) and math.isnan(v))}
        return None

    def refresh_user_info(self):
        """Refresh user information from the database."""
        self.user_info = self.get_user_info()

    def get_user_id(self) -> Optional[int]:
        """
        Retrieves the user ID from the database.

        Returns:
            Optional[int]: The user ID if found, otherwise None.
        """
        query = "SELECT id FROM user_info LIMIT 1;"
        user = self.sql_manager.execute_query(query, fetch_one=True)
        return user[0] if user else None

    def find_or_create_oauth_user(self, oauth_user_info: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """
        Find existing OAuth user or create a new one based on OAuth information.
        
        Args:
            oauth_user_info (Dict[str, Any]): OAuth user information from Google
            
        Returns:
            Tuple[bool, Optional[int]]: (is_new_user, user_id)
        """
        oauth_id = oauth_user_info.get('id')
        oauth_email = oauth_user_info.get('email')
        
        if not oauth_id or not oauth_email:
            return False, None
            
        # Check if user exists by OAuth ID
        query = "SELECT id FROM user_info WHERE user_id = ?;"
        existing_user = self.sql_manager.execute_query(query, (oauth_id,), fetch_one=True)
        
        if existing_user:
            user_id = existing_user[0]
            # Update last login and session info
            self._update_user_session(user_id, oauth_user_info)
            return False, user_id
        else:
            # Create new user
            user_id = self._create_oauth_user(oauth_user_info)
            return True, user_id

    def _create_oauth_user(self, oauth_user_info: Dict[str, Any]) -> Optional[int]:
        """
        Create a new user record for OAuth authentication.
        
        Args:
            oauth_user_info (Dict[str, Any]): OAuth user information
            
        Returns:
            Optional[int]: The new user ID or None if creation failed
        """
        # Generate session token and expiration (24 hours from now)
        session_token = secrets.token_urlsafe(32)
        session_expires = datetime.now() + timedelta(hours=24)
        
        query = """
        INSERT INTO user_info (
            user_id, email, name, given_name, family_name, picture, verified_email,
            last_login, session_token, session_expires
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        params = (
            oauth_user_info.get('id'),
            oauth_user_info.get('email'),
            oauth_user_info.get('name'),
            oauth_user_info.get('given_name'),
            oauth_user_info.get('family_name'),
            oauth_user_info.get('picture'),
            oauth_user_info.get('verified_email', False),
            datetime.now(),
            session_token,
            session_expires
        )
        
        self.sql_manager.execute_query(query, params)
        
        # Get the new user ID
        query = "SELECT id FROM user_info WHERE user_id = ?;"
        user = self.sql_manager.execute_query(query, (oauth_user_info.get('id'),), fetch_one=True)
        return user[0] if user else None

    def _update_user_session(self, user_id: int, oauth_user_info: Dict[str, Any]):
        """
        Update user session information after login.
        
        Args:
            user_id (int): User ID
            oauth_user_info (Dict[str, Any]): OAuth user information
        """
        # Generate new session token and expiration (24 hours from now)
        session_token = secrets.token_urlsafe(32)
        session_expires = datetime.now() + timedelta(hours=24)
        
        query = """
        UPDATE user_info 
        SET last_login = ?, session_token = ?, session_expires = ?,
            picture = ?, verified_email = ?
        WHERE id = ?;
        """
        
        params = (
            datetime.now(),
            session_token,
            session_expires,
            oauth_user_info.get('picture'),
            oauth_user_info.get('verified_email', False),
            user_id
        )
        
        self.sql_manager.execute_query(query, params)

    def validate_session(self, session_token: str) -> Optional[int]:
        """
        Validate session token and return user ID if valid.
        
        Args:
            session_token (str): Session token to validate
            
        Returns:
            Optional[int]: User ID if session is valid, None otherwise
        """
        if not session_token:
            return None
            
        query = """
        SELECT id FROM user_info 
        WHERE session_token = ? AND session_expires > ?;
        """
        
        user = self.sql_manager.execute_query(
            query, 
            (session_token, datetime.now()), 
            fetch_one=True
        )
        
        return user[0] if user else None

    def refresh_session(self, user_id: int) -> str:
        """
        Refresh session for a user and return new session token.
        
        Args:
            user_id (int): User ID
            
        Returns:
            str: New session token
        """
        session_token = secrets.token_urlsafe(32)
        session_expires = datetime.now() + timedelta(hours=24)
        
        query = """
        UPDATE user_info 
        SET session_token = ?, session_expires = ?
        WHERE id = ?;
        """
        
        self.sql_manager.execute_query(query, (session_token, session_expires, user_id))
        return session_token

    def clear_session(self, user_id: int):
        """
        Clear session for a user (logout).
        
        Args:
            user_id (int): User ID
        """
        query = """
        UPDATE user_info 
        SET session_token = NULL, session_expires = NULL
        WHERE id = ?;
        """
        
        self.sql_manager.execute_query(query, (user_id,))

    def get_user_by_oauth_id(self, oauth_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by OAuth ID.
        
        Args:
            oauth_id (str): OAuth user ID
            
        Returns:
            Optional[Dict[str, Any]]: User information or None
        """
        query = "SELECT * FROM user_info WHERE user_id = ?;"
        user = self.sql_manager.execute_query(query, (oauth_id,), fetch_one=True)
        
        if user:
            user_info = {
                "id": user[0],
                "user_id": user[1] if len(user) > 1 else None,
                "email": user[2] if len(user) > 2 else None,
                "name": user[3] if len(user) > 3 else None,
                "given_name": user[4] if len(user) > 4 else None,
                "family_name": user[5] if len(user) > 5 else None,
                "picture": user[6] if len(user) > 6 else None,
                "verified_email": user[7] if len(user) > 7 else False,
                "last_login": user[8] if len(user) > 8 else None,
                "session_token": user[9] if len(user) > 9 else None,
                "session_expires": user[10] if len(user) > 10 else None
            }
            return {k: v for k, v in user_info.items() if v not in (None, "") and not (isinstance(v, float) and math.isnan(v))}
        return None

    def add_user_info_to_database(self, user_info: dict) -> Tuple[str, str]:
        """
        Updates the user information in the database if valid keys are provided.
        Only updates fields that exist in the user_info table schema.

        Args:
            user_info (dict): Dictionary containing user attributes to update.
        """
        try:
            # Only allow updates to fields that exist in the user_info table
            valid_keys = {
                "user_id", "email", "name", "given_name", "family_name", 
                "picture", "verified_email"
            }

            for key in user_info.keys():
                if key not in valid_keys:
                    return "Function call failed.", f"Please provide a valid key from the following list: {', '.join(sorted(valid_keys))}"

            processed_info = user_info.copy()

            # Prepare SQL SET clause
            set_clause = ", ".join(
                [f"{key} = ?" for key in processed_info.keys()])
            params = tuple(processed_info.values())

            if not set_clause:  # Check if there's anything to update
                return "Function call failed.", "No valid fields to update."

            query = f"""
            UPDATE user_info
            SET {set_clause}
            WHERE id = (SELECT id FROM user_info LIMIT 1);
            """

            self.sql_manager.execute_query(query, params)
            return "Function call successful.", "User information updated."
        except Exception as e:
            print(f"Error: {e}")
            return "Function call failed.", f"Error: {e}"

    def get_user_by_session_token(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by session token.
        
        Args:
            session_token (str): Session token
            
        Returns:
            Optional[Dict[str, Any]]: User information or None
        """
        query = "SELECT * FROM user_info WHERE session_token = ?;"
        user = self.sql_manager.execute_query(query, (session_token,), fetch_one=True)
        
        if user:
            user_info = {
                "id": user[0],
                "user_id": user[1] if len(user) > 1 else None,
                "email": user[2] if len(user) > 2 else None,
                "name": user[3] if len(user) > 3 else None,
                "given_name": user[4] if len(user) > 4 else None,
                "family_name": user[5] if len(user) > 5 else None,
                "picture": user[6] if len(user) > 6 else None,
                "verified_email": user[7] if len(user) > 7 else False,
                "last_login": user[8] if len(user) > 8 else None,
                "session_token": user[9] if len(user) > 9 else None,
                "session_expires": user[10] if len(user) > 10 else None
            }
            return {k: v for k, v in user_info.items() if v not in (None, "") and not (isinstance(v, float) and math.isnan(v))}
        return None