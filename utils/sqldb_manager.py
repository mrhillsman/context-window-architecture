import sqlite3
from typing import Any

class SQLManager:
    """
    A manager for handling SQLite database connections and executing queries.
    """

    def __init__(self, db_path: str):
        """
        Initializes the SQLManager instance.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False) -> list|Any:
        """
        Executes an SQL query with optional parameters and fetch options.

        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): Parameters to pass to the SQL query. Defaults to ().
            fetch_one (bool, optional): Whether to fetch a single row. Defaults to False.
            fetch_all (bool, optional): Whether to fetch all rows. Defaults to False.

        Returns:
            Optional[list[tuple[Any, ...]]]:
                - A single row (if `fetch_one` is True).
                - All rows (if `fetch_all` is True).
                - None if no data is fetched.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone() if fetch_one else cursor.fetchall() if fetch_all else None
        conn.commit()
        conn.close()
        return result