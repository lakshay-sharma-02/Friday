"""Evidence Types - minimal set for Evidence Planner experiment.

EXPERIMENT ONLY - Can be removed if experiment fails.
"""

from enum import Enum


class EvidenceType(Enum):
    """Types of evidence that can be collected to answer queries."""

    USER_PROFILE = "user_profile"
    USER_PREFERENCES = "user_preferences"
    SYSTEM_STATE = "system_state"
    WORKSPACE = "workspace"
    REPOSITORY = "repository"
    FILESYSTEM = "filesystem"
    GIT = "git"
    PROJECT_METADATA = "project_metadata"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
