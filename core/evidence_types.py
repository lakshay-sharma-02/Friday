"""Evidence Types - minimal set for Evidence Planner experiment.

This is an EXPERIMENTAL module for testing evidence-based routing.
Do not use in production code yet.
"""

from enum import Enum


class EvidenceType(Enum):
    """Evidence types that queries can require.

    These are stable architectural components, not query-specific intents.
    """

    # User information
    USER_PROFILE = "user_profile"  # Identity, name, role
    USER_PREFERENCES = "user_preferences"  # Choices, settings, taught preferences

    # System state
    SYSTEM_STATE = "system_state"  # RAM, CPU, disk, battery, network

    # Workspace/project
    WORKSPACE = "workspace"  # Current project context, type, languages
    PROJECT_METADATA = "project_metadata"  # Project structure, config

    # Version control
    GIT = "git"  # Repository status, history, branches

    # Repository analysis
    REPOSITORY = "repository"  # Full repository structure and patterns
    ARCHITECTURE = "architecture"  # System architecture and design

    # Filesystem
    FILESYSTEM = "filesystem"  # Files, directories, content

    # Documentation
    DOCUMENTATION = "documentation"  # README, docs, comments
