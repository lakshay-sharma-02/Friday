"""Plan validation, repair, risk analysis, and execution guards.

Sits between the Planner and Executor. Everything here is deterministic and uses
the Tool Registry as the single source of truth. No LLM calls.
"""

from typing import Any

from tools.registry import TOOL_REGISTRY

# Risk tiers for planned tools. LOW/MEDIUM/HIGH per Phase 6D spec.
RISK_LOW = ["read_file", "list_directory", "git_status", "search_files", "git_diff", "git_log"]
RISK_MEDIUM = ["write_file", "replace_in_file", "git_add", "git_commit", "git_branch", "git_checkout", "git_restore", "diff_files"]
RISK_HIGH = ["shell", "python", "start_shell", "start_python", "process", "git_reset", "git_clone", "delete_file"]


def tool_risk(tool_name: str) -> str:
    """Return LOW/MEDIUM/HIGH risk level for a tool."""
    if tool_name in RISK_LOW:
        return "LOW"
    if tool_name in RISK_MEDIUM:
        return "MEDIUM"
    if tool_name in RISK_HIGH:
        return "HIGH"
    # Unmapped tools default to MEDIUM (conservative; not silent-LOW).
    return "MEDIUM"


def _type_ok(value: Any, expected: str) -> bool:
    """Check a value against an arg's declared type string."""
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "list":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True  # unknown type strings are not enforced


def _repair_step(step: dict) -> tuple[dict | None, list[str], list[str]]:
    """Deterministically repair a step.

    Returns (repaired_step, repairs_made, hard_errors).
    Repairs never guess user intent; only safe normalizations are applied.
    """
    repairs = []
    errors = []

    if not isinstance(step, dict):
        return None, repairs, [f"step is {type(step).__name__}, expected object"]

    fixed = dict(step)

    # 1. tool field must exist and be a string.
    tool = fixed.get("tool")
    if not isinstance(tool, str):
        return None, repairs, ["'tool' is missing or not a string"]
    if tool not in TOOL_REGISTRY:
        # Case-insensitive match against known tools.
        lowered = {t.lower(): t for t in TOOL_REGISTRY}
        if tool.lower() in lowered:
            fixed["tool"] = lowered[tool.lower()]
            repairs.append(f"normalized tool name '{tool}' -> '{fixed['tool']}'")
        else:
            return None, repairs, [f"unknown tool '{tool}'"]

    tool_name = fixed["tool"]
    spec = TOOL_REGISTRY[tool_name]

    # 2. args must be a dict (default to empty).
    args = fixed.get("args")
    if args is None:
        args = {}
        repairs.append("added missing 'args' object")
    elif not isinstance(args, dict):
        return None, repairs, ["'args' is not an object"]

    # 3. Drop unknown top-level fields beyond tool/args/description (unknown-only field).
    allowed = {"tool", "args", "description"}
    for k in list(fixed.keys()):
        if k not in allowed:
            del fixed[k]
            repairs.append(f"removed unknown field '{k}'")

    # 4. Drop unknown arg keys (extra unused fields).
    for k in list(args.keys()):
        if k not in spec["args"]:
            del args[k]
            repairs.append(f"removed unknown argument '{k}' from '{tool_name}'")

    # 5. Fill missing optional args have no default to inject (only required enforced).
    # 6. Required args present?
    for arg_name, arg_spec in spec["args"].items():
        if arg_spec.get("required") and arg_name not in args:
            errors.append(f"missing required argument '{arg_name}' for '{tool_name}'")

    # 7. Type check present args.
    for arg_name, arg_spec in spec["args"].items():
        if arg_name in args:
            expected = arg_spec.get("type")
            if expected and not _type_ok(args[arg_name], expected):
                # Enum-style 'string' with choices not modelled; only type-level reject.
                errors.append(
                    f"argument '{arg_name}' expected {expected}, got "
                    f"{type(args[arg_name]).__name__}"
                )

    if errors:
        return None, repairs, errors

    fixed["args"] = args
    if "description" not in fixed:
        fixed["description"] = f"{tool_name} step"
        repairs.append("added default description")
    fixed["risk_level"] = tool_risk(tool_name)
    return fixed, repairs, []


