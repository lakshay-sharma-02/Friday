"""Engineering Reflection - identifies architectural improvements from execution."""

from dataclasses import dataclass
from typing import Optional
from core.run import PipelineRun
from core.world import WorldState


@dataclass
class EngineeringIssue:
    """An identified engineering improvement."""
    layer: str  # Which architectural layer has the issue
    reason: str  # What problem was observed
    impact: str  # HIGH, MEDIUM, LOW
    suggested_fix: str  # What should be done
    evidence: str  # Concrete data supporting this issue
    regression_required: bool  # Does this need a regression test


class EngineeringReflection:
    """Evaluates execution to identify architectural improvements."""

    def reflect(self, run: PipelineRun, world: WorldState, timings: dict) -> Optional[EngineeringIssue]:
        """Inspect execution and return engineering issue if found, else None.

        Returns None when execution was clean with no improvement opportunity.
        """

        # Check for repeated failures
        if run.status == "failed" and run.retry_count > 0:
            failures = [e for e in run.execution_log if not e["success"]]
            if failures:
                first_failure = failures[0]
                return EngineeringIssue(
                    layer="Executor",
                    reason=f"Task failed after {run.retry_count + 1} attempts",
                    impact="HIGH",
                    suggested_fix="Improve error recovery or planner retry strategy",
                    evidence=f"Tool: {first_failure['tool']}, Error: {first_failure.get('output', 'unknown')}",
                    regression_required=True
                )

        # Check for plan validation failures in retry context
        if run.retry_count > 0 and run.plan:
            return EngineeringIssue(
                layer="Planner",
                reason="Required retry to complete task",
                impact="MEDIUM",
                suggested_fix="Improve initial plan quality or validation",
                evidence=f"Retry count: {run.retry_count}, Plan steps: {len(run.plan)}",
                regression_required=True
            )

        # Check for slow memory search
        if timings.get("memory_search", 0) > 1.0:
            return EngineeringIssue(
                layer="Memory",
                reason="Memory search exceeded 1s threshold",
                impact="MEDIUM",
                suggested_fix="Optimize memory retrieval or add caching",
                evidence=f"Memory search took {timings['memory_search']:.2f}s",
                regression_required=False
            )

        # Check for slow planning
        if timings.get("plan", 0) > 15.0:
            return EngineeringIssue(
                layer="Planner",
                reason="Planning took longer than 15s",
                impact="MEDIUM",
                suggested_fix="Reduce world state size or optimize planner prompt",
                evidence=f"Planning took {timings['plan']:.2f}s",
                regression_required=False
            )

        # Check for excessive observation time
        if timings.get("observe", 0) > 2.0:
            return EngineeringIssue(
                layer="Observers",
                reason="World observation exceeded 2s threshold",
                impact="LOW",
                suggested_fix="Optimize observer collection or parallelize observers",
                evidence=f"Observation took {timings['observe']:.2f}s",
                regression_required=False
            )

        # Check for high-risk operations
        if run.plan_risk_level == "HIGH" and run.status == "completed":
            # This is actually good - high risk operations succeeded
            # No issue to report
            pass

        # No issues found
        return None
