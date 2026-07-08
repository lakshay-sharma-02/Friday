"""Output mode control for Friday - manages log verbosity levels."""

import os
import sys
from enum import Enum


class OutputMode(Enum):
    """Output verbosity levels."""
    NORMAL = "normal"    # Only assistant responses
    VERBOSE = "verbose"  # + subsystem timings
    DEBUG = "debug"      # Everything


_current_mode = OutputMode.NORMAL


def set_mode(mode: OutputMode):
    """Set the global output mode."""
    global _current_mode
    _current_mode = mode


def get_mode() -> OutputMode:
    """Get the current output mode."""
    return _current_mode


def should_show_debug() -> bool:
    """Check if debug logs should be shown."""
    return _current_mode == OutputMode.DEBUG


def should_show_verbose() -> bool:
    """Check if verbose logs should be shown."""
    return _current_mode in (OutputMode.VERBOSE, OutputMode.DEBUG)


def log_debug(message: str):
    """Log a debug message (only in DEBUG mode)."""
    if should_show_debug():
        print(message, file=sys.stderr)


def log_verbose(message: str):
    """Log a verbose message (in VERBOSE and DEBUG modes)."""
    if should_show_verbose():
        print(message, file=sys.stderr)


def log_info(message: str):
    """Log an info message (always shown)."""
    print(message, file=sys.stderr)


# Initialize from environment variable
_env_mode = os.getenv("FRIDAY_OUTPUT_MODE", "normal").lower()
if _env_mode == "debug":
    _current_mode = OutputMode.DEBUG
elif _env_mode == "verbose":
    _current_mode = OutputMode.VERBOSE
else:
    _current_mode = OutputMode.NORMAL
