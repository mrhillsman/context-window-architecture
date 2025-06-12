"""
Agentic Chat Interface with Memory and Agent Capabilities

This module provides an advanced chat interface with memory systems,
agent capabilities, and enhanced AI interactions.

Features:
    - Agentic behavior with function calling
    - Long-term memory management
    - Context-aware responses
    - Advanced reasoning capabilities

Usage:
    This module is loaded automatically by main.py when chatbot.type is set to "agentic"
"""

import os
import json
from datetime import datetime
from box import Box
import yaml
from pyprojroot import here

from google import genai
from google.genai import types
import streamlit as st

from utils.chat_history_manager import ChatHistoryManager
from utils.sqldb_manager import SQLManager
from utils.system_prompt import system_prompt_for_agentic_ui_chat
from utils.user_manager import UserManager
from utils.search_manager import SearchManager


with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))


def search_chat_history(search_term: str) -> dict:
    """
    Search through the user's chat history for relevant information.

    Args:
        search_term: The term or phrase to search for in the chat history

    Returns:
        A dictionary containing the search results or error message
    """
    search_manager = st.session_state.search_manager
    if search_manager:
        status, result = search_manager.search_chat_history(search_term)

        # If result is a list of tuples, convert to a more JSON-friendly format
        if isinstance(result, list) and result:
            # Convert list of tuples to list of dictionaries
            formatted_results = []
            for item in result:
                if isinstance(item, tuple) and len(item) >= 3:
                    formatted_results.append({
                        "question": item[0],
                        "answer": item[1],
                        "timestamp": str(item[2])  # Convert timestamp to string for JSON serialization
                    })
            return {
                "status": status,
                "result": formatted_results,
                "message": f"Found {len(formatted_results)} matching conversation(s)"
            }
        else:
            # Result is already a string (either error message or summarized results)
            return {
                "status": status,
                "result": str(result)
            }
    return {
        "status": "Function call failed.",
        "result": "Search manager not initialized"
    }


def add_user_info_to_database(
    name: str = None,
    last_name: str = None,
    age: int = None,
    gender: str = None,
    location: str = None,
    occupation: str = None,
    interests: list[str] = None
) -> dict:
    """
    Update the user's information in the database.

    Args:
        name: User's first name
        last_name: User's last name
        age: User's age
        gender: User's gender
        location: User's location
        occupation: User's occupation
        interests: List of user's interests

    Returns:
        A dictionary containing the update status and message
    """
    user_manager = st.session_state.user_manager
    if user_manager:
        # Build user_info dict with only non-None values
        user_info = {}
        if name is not None:
            user_info["name"] = name
        if last_name is not None:
            user_info["last_name"] = last_name
        if age is not None:
            user_info["age"] = age
        if gender is not None:
            user_info["gender"] = gender
        if location is not None:
            user_info["location"] = location
        if occupation is not None:
            user_info["occupation"] = occupation
        if interests is not None:
            user_info["interests"] = interests

        if not user_info:
            return {
                "status": "Function call failed.",
                "result": "No user information provided to update"
            }

        status, result = user_manager.add_user_info_to_database(user_info)
        return {
            "status": status,
            "result": result
        }
    return {
        "status": "Function call failed.",
        "result": "User manager not initialized"
    }


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
        - utils (Utils): Utility functions for the chat application
        - search_manager (SearchManager): Manager for searching chat history

    Returns:
        None

    Example:
        >>> init_session_state()
        # Session state variables are now initialized
    """
    # Initialize empty message history for storing chat conversations
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Try to get API key from environment, fallback to empty string
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    # Initialize model instance holder
    if 'model' not in st.session_state:
        st.session_state.model = None

    # Initialize chat session holder
    if 'chat' not in st.session_state:
        st.session_state.chat = None

    # Set the session ID using UUID
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

    # Initialize managers in the session state
    if 'sqldb_manager' not in st.session_state:
        st.session_state.sqldb_manager = SQLManager(f'{config.db.sql.dir}/{config.db.sql.file}')

    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager(st.session_state.sqldb_manager)

    if 'chat_history_manager' not in st.session_state:
        st.session_state.chat_history_manager = None

    # Initialize utils in the session state
    if 'utils' not in st.session_state:
        from utils.utils import Utils
        st.session_state.utils = Utils()

    # Initialize search manager in the session state
    if 'search_manager' not in st.session_state:
        st.session_state.search_manager = None


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
        - Initializes st.session_state.search_manager with the chat client
        - Displays error messages in Streamlit interface on failure

    Example:
        >>> success = initialize_gemini("your-api-key")
        >>> if success:
                print("Gemini initialized successfully")
    """
    if not api_key:
        return False

    try:
        # Configure the Google Generative AI library with the provided API key
        client = genai.Client(api_key=api_key)

        # Start a fresh chat session with empty history
        # This ensures each session starts clean without the previous context
        st.session_state.chat = client

        # Initialize the search manager with the chat client
        if st.session_state.search_manager is None:
            st.session_state.search_manager = SearchManager(
                st.session_state.sqldb_manager,
                st.session_state.utils,
                client,
                config.llm_config.summary_model,
                config.chat_history_config.max_characters
            )

        return True

    except Exception as e:
        # Display user-friendly error message in the Streamlit interface
        st.error(f"Failed to initialize Gemini: {str(e)}")
        return False


