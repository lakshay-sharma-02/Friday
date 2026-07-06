import pytest
from core.router import route_intent

def test_router_chat():
    assert route_intent("Hello") == "chat"
    assert route_intent("How are you?") == "chat"
    assert route_intent("Explain recursion.") == "chat"
    assert route_intent("Who created Python?") == "chat"
    assert route_intent("What is Python?") == "chat"

def test_router_task():
    assert route_intent("Read README.md") == "task"
    assert route_intent("Open CLAUDE.md") == "task"
    assert route_intent("Search for TODO") == "task"
    assert route_intent("Run tests") == "task"
    assert route_intent("Run pytest") == "task"
    assert route_intent("List files") == "task"
    assert route_intent("Replace text") == "task"
    assert route_intent("Commit changes") == "task"

def test_router_hybrid():
    assert route_intent("Explain what is inside README.md") == "hybrid"
    assert route_intent("Summarize LICENSE") == "hybrid"
    assert route_intent("Read config.json and explain it") == "hybrid"
    assert route_intent("What changed in main.py?") == "hybrid"
    
def test_router_compatibility():
    assert route_intent("task: read README.md") == "task"

def test_router_ambiguous_task_explain():
    # When both an explain verb and a task verb are present, but NO file/workspace indicator,
    # it safely degrades to chat to prevent running tools randomly on vague input.
    assert route_intent("explain how to build the release") == "chat"
    assert route_intent("why did git commit fail") == "chat"
    assert route_intent("how do I fix the build") == "chat"
