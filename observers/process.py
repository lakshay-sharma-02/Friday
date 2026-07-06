"""Process observer - tracks running child processes."""

import psutil
from core.world import ProcessInfo, ProcessState


async def inspect(tracked_pids: set[int] = None) -> ProcessState:
    """Inspect running processes.

    Args:
        tracked_pids: PIDs to specifically track. If None, only tracks Friday's children.

    Returns:
        ProcessState with current process information
    """
    state = ProcessState()

    if tracked_pids is None:
        tracked_pids = set()

    current_process = psutil.Process()

    # Track Friday's direct children
    try:
        children = current_process.children(recursive=False)
        for child in children:
            tracked_pids.add(child.pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    # Inspect each tracked process
    for pid in tracked_pids:
        try:
            proc = psutil.Process(pid)

            # Get process info
            with proc.oneshot():
                cmdline = proc.cmdline()
                command = " ".join(cmdline) if cmdline else proc.name()
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_info = proc.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                create_time = proc.create_time()
                status = proc.status()

                # Check if process has exited
                proc_status = "running" if status in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING] else status
                exit_code = None

                # Try to get exit code if process finished
                if status == psutil.STATUS_ZOMBIE:
                    try:
                        proc.wait(timeout=0)
                        exit_code = proc.returncode
                        proc_status = "finished"
                    except psutil.TimeoutExpired:
                        proc_status = "zombie"

                info = ProcessInfo(
                    pid=pid,
                    command=command[:200],  # Truncate long commands
                    started_at=create_time,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    status=proc_status,
                    exit_code=exit_code,
                )

                state.add_process(info)

        except psutil.NoSuchProcess:
            # Process no longer exists, mark as finished if we were tracking it
            pass
        except (psutil.AccessDenied, psutil.ZombieProcess):
            # Can't access process info, skip it
            pass

    return state