def get_gemini_response_with_tools(system_prompt: str, prompt: str, function_call_count: int = 0) -> tuple[str, str, str, dict, int]:
    """
    Enhanced version that instructs the model to use tools through prompting.
    This approach works when native tool calling isn't available.

    Args:
        system_prompt (str): The system instructions to send to Gemini
        prompt (str): The user's message/question to send to Gemini
        function_call_count (int): The number of function calls made so far

    Returns:
        tuple: A tuple containing:
            - assistant_response (str): The model's response text or an error message
            - function_call_state (str): The state of the function call
            - function_name (str): The name of the function called (if any)
            - function_args (dict): The arguments for the function call (if any)
            - function_call_count (int): The updated number of function calls
    """
    # Ensure chat session is properly initialized
    if not st.session_state.chat:
        return "❌ Chat session not initialized. Please check your API key.", None, None, {}, function_call_count

    # Check if we've reached the maximum number of function calls
    if function_call_count >= config.agent_config.max_function_calls:
        return "I've reached the maximum number of function calls for this conversation.", None, None, {}, function_call_count

    try:
        # Enhanced system prompt that includes tool instructions
        enhanced_system_prompt = system_prompt + """

IMPORTANT: The function mentioned as 'search_vector_db' in the instructions above is actually called 'search_chat_history' in the available functions below.

You have access to these functions:

1. search_chat_history(search_term: str) - Search through the user's previous conversations
   - Use this when:
     * The user asks "What did we talk about..." or "Do you remember when..."
     * You need context from previous conversations to answer the current question
     * The user references something from past chats
     * You need to find specific information discussed before
   - The search_term should be a clear, specific keyword or phrase
   - Returns matching conversations with questions, answers, and timestamps

2. add_user_info_to_database(name: str = None, last_name: str = None, age: int = None, gender: str = None, location: str = None, occupation: str = None, interests: list[str] = None) - Update user information
   - Use this when the user wants to update their personal information
   - Only include the fields that need to be updated
   - All parameters are optional

When you need to use a function, respond with ONLY a JSON object in this exact format:
{
  "function": "function_name",
  "arguments": {
    "arg1": "value1",
    "arg2": "value2"
  }
}

Examples:
- User: "What did we discuss about Python?" → {"function": "search_chat_history", "arguments": {"search_term": "Python"}}
- User: "Do you remember our conversation about machine learning?" → {"function": "search_chat_history", "arguments": {"search_term": "machine learning"}}
- User: "Update my name to John" → {"function": "add_user_info_to_database", "arguments": {"name": "John"}}
- User: "I'm 30 years old and live in New York" → {"function": "add_user_info_to_database", "arguments": {"age": 30, "location": "New York"}}

Do not include any other text when calling a function. After receiving the function result, provide a natural response to the user based on the result.
"""

        # Send the user's message to Gemini
        response = st.session_state.chat.models.generate_content(
            model=config.llm_config.chat_model,
            config=types.GenerateContentConfig(
                system_instruction=enhanced_system_prompt
            ),
            contents=prompt
        )

        response_text = response.text.strip()

        # Check if the response is a function call (JSON format)
        if response_text.startswith('{') and response_text.endswith('}'):
            try:
                function_data = json.loads(response_text)
                if 'function' in function_data and 'arguments' in function_data:
                    function_name = function_data['function']
                    function_args = function_data['arguments']
                    function_call_count += 1
                    return "", "Function call requested", function_name, function_args, function_call_count
            except json.JSONDecodeError:
                # Not a valid JSON, treat as normal response
                pass

        # Normal response (no function call)
        return response_text, None, None, {}, function_call_count

    except Exception as e:
        # Log the full error for debugging
        print(f"Error in get_gemini_response_with_tools: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

        # Convert technical errors to user-friendly messages
        error_msg = f"❌ Error: {str(e)}"

        # Handle specific common error cases with helpful guidance
        if "API_KEY_INVALID" in str(e):
            error_msg = "❌ Invalid API key. Please check your API key in the sidebar."
        elif "RATE_LIMIT_EXCEEDED" in str(e):
            error_msg = "⏱️ Rate limit exceeded. Please wait a moment and try again."
        elif "SAFETY" in str(e):
            error_msg = "⚠️ Response blocked due to safety settings. Please try rephrasing your message."

        return error_msg, None, None, {}, function_call_count


def execute_function_call(function_name: str, function_args: dict) -> dict:
    """
    Executes the requested function based on the function name and arguments.

    Args:
        function_name (str): The name of the function to execute.
        function_args (dict): The arguments required for the function.

    Returns:
        dict: The function result
    """
    print(f"Executing function: {function_name} with args: {function_args}")

    if function_name == "search_chat_history":
        result = search_chat_history(**function_args)
        print(f"Search result: {result}")
        return result
    elif function_name == "add_user_info_to_database":
        result = add_user_info_to_database(**function_args)
        print(f"Update result: {result}")
        return result

    return {"status": "Function call failed.", "result": "Unknown function"}


def main() -> None:
    """
    Main function for the Agentic Chat interface.
    """
    st.set_page_config(
        page_title="Agentic Chat",
        page_icon="🤖",
        layout="wide"
    )

    # Initialize all session state variables
    init_session_state()

    # Use managers from the session state
    sqldb_manager = st.session_state.sqldb_manager
    user_manager = st.session_state.user_manager

    # Initialize chat_history_manager only once or when the chat client changes
    if (st.session_state.chat_history_manager is None or
            st.session_state.chat_history_manager.client != st.session_state.chat):
        st.session_state.chat_history_manager = ChatHistoryManager(
            sqldb_manager,
            user_manager.user_id,
            st.session_state.session_id,
            st.session_state.chat,
            config.llm_config.summary_model,
            config.chat_history_config.max_tokens
        )

    chat_history_manager = st.session_state.chat_history_manager

    # === SIDEBAR CONFIGURATION ===
    with st.sidebar:
        st.title("⚙️ Settings")
        st.info("🤖 Chatbot: Agentic")

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
        if api_key and not st.session_state.chat:
            initialize_gemini(api_key)

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
    st.title("🤖 Agentic Chat Interface")
    st.markdown("Advanced chat with memory and agent capabilities")

    # Display all previous chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input handling
    if prompt := st.chat_input("Type your message here..." if api_key else "Please set your API key first"):
        # Validate prerequisites before processing the message
        if not st.session_state.gemini_api_key:
            st.error("❌ Please configure your Gemini API key in the sidebar")
        elif not st.session_state.chat:
            st.error("❌ Gemini not initialized. Please check your API key.")
        else:
            # Display a user message immediately
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    previous_summary = chat_history_manager.get_latest_summary()
                    function_call_count = 0
                    final_response = ""
                    function_results = []

                    # Process the conversation with function calling
                    current_prompt = prompt
                    while True:
                        # Generate the system prompt with current context
                        function_result_section = ""
                        if function_results:
                            function_result_section = "\n\n## Previous Function Results:\n"
                            for result in function_results:
                                function_result_section += f"- {result['function']}: {result['result']}\n"

                        system_prompt = system_prompt_for_agentic_ui_chat(
                            user_manager.user_info,
                            previous_summary,
                            chat_history_manager.chat_history,
                            function_result_section
                        )

                        # Get response from Gemini
                        response, function_state, function_name, function_args, function_call_count = get_gemini_response_with_tools(
                            system_prompt,
                            current_prompt,
                            function_call_count
                        )

                        # If we got a function call request, execute it
                        if function_state == "Function call requested":
                            # Execute the function
                            function_result = execute_function_call(function_name, function_args)

                            # Store the result
                            function_results.append({
                                "function": function_name,
                                "args": function_args,
                                "result": function_result
                            })

                            # Refresh user info if it was updated
                            if function_name == "add_user_info_to_database" and function_result.get("status") == "Function call successful.":
                                user_manager.refresh_user_info()

                            # Prepare prompt for next iteration with function result
                            if function_result.get("status") == "Function call successful.":
                                if function_name == "search_chat_history":
                                    # Handle search results
                                    result_data = function_result.get("result", "")
                                    if isinstance(result_data, list):
                                        # Format the search results nicely
                                        search_summary = f"Found {len(result_data)} matching conversation(s) for '{function_args.get('search_term', '')}':\n"
                                        for idx, conv in enumerate(result_data, 1):
                                            search_summary += f"\n{idx}. Q: {conv['question']}\n   A: {conv['answer']}\n   Time: {conv['timestamp']}\n"
                                        current_prompt = f"The search was successful. {search_summary}\nPlease provide a helpful response to the user about these search results."
                                    else:
                                        # Result is a summary string
                                        current_prompt = f"The search was successful. Results: {result_data}\nPlease provide a helpful response to the user about these search results."
                                else:
                                    # For other functions like add_user_info_to_database
                                    current_prompt = f"The function {function_name} was executed successfully. Result: {function_result.get('result', 'Operation completed.')}\nPlease provide a natural response to the user confirming the action."
                            else:
                                # Function failed
                                current_prompt = f"The function {function_name} failed with message: {function_result.get('result', 'Unknown error')}\nPlease inform the user about this issue and suggest alternatives if appropriate."

                            # Continue the conversation
                            continue

                        # If we got a text response, we're done
                        if response:
                            final_response = response
                            break

                        # Safety check to prevent infinite loops
                        if function_call_count >= config.agent_config.max_function_calls:
                            final_response = "I've reached the maximum number of function calls for this conversation."
                            break

                    # Display the final response
                    st.markdown(final_response)

                    # Add messages to session state for display
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": final_response})

                    # Add to chat history for context
                    chat_history_manager.add_to_history(prompt, final_response, config.chat_history_config.max_history_pairs)
                    chat_history_manager.update_chat_summary(config.chat_history_config.max_history_pairs)

                    # Debug logging
                    print(f"User prompt: {prompt}\n")
                    print(f"Function calls made: {function_call_count}")
                    if function_results:
                        print(f"Functions executed: {[r['function'] for r in function_results]}")


if __name__ == "__main__":
    main()