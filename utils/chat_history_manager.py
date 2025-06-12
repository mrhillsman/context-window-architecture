from typing import Optional, List
from utils.sqldb_manager import SQLManager
from utils.utils import Utils
import json
from google import genai


class ChatHistoryManager:
    """
    Manages chat history and summarization for a user session.
    """

    def __init__(self, sql_manager: SQLManager, user_id: str, session_id: str, client: genai.Client, summary_model: str, max_tokens: int) -> None:
        self.client = client
        self.summary_model = summary_model
        self.max_tokens = max_tokens
        self.sql_manager = sql_manager
        self.user_id = user_id
        self.session_id = session_id
        self.chat_history = []
        self.pairs_since_last_summary = 0  # Track pairs that have been added since the last summary

    def add_to_history(self, user_message: str, assistant_response: str, max_history_pairs: int) -> None:
        """
        Adds a user message and assistant response to the chat history and saves to the database.

        Args:
            user_message (str): The user's message.
            assistant_response (str): The assistant's response.
            max_history_pairs (int): The maximum number of message pairs to keep in the history.
        """
        self.chat_history.append({"user": user_message})
        self.chat_history.append(
            {"assistant": assistant_response})

        if len(self.chat_history) > max_history_pairs * 2:
            self.chat_history = self.chat_history[-max_history_pairs * 2:]

        self.save_to_db(user_message, assistant_response)
        self.pairs_since_last_summary += 1
        print("Chat history saved to database.")
        chat_history_token_count = Utils.count_number_of_tokens(
            str(self.chat_history))
        if chat_history_token_count > self.max_tokens:
            print("Summarizing the chat history ...")
            print("\nOld number of tokens:", chat_history_token_count)

            self.summarize_chat_history(max_history_pairs)  # ← Pass the parameter

            # Re-count tokens after summarization
            chat_history_token_count = Utils.count_number_of_tokens(
                str(self.chat_history))
            print("\nNew number of tokens:", chat_history_token_count)

    def save_to_db(self, user_message: str, assistant_response: str) -> None:
        """
        Saves a user message and assistant response to the database.

        Args:
            user_message (str): The user's message.
            assistant_response (str): The assistant's response.
        """
        if not self.user_id:
            print("Error: No user found in the database.")
            return
        query = """
            INSERT INTO chat_history (user_id, question, answer, session_id)
            VALUES (?, ?, ?, ?);
        """
        self.sql_manager.execute_query(
            query, (self.user_id, user_message, assistant_response, self.session_id))

    def get_latest_chat_pairs(self, num_pairs: int) -> List[tuple]:
        """
        Fetches the latest `num_pairs` user-assistant pairs from the database.

        Args:
            num_pairs (int): Number of pairs to retrieve.

        Returns:
            List[tuple]: A list of tuples containing user questions and assistant answers.
        """
        query = """
            SELECT question, answer FROM chat_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?;
        """
        chat_data = self.sql_manager.execute_query(
            query, (self.session_id, num_pairs * 2), fetch_all=True)
        # Reverse to maintain chronological order
        return list(reversed(chat_data))

    def get_latest_summary(self) -> Optional[str]:
        """
        Retrieves the latest summary for the current session from the database.

        Returns:
            Optional[str]: The latest summary or None if no summary exists.
        """
        query = """
            SELECT summary_text FROM summary
            WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1;
        """
        summary = self.sql_manager.execute_query(
            query, (self.session_id,), fetch_one=True)
        return summary[0] if summary else None

    def save_summary_to_db(self, summary_text: str) -> None:
        """
        Saves a generated summary to the database.

        Args:
            summary_text (str): The summary text to save.
        """
        if not self.user_id or not summary_text:
            return
        query = """
            INSERT INTO summary (user_id, session_id, summary_text)
            VALUES (?, ?, ?);
        """
        self.sql_manager.execute_query(
            query, (self.user_id, self.session_id, summary_text))
        print("Summary saved to database.")

    def update_chat_summary(self, max_history_pairs: int) -> None:
        """
        Updates the chat summary when {max_history_pairs} new pairs have been added since the last summary.

        Args:
            max_history_pairs (int): Number of pairs required to trigger summary generation.
        """
        print("pairs_since_last_summary:", self.pairs_since_last_summary)
        if self.pairs_since_last_summary < max_history_pairs:
            return None
        # Fetch the latest two pairs (if available)
        chat_data = self.get_latest_chat_pairs(max_history_pairs)

        # Fetch the previous summary
        previous_summary = self.get_latest_summary()

        # Only generate a new summary if there are exactly two pairs
        if len(chat_data) <= max_history_pairs:
            print("Insufficient chat data. Skipping summary.")
            return None

        summary_text = self.generate_the_new_summary(
            self.client, self.summary_model, chat_data, previous_summary)
        # print("Generated summary:", summary_text)

        if summary_text:
            self.save_summary_to_db(summary_text)
            self.pairs_since_last_summary = 0  # Reset the counter after a summary
            print("Chat history summary generated and saved to database.")
            return None
        return None

    @staticmethod
    def generate_the_new_summary(
        client: genai.Client,
        summary_model: str,
        chat_data: List[tuple],
        previous_summary: Optional[str]
    ) -> Optional[str]:
        """
        Generates a summary from the latest two pairs and the previous summary.

        Args:
            client (genai.Client): The Gemini model instance.
            summary_model (str): The model name to use for summarization.
            chat_data (List[tuple]): A list of tuples containing user questions and assistant answers.
            previous_summary (Optional[str]): The previous summary, if available.

        Returns:
            Optional[str]: The generated summary or None if an error occurs.
        """
        if not chat_data:
            return None

        # Start building the prompt
        summary_prompt = "Summarize the following conversation:\n\n"

        if previous_summary:
            summary_prompt += f"Previous summary:\n{previous_summary}\n\n"

        for q, a in chat_data:
            summary_prompt += f"User: {q}\nAssistant: {a}\n\n"

        summary_prompt += "Provide a concise summary while keeping important details."

        try:
            # Create a new model instance for the summary model
            summary_client = client
            response = summary_client.models.generate_content(
                model=summary_model,
                contents=summary_prompt
            )
            return response.text
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return None

    def summarize_chat_history(self, max_history_pairs: int = 1):  # ← Add parameter
        """
        Summarizes older parts of the chat history to reduce token count while maintaining context.
        """
        # Select older pairs to summarize (keep the latest pairs untouched)
        pairs_to_keep = max_history_pairs  # ← Use the parameter instead of hardcoded 1
        pairs_to_summarize = self.chat_history[:-pairs_to_keep * 2]

        if len(pairs_to_summarize) == 0:
            return

        # Create a prompt for summarization
        prompt = f"""
        Summarize the following conversation while preserving key details and the conversation's tone:
        {pairs_to_summarize}

        Return the summarized conversation (in JSON format with 'user' and 'assistant' pairs):
        """
        try:
            # Create a new model instance for the summary model
            summary_client = self.client
            response = summary_client.models.generate_content(
                model=self.summary_model,
                contents=prompt
            )
            summarized_pairs = response.text
            summarized_pairs = json.loads(summarized_pairs)

            # ✅ If the output is a single dictionary, wrap it in a list
            if isinstance(summarized_pairs, dict):
                summarized_pairs = [summarized_pairs]

            # ✅ Ensure the format is consistent
            if isinstance(summarized_pairs, list) and all(
                    isinstance(
                        pair, dict) and 'user' in pair and 'assistant' in pair
                    for pair in summarized_pairs
            ):
                # Keep the latest pairs and summarized history
                self.chat_history = summarized_pairs + \
                                    self.chat_history[-pairs_to_keep * 2:]
                print("Chat history summarized.")
            else:
                raise ValueError("Invalid format received from LLM.")

        except Exception as e:
            print(f"Failed to summarize chat history: {e}")