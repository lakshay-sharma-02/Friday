"""Timing infrastructure for performance profiling."""

import time
from typing import Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class TimingStats:
    """Rolling statistics for a timed operation."""
    name: str
    samples: deque = field(default_factory=lambda: deque(maxlen=100))

    def record(self, duration: float):
        """Record a timing sample."""
        self.samples.append(duration)

    def average(self) -> Optional[float]:
        """Get average duration."""
        if not self.samples:
            return None
        return sum(self.samples) / len(self.samples)

    def percentile(self, p: int) -> Optional[float]:
        """Get percentile duration (e.g., p=95 for p95)."""
        if not self.samples:
            return None
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * (p / 100.0))
        return sorted_samples[min(idx, len(sorted_samples) - 1)]


class PerformanceProfiler:
    """Global performance profiler for Friday subsystems."""

    def __init__(self):
        self.stats = {
            "routing": TimingStats("routing"),
            "memory_search": TimingStats("memory_search"),
            "planning": TimingStats("planning"),
            "execution": TimingStats("execution"),
            "generation": TimingStats("generation"),
            "total": TimingStats("total"),
        }

    def record(self, operation: str, duration: float):
        """Record timing for an operation."""
        if operation in self.stats:
            self.stats[operation].record(duration)

    def summary(self) -> dict:
        """Get summary statistics."""
        result = {}
        for name, stat in self.stats.items():
            avg = stat.average()
            p95 = stat.percentile(95)
            result[name] = {
                "avg_ms": round(avg * 1000, 1) if avg else None,
                "p95_ms": round(p95 * 1000, 1) if p95 else None,
                "samples": len(stat.samples),
            }
        return result


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance."""
    return _profiler


class Timer:
    """Context manager for timing operations."""

    def __init__(self, operation: str):
        self.operation = operation
        self.start = None
        self.duration = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.duration = time.perf_counter() - self.start
        get_profiler().record(self.operation, self.duration)
