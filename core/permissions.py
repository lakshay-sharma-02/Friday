"""Permission management for tool execution."""

import sys
import yaml

_PERMISSIONS_PATH = "config/permissions.yaml"
_PERMISSIONS = None


def _load_permissions():
    """Load permissions once at module import."""
    global _PERMISSIONS
    if _PERMISSIONS is None:
        try:
            with open(_PERMISSIONS_PATH) as f:
                _PERMISSIONS = yaml.safe_load(f)
        except Exception as e:
            print(f"[permissions] failed to load {_PERMISSIONS_PATH}: {e}", file=sys.stderr)
            _PERMISSIONS = {"tools": {}}
    return _PERMISSIONS


def get_tool_tier(tool_name: str) -> int:
    """Get permission tier for a tool.

    Returns:
        0: Execute immediately
        1: Prompt user for confirmation
        2: Treat like tier 1 for now
    """
    perms = _load_permissions()
    return perms.get("tools", {}).get(tool_name, 1)


def check_permission(tool_name: str, args: dict, intent: "Intent" = None) -> bool:
    """Check if tool execution should proceed.

    Args:
        tool_name: Name of tool to execute
        args: Tool arguments
        intent: Optional Intent to check permission_ceiling

    Returns:
        True if execution should proceed, False if user denied or ceiling blocks
    """
    tier = get_tool_tier(tool_name)

    # Check permission ceiling if intent provided
    if intent and hasattr(intent, 'permission_ceiling'):
        ceiling = int(intent.permission_ceiling)
        if tier > ceiling:
            print(
                f"[permissions] blocked: {tool_name} requires tier {tier} but "
                f"intent ceiling is {ceiling} (source={intent.source})",
                file=sys.stderr
            )
            return False

    if tier == 0:
        return True

    # Check if stdin is a terminal (interactive)
    if not sys.stdin.isatty():
        # Non-interactive mode: auto-approve tier 1 to avoid blocking
        from core.output_mode import log_debug
        log_debug(f"[permissions] auto-approving {tool_name} (non-interactive)")
        return True

    print(f"\n[Permission required]")
    print(f"Tool: {tool_name}")
    print(f"Arguments: {args}")
    response = input("Execute? (y/n): ").strip().lower()

    return response == "y"
