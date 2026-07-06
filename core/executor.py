"""Plan validation and execution engine."""

import sys
import time
import asyncio
from tools.registry import TOOL_REGISTRY
from core.permissions import check_permission


def validate_step(step: dict, step_index: int) -> tuple[bool, str]:
    """Validate a single plan step.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(step, dict):
        return False, f"Step {step_index} is not a dict"

    tool = step.get("tool")
    if not tool:
        return False, f"Step {step_index} missing 'tool' field"

    if tool not in TOOL_REGISTRY:
        return False, f"Step {step_index} uses unknown tool '{tool}'"

    args = step.get("args")
    if not isinstance(args, dict):
        return False, f"Step {step_index} 'args' is not a dict"

    tool_spec = TOOL_REGISTRY[tool]
    for arg_name, arg_spec in tool_spec["args"].items():
        if arg_spec.get("required") and arg_name not in args:
            return False, f"Step {step_index} missing required arg '{arg_name}' for tool '{tool}'"

    return True, ""


def validate_plan(plan: list[dict]) -> list[dict]:
    """Validate plan and return only valid steps with warnings for invalid ones.

    Returns:
        List of valid steps
    """
    valid_steps = []

    for i, step in enumerate(plan):
        is_valid, error = validate_step(step, i)

        if is_valid:
            valid_steps.append(step)
        else:
            print(f"[executor] warning: {error}, skipping", file=sys.stderr)

    return valid_steps


async def execute_plan(plan: list[dict], intent=None) -> list[dict]:
    """Execute a validated plan and return execution log.

    Args:
        plan: List of validated steps to execute
        intent: Optional Intent to check permission_ceiling

    Returns:
        List of execution log entries
    """
    execution_log = []

    for step in plan:
        tool_name = step["tool"]
        args = step.get("args", {})
        description = step.get("description", "")

        print(f"\n[{tool_name}] {description}")

        if not check_permission(tool_name, args, intent):
            log_entry = {
                "tool": tool_name,
                "args": args,
                "started_at": time.time(),
                "ended_at": time.time(),
                "duration": 0.0,
                "output": "Blocked: exceeds permission ceiling or user denied",
                "exit_code": None,
                "success": False,
                "skipped": True,
            }
            execution_log.append(log_entry)
            print("[blocked]")
            continue

        handler = TOOL_REGISTRY[tool_name]["handler"]

        t0 = time.time()
        try:
            result = await asyncio.to_thread(handler, **args)
            t1 = time.time()

            log_entry = {
                "tool": tool_name,
                "args": args,
                "started_at": t0,
                "ended_at": t1,
                "duration": t1 - t0,
                "output": result.get("output", ""),
                "exit_code": result.get("exit_code"),
                "success": result.get("success", False),
            }

            execution_log.append(log_entry)

            print(result.get("output", ""))

            if not result.get("success"):
                print(f"[failed: exit_code={result.get('exit_code')}]", file=sys.stderr)

        except Exception as e:
            t1 = time.time()
            error_msg = f"Executor error: {str(e)}"

            log_entry = {
                "tool": tool_name,
                "args": args,
                "started_at": t0,
                "ended_at": t1,
                "duration": t1 - t0,
                "output": error_msg,
                "exit_code": None,
                "success": False,
            }

            execution_log.append(log_entry)
            print(error_msg, file=sys.stderr)

    return execution_log