def validate_step(step: dict, step_index: int) -> tuple[bool, str]:
    """Strict validation of a single step (no repair). Returns (ok, error)."""
    repaired, repairs, errors = _repair_step(step)
    if repaired is None:
        return False, f"step {step_index}: " + "; ".join(errors)
    return True, ""


def validate_and_prepare_plan(plan: Any) -> dict:
    """Validate, repair, risk-tag, and guard a whole plan.

    Returns a structured dict:
        {
            "accepted": bool,
            "steps": [repaired step dicts] | [],   # only when accepted
            "risk_level": "LOW"|"MEDIUM"|"HIGH"|"NONE",
            "errors": [ {step, error} ... ],        # per-step hard errors
            "repairs": [ {step, repairs} ... ],     # per-step repairs applied
            "message": str,                          # human-readable summary
        }
    """
    if not isinstance(plan, list):
        return {
            "accepted": False,
            "steps": [],
            "risk_level": "NONE",
            "errors": [{"step": None, "error": f"plan must be a JSON array, got {type(plan).__name__}"}],
            "repairs": [],
            "message": "Plan is not a JSON array.",
        }

    if not plan:
        return {
            "accepted": False,
            "steps": [],
            "risk_level": "NONE",
            "errors": [{"step": None, "error": "plan is empty"}],
            "repairs": [],
            "message": "Plan contains no steps.",
        }

    prepared = []
    errors = []
    repairs_log = []
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "NONE": -1}
    max_risk = "NONE"

    for i, raw_step in enumerate(plan):
        repaired, step_repairs, step_errors = _repair_step(raw_step)
        if step_errors:
            for e in step_errors:
                errors.append({"step": i, "error": e})
        if step_repairs:
            repairs_log.append({"step": i, "repairs": step_repairs})
        if repaired is None:
            continue
        prepared.append(repaired)
        if risk_order.get(repaired.get("risk_level", "NONE"), 1) > risk_order.get(max_risk, -1):
            max_risk = repaired["risk_level"]

    if errors and not prepared:
        return {
            "accepted": False,
            "steps": [],
            "risk_level": "NONE",
            "errors": errors,
            "repairs": repairs_log,
            "message": "Plan rejected: no valid steps after validation/repair.",
        }

    if errors and prepared:
        # Mixed: some steps repaired/accepted, others fatal. Reject the whole plan
        # rather than partially executing an unsafe plan.
        return {
            "accepted": False,
            "steps": [],
            "risk_level": max_risk,
            "errors": errors,
            "repairs": repairs_log,
            "message": "Plan rejected: contains unrecoverable invalid steps.",
        }

    return {
        "accepted": True,
        "steps": prepared,
        "risk_level": max_risk,
        "errors": [],
        "repairs": repairs_log,
        "message": f"Plan accepted ({len(prepared)} step(s), risk {max_risk}).",
    }


def verify_execution_guards(step: dict, intent: Any = None, world: Any = None) -> tuple[bool, str]:
    """Verify execution guards before a step runs.
    
    Checks:
    - tool exists
    - arguments validated
    - permissions satisfied
    - workspace available
    - execution prerequisites met
    """
    import os
    
    # 1 & 2. Tool exists & args validated
    ok, err = validate_step(step, 0)
    if not ok:
        return False, f"Guard failed: {err}"
        
    tool_name = step["tool"]
    args = step.get("args", {})
    
    # 3. Permissions satisfied
    from core.permissions import check_permission
    if not check_permission(tool_name, args, intent):
        return False, f"Guard failed: Permission denied for tool '{tool_name}'."
        
    # 4. Workspace available
    if world and hasattr(world, "workspace") and world.workspace:
        cwd = args.get("cwd") or world.workspace.cwd
        if cwd and not os.path.exists(cwd):
            return False, f"Guard failed: Workspace directory '{cwd}' does not exist."
            
    # 5. Execution prerequisites met
    if tool_name.startswith("git_") and tool_name != "git_clone":
        if world and hasattr(world, "workspace") and world.workspace:
            if not world.workspace.is_git_repo:
                return False, f"Guard failed: Tool '{tool_name}' requires a git repository."
                
    return True, ""
