from utils.sqldb_manager import SQLManager
from utils.utils import Utils
from google import genai
from typing import Union, Tuple, List

class SearchManager:
    def __init__(self, sql_manager: SQLManager, utils: Utils, client: genai.Client, summary_model: str, max_characters: int = 1000):
        """
        Initializes the SearchManager instance.
        """
        self.sql_manager = sql_manager
        self.utils = utils
        self.client = client
        self.summary_model = summary_model
        self.max_characters = max_characters

    def search_chat_history(self, search_term: str) -> Tuple[str, Union[str, List[Tuple[str, str, str]]]]:
        """
        Searches chat history for a term, performing a case-insensitive lookup.

        Args:
            search_term(str): The keyword to search in the chat history.

        Returns:
            Tuple[str, Union[str, List[Tuple[str, str, str]]]]: A tuple containing:
                - A status message (str)
                - Either an error message (str) or a list of tuples containing matching question, answer, and timestamp
        """
        try:
            search_term = search_term.lower()
            query = """
            SELECT question, answer, timestamp FROM chat_history
            WHERE LOWER(question) LIKE ? OR LOWER(answer) LIKE ?
            ORDER BY timestamp
            LIMIT 3;
            """

            results = self.sql_manager.execute_query(
                query, (f"%{search_term}%", f"%{search_term}%"), fetch_all=True)
            # Ensure the results maintain the order of question, then answer
            formatted_results = [(q, a, t) for q, a, t in results]
            if not formatted_results:
                return "Function call failed.", "No results found. Please try again with a different word."

            num_characters = self.utils.count_number_of_characters(
                str(results))
            print(f"Number of characters in search results: {num_characters}")
            if num_characters > self.max_characters:
                results_summary = self.summarize_search_result(
                    str(formatted_results))
                return "Function call successful.", results_summary
            return "Function call successful.", formatted_results
        except Exception as e:
            return "Function call failed.", f"Error: {e}"

    def summarize_search_result(self, search_result: str) -> str:
        """
        Summarizes a search result if it exceeds the character limit.

        Args:
            search_result (str): The search result to summarize.

        Returns:
            str: A summarized version of the search result.
        """
        prompt = f"""
        Summarize the following conversation within {self.max_characters} characters
        {search_result}
        """

        summary_client = self.client
        response = summary_client.models.generate_content(
            model=self.summary_model,
            contents=prompt
        )
        return response.text
