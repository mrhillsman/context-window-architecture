from ollama import Client, ChatResponse
from pyprojroot import here
import yaml
from box import Box


with open(here('.config.yml'), 'r') as file:
    config = Box(yaml.safe_load(file))


class OllamaManager:
    """Manages persistent Ollama client with tool/function support"""

    def __init__(self, host, model, options, tools=None):
        self.client = Client(host=host)
        self.model = model
        self.options = options
        self.tools = tools or []  # Default tools available for all chats

    def chat(self, messages, tools=None, tool_choice=None) -> ChatResponse:
        """Chat with optional tool support"""
        # Build request parameters
        params = {
            'model': self.model,
            'messages': messages,
            'options': self.options
        }

        # Use provided tools or default tools
        if tools or self.tools:
            params['tools'] = tools or self.tools

        # Add tool choice if specified
        if tool_choice:
            params['tool_choice'] = tool_choice

        response = self.client.chat(**params)
        return response

    def chat_stream(self, messages, tools=None):
        """Stream chat responses with tool support"""
        params = {
            'model': self.model,
            'messages': messages,
            'options': self.options,
            'stream': True
        }

        if tools or self.tools:
            params['tools'] = tools or self.tools

        return self.client.chat(**params)

    def set_tools(self, tools):
        """Update default tools"""
        self.tools = tools