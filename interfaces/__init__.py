"""Interfaces: entry points into Friday (CLI, future: HTTP, gRPC, etc)."""

from .cli import run_cli

__all__ = ["run_cli"]
