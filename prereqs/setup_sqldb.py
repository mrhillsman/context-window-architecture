"""
SQLite Database Setup Module

This module provides functionality to initialize and configure SQLite database
for storing user information, chat history, and conversation summaries.

Dependencies:
    - sqlite3: Built-in Python SQLite database interface
    - pyprojroot: Project root path management
    - os: Operating system interface for directory operations

Database Schema:
    - user_info: Stores user profile information
    - chat_history: Records chat interactions with timestamps
    - summary: Stores summarized chat sessions
"""

from box import Box
import os
import sqlite3
from pyprojroot import here
import yaml

with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))

def create_user_info():
    """
    Creates SQLite database and initializes tables for user information, chat history, and summaries.

    This function performs the following operations:
    - Creates a `db` directory if it doesn't exist
    - Establishes a SQLite connection to `store.db`
    - Creates the following tables if they don't already exist:
        - `user_info`: Stores user details (name, occupation, location, etc.)
        - `chat_history`: Records chat interactions with timestamps and session IDs
        - `summary`: Stores summarized chat sessions
    - Inserts a sample user (Melvin Hillsman) if no user records exist

    Database Structure:
        user_info table:
            - id (INTEGER, PRIMARY KEY): Auto-incrementing unique identifier
            - name (TEXT, NOT NULL): User's first name
            - last_name (TEXT, NOT NULL): User's last name
            - occupation (TEXT, NOT NULL): User's job/profession
            - location (TEXT, NOT NULL): User's geographic location
            - age (INTEGER, NULLABLE): User's age (optional)
            - gender (TEXT, NULLABLE): User's gender (optional)
            - interests (TEXT, NULLABLE): User's interests/hobbies (optional)

        chat_history table:
            - id (INTEGER, PRIMARY KEY): Auto-incrementing unique identifier
            - user_id (INTEGER, FOREIGN KEY): References user_info.id
            - timestamp (DATETIME, DEFAULT CURRENT_TIMESTAMP): When message was sent
            - question (TEXT, NOT NULL): User's question/input
            - answer (TEXT, NOT NULL): AI's response
            - session_id (TEXT, NOT NULL): Unique session identifier

        summary table:
            - id (INTEGER, PRIMARY KEY): Auto-incrementing unique identifier
            - user_id (INTEGER, FOREIGN KEY): References user_info.id
            - session_id (TEXT, NOT NULL): Session being summarized
            - summary_text (TEXT, NOT NULL): Generated summary content
            - timestamp (DATETIME, DEFAULT CURRENT_TIMESTAMP): When summary was created

    Database Location:
        The database file is created at: {project_root}/db/store.db

    Sample Data:
        Creates a default user "Melvin Hillsman" if no users exist, with:
        - Name: Melvin Hillsman
        - Occupation: Principal Software Engineer
        - Location: USA
        - Age, gender, interests: NULL (to be filled by chatbot)

    Raises:
        OSError: If the data directory cannot be created
        sqlite3.Error: If database operations fail

    Returns:
        None
    """

    # Create the data directory if it doesn't exist
    # This directory is used for storing various data files
    data_dir = config.db.sql.dir
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            print(f"Directory `{data_dir}` was created.")
        except OSError as err:
            raise OSError(f"Failed to create db directory: {err}")
    
    # Establish connection to SQLite database
    # The database file will be created if it doesn't exist
    db_file = f'{config.db.sql.dir}/{config.db.sql.file}'
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
    except sqlite3.Error as err:
        raise sqlite3.Error(f"Failed to connect to database: {err}")

    try:
        # Create all required tables using executescript for efficiency
        # Each table is created only if it doesn't already exist
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            occupation TEXT NOT NULL,
            location TEXT NOT NULL,
            age INTEGER,  -- Allow NULL values (chatbot can fill later)
            gender TEXT,  -- Allow NULL values (chatbot can fill later)
            interests TEXT  -- Allow NULL values (chatbot can fill later)
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            session_id TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user_info(id)
        );

        CREATE TABLE IF NOT EXISTS summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_info(id)
        );
        """)

        # Insert a sample user if no users exist in the database
        # This provides a default user for testing and initial setup
        # Uses a conditional INSERT to avoid duplicates
        cursor.execute("""
        INSERT INTO user_info (name, last_name, occupation, location, age, gender, interests)
        SELECT 'Melvin', 'Hillsman', 'Principal Software Engineer', 'USA', NULL, NULL, NULL
        WHERE NOT EXISTS (SELECT 1 FROM user_info);
        """)

        # Commit all changes to the database
        conn.commit()
        
    except sqlite3.Error as err:
        # Rollback any changes if an error occurs
        conn.rollback()
        raise sqlite3.Error(f"Database operation failed: {err}")
    
    finally:
        # Always close the database connection
        conn.close()


if __name__ == "__main__":
    """
    Main execution block for standalone script usage.
    
    When run directly, this script will:
    1. Create the necessary directory structure
    2. Initialize the SQLite database
    3. Create all required tables
    4. Insert sample data if needed
    5. Display status information
    
    Usage:
        python setup_sqldb.py
        
    This is useful for:
    - Initial project setup
    - Database schema updates
    - Testing database connectivity
    - Resetting the database structure
    """
    try:
        create_user_info()
        print("✅ SQLite database setup completed successfully!")
        print(f"📁 Database location: {config.db.sql.dir}/{config.db.sql.file}")
        print("🗃️ Tables created: user_info, chat_history, summary")
    except Exception as e:
        print(f"❌ Error setting up SQLite database: {e}")
        raise