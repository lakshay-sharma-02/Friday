"""Planner cache for reusing deterministic plans."""

import hashlib
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone


class PlannerCache:
    """Cache deterministic plans to avoid redundant planner invocations."""

    def __init__(self, cache_dir: str = ".friday_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.plan_cache = self.cache_dir / "plans.json"
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load cache from disk."""
        if self.plan_cache.exists():
            try:
                with open(self.plan_cache, "r") as f:
                    return json.load(f)
            except Exception as e:
                from core.output_mode import log_debug
                log_debug(f"[cache] failed to load plan cache: {e}")
        return {"plans": {}, "version": 1}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.plan_cache, "w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            from core.output_mode import log_debug
            log_debug(f"[cache] failed to save plan cache: {e}")

    def _compute_key(self, request: str, context: dict) -> str:
        """Compute cache key from request and relevant context."""
        # Include request text and relevant context that affects planning
        key_data = {
            "request": request.strip().lower(),
            "tool_schema_version": context.get("tool_schema_version", "v1"),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, request: str, context: dict) -> Optional[list]:
        """Retrieve cached plan if available and valid.

        Returns None if:
        - No cached plan exists
        - Cached plan is expired
        - Request is non-deterministic
        """
        # Skip caching for time-sensitive or environment-dependent requests
        if self._is_non_deterministic(request):
            return None

        cache_key = self._compute_key(request, context)
        entry = self._cache["plans"].get(cache_key)

        if not entry:
            return None

        # Check expiration (24 hour TTL)
        cached_at = datetime.fromisoformat(entry["cached_at"])
        age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
        if age_hours > 24:
            from core.output_mode import log_debug
            log_debug(f"[cache] plan expired (age: {age_hours:.1f}h)")
            return None

        from core.output_mode import log_debug
        log_debug(f"[cache] hit for request: {request[:50]}")
        return entry["plan"]

    def put(self, request: str, context: dict, plan: list):
        """Cache a deterministic plan."""
        if self._is_non_deterministic(request):
            return

        cache_key = self._compute_key(request, context)
        self._cache["plans"][cache_key] = {
            "plan": plan,
            "request": request[:100],  # Store truncated request for debugging
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_cache()

        from core.output_mode import log_debug
        log_debug(f"[cache] stored plan for: {request[:50]}")

    def _is_non_deterministic(self, request: str) -> bool:
        """Check if request is non-deterministic (time/network/environment dependent)."""
        request_lower = request.lower()

        # Time-sensitive keywords
        time_keywords = [
            "time", "date", "now", "today", "yesterday", "tomorrow",
            "current", "latest", "recent", "ago"
        ]

        # Network-dependent keywords
        network_keywords = [
            "fetch", "download", "http", "https", "api", "curl", "wget"
        ]

        # Environment-dependent keywords
        env_keywords = [
            "status", "running", "active", "process", "memory", "cpu"
        ]

        non_deterministic_keywords = time_keywords + network_keywords + env_keywords

        return any(keyword in request_lower for keyword in non_deterministic_keywords)

    def invalidate_all(self):
        """Invalidate entire cache (e.g., on workspace change)."""
        self._cache = {"plans": {}, "version": 1}
        self._save_cache()
        from core.output_mode import log_debug
        log_debug("[cache] invalidated all plans")

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "total_plans": len(self._cache["plans"]),
            "cache_file": str(self.plan_cache),
        }


# Global cache instance
_planner_cache = None


def get_planner_cache() -> PlannerCache:
    """Get or create the global planner cache instance."""
    global _planner_cache
    if _planner_cache is None:
        _planner_cache = PlannerCache()
    return _planner_cache
