"""Operation taxonomy for capability system.

Phase 10.5: Distinguishes WHAT the user wants to do, not just WHO owns it.
"""

from enum import Enum


class Operation(Enum):
    """User intent operations - what the user wants to DO with a capability."""

    # Read operations (no execution, no modification)
    READ = "read"                    # "show RAM", "current project"
    LOOKUP = "lookup"                # "where is X", "find Y"
    INSPECT = "inspect"              # "check status", "view logs"

    # Analysis operations (read + synthesis)
    EXPLAIN = "explain"              # "explain ownership", "what does this do"
    SUMMARIZE = "summarize"          # "summarize project", "overview of README"
    REVIEW = "review"                # "review repository", "audit code"
    COMPARE = "compare"              # "compare approaches", "diff files"
    ANALYZE = "analyze"              # "analyze performance", "why is this slow"

    # Query operations (may need evidence collection)
    SEARCH = "search"                # "search for X", "grep pattern"

    # Planning operations (advice, no execution)
    PLAN = "plan"                    # "plan migration", "design approach"
    ADVISE = "advise"                # "how should I", "what command", "best practice"

    # Memory operations
    REMEMBER = "remember"            # "remember this", "teach you"
    RECALL = "recall"                # "what did I teach", "do you remember"
    REFLECT = "reflect"              # "what went wrong", "lessons learned"

    # Execution operations (requires explicit authorization)
    EXECUTE = "execute"              # "run tests", "install package", "commit changes"
    MODIFY = "modify"                # "create file", "edit code", "rename function"


def is_read_only(operation: Operation) -> bool:
    """Check if operation is read-only (never executes or modifies)."""
    return operation in {
        Operation.READ,
        Operation.LOOKUP,
        Operation.INSPECT,
        Operation.EXPLAIN,
        Operation.SUMMARIZE,
        Operation.REVIEW,
        Operation.COMPARE,
        Operation.ANALYZE,
        Operation.RECALL,
        Operation.REFLECT,
    }


def requires_execution(operation: Operation) -> bool:
    """Check if operation requires actual execution."""
    return operation in {
        Operation.EXECUTE,
        Operation.MODIFY,
        Operation.SEARCH,  # May require search_files tool
    }


def requires_planning(operation: Operation) -> bool:
    """Check if operation requires planner (multi-step work)."""
    return operation in {
        Operation.EXECUTE,
        Operation.MODIFY,
        Operation.PLAN,
    }


def requires_llm_synthesis(operation: Operation) -> bool:
    """Check if operation requires LLM to synthesize answer."""
    return operation in {
        Operation.EXPLAIN,
        Operation.SUMMARIZE,
        Operation.REVIEW,
        Operation.COMPARE,
        Operation.ANALYZE,
        Operation.ADVISE,
        Operation.PLAN,
        Operation.REFLECT,
    }
