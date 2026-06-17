import requests
import json
import re
from typing import List, Optional, Dict, Any

class OllamaGenerator:
    """Handles interactions with Ollama API for generating responses"""

    SYSTEM_PROMPT = """You are an AI assistant for AI/ML course materials. \
When course content is provided, answer ONLY from that content. \
Be concise, direct, and educational. \
Do not mention "based on the content" or "according to the course" — just answer. \
If the provided content does not contain the answer, say so briefly."""

    def __init__(self, api_url: str, model: str):
        """
        Initialize Ollama generator.

        Args:
            api_url: Ollama API URL (default: http://localhost:11434)
            model: Model name (default: llama2)
        """
        self.api_url = api_url.rstrip('/')
        self.model = model
        self.chat_endpoint = f"{self.api_url}/api/chat"

        # Verify Ollama connection on init
        self._verify_connection()

    def _verify_connection(self):
        """Verify Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=2)
            if response.status_code != 200:
                raise ConnectionError(f"Ollama returned status {response.status_code}")
            print(f"[OK] Connected to Ollama at {self.api_url}")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.api_url}. "
                f"Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            raise ConnectionError(f"Ollama connection error: {e}")

    def _extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract tool call JSON from response text.
        Looks for JSON object matching tool call pattern.

        Args:
            text: Response text potentially containing tool JSON

        Returns:
            Tool call dict or None if not found
        """
        # Match JSON object at start of response (for first tool call)
        json_pattern = r'^\s*\{[^{}]*"tool"[^{}]*\}'
        match = re.search(json_pattern, text, re.MULTILINE | re.DOTALL)

        if match:
            try:
                tool_json = json.loads(match.group())
                if 'tool' in tool_json and 'args' in tool_json:
                    return tool_json
            except json.JSONDecodeError:
                pass

        return None

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None) -> str:
        """
        Generate AI response with optional conversation context.

        Args:
            query: User query (may include retrieved course context)
            conversation_history: Previous conversation formatted as "User: msg\nAssistant: msg"

        Returns:
            Generated response text
        """
        messages = []

        if conversation_history:
            messages.append({
                "role": "user",
                "content": f"Previous conversation:\n{conversation_history}\n\nNew question:"
            })

        messages.append({"role": "user", "content": query})

        return self._call_ollama(messages)

    def _call_ollama(self, messages: List[Dict[str, str]]) -> str:
        """
        Call Ollama API with messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Response text from Ollama
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "system": self.SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 800,  # Similar to Claude's max_tokens
                }
            }

            response = requests.post(
                self.chat_endpoint,
                json=payload,
                timeout=180  # Allow longer timeout for Ollama processing
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code}")

            result = response.json()
            return result.get('message', {}).get('content', '').strip()

        except requests.exceptions.Timeout:
            raise Exception("Ollama request timed out. Model may be still loading.")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to Ollama at {self.api_url}. Is it running?")
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}")
