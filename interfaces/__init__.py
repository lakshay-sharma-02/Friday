"""Interfaces: entry points into Friday (CLI, future: HTTP, gRPC, etc)."""

from .cli import run_cli
from .oneshot import run_oneshot

__all__ = ["run_cli", "run_oneshot"]
