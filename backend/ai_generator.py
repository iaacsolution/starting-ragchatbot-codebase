import anthropic
from typing import List, Optional, Dict, Any, AsyncIterator


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to 2 sequential searches per query** — use a second search only when the first result is insufficient or a comparison requires separate lookups (e.g. cross-course comparisons, multi-part questions)
- Synthesize search results into accurate, fact-based responses
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

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    async def generate_stream(
        self, query: str, conversation_history: str = None
    ) -> AsyncIterator[str]:
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }
        async with self.async_client.messages.stream(**api_params) as stream:
            async for text in stream.text_stream:
                yield text

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager
    ) -> str:
        """Execute tool calls in a loop, up to MAX_TOOL_ROUNDS sequential rounds."""
        messages = base_params["messages"].copy()
        messages.append({"role": "assistant", "content": initial_response.content})
        tools = base_params.get("tools")
        current_response = initial_response

        for round_idx in range(self.MAX_TOOL_ROUNDS):
            tool_results = []
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Tool error: {e}"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            if not tool_results:
                return current_response.content[0].text

            messages.append({"role": "user", "content": tool_results})

            # Allow another tool round only if below the cap
            allow_more = (round_idx < self.MAX_TOOL_ROUNDS - 1) and tools
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }
            if allow_more:
                next_params["tools"] = tools
                next_params["tool_choice"] = {"type": "auto"}

            current_response = self.client.messages.create(**next_params)

            if current_response.stop_reason != "tool_use":
                return current_response.content[0].text

            messages.append({"role": "assistant", "content": current_response.content})

        return current_response.content[0].text
