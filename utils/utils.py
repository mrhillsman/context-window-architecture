import tiktoken
from pydantic import create_model
import inspect
from inspect import Parameter
from typing import Callable, Dict, Any


class Utils:
    @staticmethod
    def count_number_of_tokens(text: str) -> int:
        """
        Counts the number of tokens in a given text using the GPT-4o-mini encoding.

        Args:
            text (str): The text to tokenize.

        Returns:
            int: The number of tokens in the input text.
        """
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = encoding.encode(text)
        return len(tokens)

    @staticmethod
    def count_number_of_characters(text: str) -> int:
        """
        Counts the number of characters in a given text.

        Args:
            text (str): The text to measure.

        Returns:
            int: The number of characters in the input text.
        """
        return len(text)

    @staticmethod
    def jsonschema(f: Callable) -> Dict[str, Any]:
        """
        Generate a JSON schema for the input parameters of the given function.

        Parameters:
            f (FunctionType): The function for which to generate the JSON schema.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - `name` (str): The function name.
                - `description` (str): The function docstring.
                - `parameters` (dict): The schema of input parameters.
        """
        kw = {n: (o.annotation, ... if o.default == Parameter.empty else o.default)
              for n, o in inspect.signature(f).parameters.items()}
        s = create_model(f'Input for `{f.__name__}`', **kw).model_json_schema()
        return dict(name=f.__name__, description=f.__doc__, parameters=s)