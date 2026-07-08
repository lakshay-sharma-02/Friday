"""Deterministic tests for Phase 6F planner tool selection."""

import pytest
import asyncio
from agents.planner import create_plan
from core.world import WorldState
from core.health import HealthStatus, HealthLevel
from core.events import EventLog

@pytest.fixture
def mock_world():
    world = WorldState.empty(cwd="/test")
    world.workspace.is_git_repo = True
    return world

@pytest.fixture
def mock_health():
    return HealthStatus(
        level=HealthLevel.HEALTHY,
        reasons=[],
        cpu_percent=10.0,
        ram_percent=20.0,
        disk_percent=30.0,
        battery_percent=100.0,
        internet_reachable=True
    )

@pytest.fixture
def events():
    return EventLog()

@pytest.mark.asyncio
@pytest.mark.parametrize("task,expected_tool", [
    ("Read README.md", "read_file"),
    ("Search TODO", "search_files"),
    ("git status", "git_status"),
    ("Download file from http://example.com/data.zip to ./data.zip", "download_file"),
    ("Run cargo build", "shell"),
    ("Analyze data.csv to find the average", "python"),
    ("Transform JSON string '{\"a\": 1}' into a Python dictionary", "python"),
])
async def test_planner_tool_selection(task, expected_tool, mock_world, mock_health, events):
    plan, lesson = await create_plan(task, mock_world, mock_health, events.recent(10), "")
    
    assert len(plan) > 0, f"Plan was empty for task: '{task}'"
    tool_names = [step.get("tool") for step in plan]
    assert expected_tool in tool_names, f"For task '{task}', expected '{expected_tool}' in plan tools: {tool_names}"
