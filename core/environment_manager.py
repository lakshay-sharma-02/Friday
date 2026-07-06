"""Environment manager - orchestrates observers with caching."""

import asyncio
from datetime import datetime, timedelta
from core.environment import EnvironmentState
from observers import workspace, network, computer, developer, os as os_observer


_cache = {
    "computer": None,
    "developer": None,
    "os": None,
}

CACHE_TTL_MINUTES = 5


def _is_cache_valid(cache_entry: dict | None) -> bool:
    """Check if a cache entry is still valid."""
    if cache_entry is None:
        return False

    cached_at = cache_entry.get("cached_at")
    if cached_at is None:
        return False

    age = datetime.now() - cached_at
    return age < timedelta(minutes=CACHE_TTL_MINUTES)


async def inspect_environment(cwd: str = ".") -> EnvironmentState:
    """Inspect environment state with caching for static data.

    Args:
        cwd: Working directory to inspect

    Returns:
        EnvironmentState with all observer data
    """
    tasks = []

    tasks.append(workspace.inspect(cwd))
    tasks.append(network.inspect(cwd))

    if _is_cache_valid(_cache["computer"]):
        computer_data = _cache["computer"]["data"]
    else:
        computer_task = computer.inspect(cwd)
        tasks.append(computer_task)
        computer_data = None

    if _is_cache_valid(_cache["developer"]):
        developer_data = _cache["developer"]["data"]
    else:
        developer_task = developer.inspect(cwd)
        tasks.append(developer_task)
        developer_data = None

    if _is_cache_valid(_cache["os"]):
        os_data = _cache["os"]["data"]
    else:
        os_task = os_observer.inspect(cwd)
        tasks.append(os_task)
        os_data = None

    results = await asyncio.gather(*tasks)

    workspace_data = results[0]
    network_data = results[1]
    result_index = 2

    if computer_data is None:
        computer_data = results[result_index]
        result_index += 1
        _cache["computer"] = {
            "data": computer_data,
            "cached_at": datetime.now(),
        }

    if developer_data is None:
        developer_data = results[result_index]
        result_index += 1
        _cache["developer"] = {
            "data": developer_data,
            "cached_at": datetime.now(),
        }

    if os_data is None:
        os_data = results[result_index]
        result_index += 1
        _cache["os"] = {
            "data": os_data,
            "cached_at": datetime.now(),
        }

    return EnvironmentState(
        cwd=cwd,
        workspace=workspace_data,
        computer=computer_data,
        network=network_data,
        developer=developer_data,
        operating_system=os_data,
        observed_at=datetime.now(),
    )
