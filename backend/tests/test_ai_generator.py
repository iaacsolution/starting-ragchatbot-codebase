from unittest.mock import MagicMock
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ai_generator import AIGenerator


@pytest.fixture
def generator():
    gen = AIGenerator.__new__(AIGenerator)
    gen.model = "claude-test"
    gen.base_params = {"model": "claude-test", "temperature": 0, "max_tokens": 800}
    gen.client = MagicMock()
    gen.async_client = MagicMock()
    return gen


def _text_response(text: str):
    response = MagicMock()
    response.stop_reason = "end_turn"
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


def _tool_response(calls: list):
    response = MagicMock()
    response.stop_reason = "tool_use"
    blocks = []
    for name, inputs, tool_id in calls:
        block = MagicMock()
        block.type = "tool_use"
        block.name = name
        block.input = inputs
        block.id = tool_id
        blocks.append(block)
    response.content = blocks
    return response


def test_direct_response_no_tools(generator):
    generator.client.messages.create.return_value = _text_response("Direct answer")
    result = generator.generate_response("What is RAG?")
    assert result == "Direct answer"
    assert generator.client.messages.create.call_count == 1


def test_single_tool_round(generator):
    tool_mgr = MagicMock()
    tool_mgr.execute_tool.return_value = "Search result: RAG explanation"
    generator.client.messages.create.side_effect = [
        _tool_response([("search", {"query": "RAG"}, "t1")]),
        _text_response("RAG stands for Retrieval Augmented Generation"),
    ]

    result = generator.generate_response(
        "What is RAG?", tools=[{"name": "search"}], tool_manager=tool_mgr
    )

    assert result == "RAG stands for Retrieval Augmented Generation"
    assert generator.client.messages.create.call_count == 2
    tool_mgr.execute_tool.assert_called_once_with("search", query="RAG")


def test_two_sequential_tool_rounds(generator):
    tool_mgr = MagicMock()
    tool_mgr.execute_tool.side_effect = ["Result course X", "Result comparison"]
    generator.client.messages.create.side_effect = [
        _tool_response([("search", {"query": "course X"}, "t1")]),
        _tool_response([("search", {"query": "same topic"}, "t2")]),
        _text_response("Comparison answer"),
    ]

    result = generator.generate_response(
        "Compare courses", tools=[{"name": "search"}], tool_manager=tool_mgr
    )

    assert result == "Comparison answer"
    assert generator.client.messages.create.call_count == 3
    assert tool_mgr.execute_tool.call_count == 2


def test_last_round_has_no_tools_in_api_call(generator):
    tool_mgr = MagicMock()
    tool_mgr.execute_tool.return_value = "result"
    generator.client.messages.create.side_effect = [
        _tool_response([("search", {"query": "q1"}, "t1")]),
        _tool_response([("search", {"query": "q2"}, "t2")]),
        _text_response("Final"),
    ]

    generator.generate_response(
        "query", tools=[{"name": "search"}], tool_manager=tool_mgr
    )

    last_kwargs = generator.client.messages.create.call_args_list[-1][1]
    assert "tools" not in last_kwargs


def test_tool_error_handled_gracefully(generator):
    tool_mgr = MagicMock()
    tool_mgr.execute_tool.side_effect = RuntimeError("DB error")
    generator.client.messages.create.side_effect = [
        _tool_response([("search", {"query": "q"}, "t1")]),
        _text_response("Could not find results"),
    ]

    result = generator.generate_response(
        "query", tools=[{"name": "search"}], tool_manager=tool_mgr
    )
    assert result == "Could not find results"
