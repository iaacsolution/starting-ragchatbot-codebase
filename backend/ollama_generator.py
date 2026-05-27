import requests
import json
import re
from typing import List, Optional, Dict, Any

class OllamaGenerator:
    """Handles interactions with Ollama API for generating responses"""

    # System prompt for Ollama - includes tool invocation format
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to a search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **One search per query maximum**
- When you need to search, respond FIRST with a JSON object on its own line:
  {"tool": "search_course_content", "args": {"query": "your search query", "course_name": null, "lesson_number": null}}
- After the tool executes and provides results, synthesize them into an accurate, fact-based response
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
  - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
  - Do not mention "based on the search results"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding

Provide only the direct answer to what was asked.
"""

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
            print(f"✓ Connected to Ollama at {self.api_url}")
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
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: User query
            conversation_history: Previous conversation (formatted as "User: msg\nAssistant: msg")
            tools: List of available tools (tool definitions)
            tool_manager: Manager to execute tools

        Returns:
            Generated response text
        """
        # Build messages
        messages = []

        # Add conversation history if provided
        if conversation_history:
            messages.append({
                "role": "user",
                "content": f"Previous conversation context:\n{conversation_history}\n\nNow, answer this new question:"
            })

        # Add current query
        messages.append({
            "role": "user",
            "content": query
        })

        # First API call - allow tool use detection
        response_text = self._call_ollama(messages)

        # Check if response contains tool call
        if tool_manager and tools:
            tool_call = self._extract_tool_call(response_text)

            if tool_call:
                # Tool was invoked - execute it
                tool_name = tool_call.get('tool')
                tool_args = tool_call.get('args', {})

                # Execute the tool
                try:
                    tool_result = tool_manager.execute_tool(tool_name, tool_args)

                    # Create a clean response without the JSON part
                    response_without_json = re.sub(
                        r'^\s*\{[^{}]*"tool"[^{}]*\}',
                        '',
                        response_text
                    ).strip()

                    # Continue conversation with tool results
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": f"Search results for your query:\n{tool_result}\n\nPlease provide the final answer based on these search results."
                    })

                    # Final API call without tools to get answer
                    final_response = self._call_ollama(messages)
                    return final_response

                except Exception as e:
                    # Tool execution failed - return error message
                    return f"I encountered an error while searching: {str(e)}. Please try a more specific question."

        return response_text

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
                timeout=60  # Allow longer timeout for Ollama processing
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
