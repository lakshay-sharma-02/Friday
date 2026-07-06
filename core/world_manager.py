"""World manager - orchestrates observers and builds WorldState."""

import asyncio
import time
from datetime import datetime, timedelta
from core.world import (
    WorldState,
    WorkspaceState,
    ComputerState,
    NetworkState,
    DeveloperState,
    RuntimeState,
    ProcessState,
)
from observers import workspace, network, computer, developer, os as os_observer, process


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


def _build_workspace_state(data: dict, cwd: str) -> WorkspaceState:
    """Build WorkspaceState from observer dict."""
    git = data.get("git", {})
    return WorkspaceState(
        cwd=cwd,
        project_type=data.get("project_type"),
        languages=data.get("languages", []),
        build_system=data.get("build_system"),
        test_runner=data.get("test_runner"),
        package_manager=data.get("package_manager"),
        top_level_files=data.get("top_level_files", []),
        is_git_repo=git.get("is_repo", False),
        git_branch=git.get("branch"),
        git_clean=git.get("clean"),
        git_modified_files=git.get("modified_files", []),
    )


def _build_computer_state(data: dict) -> ComputerState:
    """Build ComputerState from observer dict."""
    disk = data.get("disk_usage", {})
    return ComputerState(
        os=data.get("os"),
        architecture=data.get("architecture"),
        hostname=data.get("hostname"),
        logical_cores=data.get("logical_cores"),
        ram_gb=data.get("ram_gb"),
        disk_total=disk.get("total"),
        disk_used=disk.get("used"),
        disk_available=disk.get("available"),
        disk_use_percent=disk.get("use_percent"),
        gpu=data.get("gpu"),
        battery_percent=data.get("battery"),
        python_version=data.get("python_version"),
        current_user=data.get("current_user"),
    )


def _build_network_state(data: dict) -> NetworkState:
    """Build NetworkState from observer dict."""
    return NetworkState(
        internet_reachable=data.get("internet_reachable", False),
        hostname=data.get("hostname"),
        local_ip=data.get("local_ip"),
        loopback_available=data.get("loopback_available", True),
        dns_available=data.get("dns_available", False),
        interfaces=data.get("interfaces", []),
    )


def _build_developer_state(data: dict) -> DeveloperState:
    """Build DeveloperState from observer dict."""
    return DeveloperState(tools=data)


async def observe_world(
    cwd: str = ".",
    runtime: RuntimeState = None,
    tracked_pids: set[int] = None,
    refresh_only: set[str] = None,
) -> WorldState:
    """Observe the world and build complete WorldState.

    Args:
        cwd: Working directory to observe
        runtime: RuntimeState to include (if None, creates empty)
        tracked_pids: PIDs to track in process observer
        refresh_only: If provided, only refresh these domains (workspace, network, processes)

    Returns:
        Complete WorldState
    """
    tasks = []

    # Determine what to refresh
    refresh_workspace = refresh_only is None or "workspace" in refresh_only
    refresh_network = refresh_only is None or "network" in refresh_only
    refresh_processes = refresh_only is None or "processes" in refresh_only
    refresh_static = refresh_only is None

    # Always refresh workspace and network if requested
    if refresh_workspace:
        tasks.append(workspace.inspect(cwd))
    else:
        tasks.append(None)

    if refresh_network:
        tasks.append(network.inspect(cwd))
    else:
        tasks.append(None)

    # Handle cached observers
    if refresh_static and _is_cache_valid(_cache["computer"]):
        computer_data = _cache["computer"]["data"]
        tasks.append(None)
    else:
        if refresh_static:
            tasks.append(computer.inspect(cwd))
        else:
            computer_data = _cache.get("computer", {}).get("data", {})
            tasks.append(None)

    if refresh_static and _is_cache_valid(_cache["developer"]):
        developer_data = _cache["developer"]["data"]
        tasks.append(None)
    else:
        if refresh_static:
            tasks.append(developer.inspect(cwd))
        else:
            developer_data = _cache.get("developer", {}).get("data", {})
            tasks.append(None)

    if refresh_static and _is_cache_valid(_cache["os"]):
        os_data = _cache["os"]["data"]
        tasks.append(None)
    else:
        if refresh_static:
            tasks.append(os_observer.inspect(cwd))
        else:
            os_data = _cache.get("os", {}).get("data", {})
            tasks.append(None)

    # Process observer
    if refresh_processes:
        tasks.append(process.inspect(tracked_pids))
    else:
        tasks.append(None)

    # Gather all tasks, filtering out None placeholders
    actual_tasks = [t for t in tasks if t is not None]
    results = await asyncio.gather(*actual_tasks) if actual_tasks else []

    # Reconstruct results with cached data
    result_index = 0
    final_results = []

    for task in tasks:
        if task is not None:
            final_results.append(results[result_index])
            result_index += 1
        else:
            final_results.append(None)

    workspace_data = final_results[0] if refresh_workspace else _cache.get("workspace_data", {})
    network_data = final_results[1] if refresh_network else _cache.get("network_data", {})

    # Handle computer data
    if final_results[2] is not None:
        computer_data = final_results[2]
        _cache["computer"] = {"data": computer_data, "cached_at": datetime.now()}
    elif not refresh_static:
        computer_data = _cache.get("computer", {}).get("data", {})

    # Handle developer data
    if final_results[3] is not None:
        developer_data = final_results[3]
        _cache["developer"] = {"data": developer_data, "cached_at": datetime.now()}
    elif not refresh_static:
        developer_data = _cache.get("developer", {}).get("data", {})

    # Handle OS data
    if final_results[4] is not None:
        os_data = final_results[4]
        _cache["os"] = {"data": os_data, "cached_at": datetime.now()}
    elif not refresh_static:
        os_data = _cache.get("os", {}).get("data", {})

    # Handle process data
    process_state = final_results[5] if refresh_processes else ProcessState()

    # Cache non-static data for partial refreshes
    if refresh_workspace:
        _cache["workspace_data"] = workspace_data
    if refresh_network:
        _cache["network_data"] = network_data

    # Build typed states
    workspace_state = _build_workspace_state(workspace_data, cwd)
    computer_state = _build_computer_state(computer_data)
    network_state = _build_network_state(network_data)
    developer_state = _build_developer_state(developer_data)

    # Use provided runtime or create empty
    if runtime is None:
        runtime = RuntimeState()

    # Update runtime elapsed time
    if runtime.task_start_time:
        runtime.update_elapsed(time.time())

    return WorldState(
        workspace=workspace_state,
        computer=computer_state,
        network=network_state,
        developer=developer_state,
        runtime=runtime,
        processes=process_state,
        observed_at=datetime.now(),
    )
