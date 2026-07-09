"""Engineering Intelligence - root cause analysis and diagnostics."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class IssueCategory(Enum):
    """Strict issue categories - never use free-form."""
    ARCHITECTURE = "Architecture"
    CAPABILITY_GAP = "Capability Gap"
    PLANNER = "Planner"
    EXECUTOR = "Executor"
    MEMORY = "Memory"
    EVIDENCE = "Evidence"
    ROUTING = "Routing"
    WORKSPACE = "Workspace"
    REPOSITORY_INTELLIGENCE = "Repository Intelligence"
    TOOL = "Tool"
    PERFORMANCE = "Performance"
    REGRESSION = "Regression"
    CONFIGURATION = "Configuration"
    MODEL = "Model"
    DOCUMENTATION = "Documentation"
    UNKNOWN = "Unknown"


@dataclass
class RootCause:
    """Root cause analysis result."""
    category: IssueCategory
    likely_cause: str
    confidence: float  # 0.0 to 1.0
    supporting_evidence: list[str]
    alternatives: list[str]
    recommended_fix: str
    regression_required: bool


class IssueClassifier:
    """Classify issues into engineering categories."""

    def classify(self, layer: str, reason: str, evidence: str) -> IssueCategory:
        """Deterministic issue classification based on layer and reason."""

        # Memory layer issues
        if layer == "Memory":
            if "search" in reason.lower() or "retrieval" in reason.lower():
                return IssueCategory.MEMORY
            if "storage" in reason.lower() or "persist" in reason.lower():
                return IssueCategory.MEMORY
            return IssueCategory.MEMORY

        # Planner issues
        if layer == "Planner":
            if "retry" in reason.lower():
                return IssueCategory.PLANNER
            if "slow" in reason.lower() or "took longer" in reason.lower():
                return IssueCategory.PERFORMANCE
            if "invalid" in reason.lower() or "validation" in reason.lower():
                return IssueCategory.PLANNER
            return IssueCategory.PLANNER

        # Executor issues
        if layer == "Executor":
            if "failed" in reason.lower():
                if "tool" in evidence.lower():
                    return IssueCategory.TOOL
                return IssueCategory.EXECUTOR
            if "timeout" in reason.lower():
                return IssueCategory.PERFORMANCE
            return IssueCategory.EXECUTOR

        # Observer issues
        if layer == "Observers":
            if "slow" in reason.lower():
                return IssueCategory.PERFORMANCE
            return IssueCategory.WORKSPACE

        # Default to unknown
        return IssueCategory.UNKNOWN


class RootCauseAnalyzer:
    """Analyze root causes of engineering issues."""

    def analyze(
        self,
        category: IssueCategory,
        layer: str,
        reason: str,
        evidence: str,
        impact: str
    ) -> RootCause:
        """Perform root cause analysis - deterministic, no LLM."""

        if category == IssueCategory.MEMORY:
            return self._analyze_memory(reason, evidence)
        elif category == IssueCategory.PLANNER:
            return self._analyze_planner(reason, evidence, impact)
        elif category == IssueCategory.EXECUTOR:
            return self._analyze_executor(reason, evidence)
        elif category == IssueCategory.TOOL:
            return self._analyze_tool(reason, evidence)
        elif category == IssueCategory.PERFORMANCE:
            return self._analyze_performance(layer, reason, evidence)
        else:
            return self._analyze_unknown(category, reason, evidence)

    def _analyze_memory(self, reason: str, evidence: str) -> RootCause:
        """Analyze memory-related issues."""
        if "exceeded 1s" in reason:
            return RootCause(
                category=IssueCategory.MEMORY,
                likely_cause="Memory search is inefficient - likely scanning full database without indexing",
                confidence=0.85,
                supporting_evidence=[
                    evidence,
                    "Search latency threshold exceeded",
                    "No semantic indexing in current memory implementation"
                ],
                alternatives=[
                    "Large result set being processed",
                    "Database lock contention",
                    "Disk I/O bottleneck"
                ],
                recommended_fix="Add vector indexing for semantic search or implement query result caching",
                regression_required=False
            )

        return RootCause(
            category=IssueCategory.MEMORY,
            likely_cause="Memory subsystem performance degradation",
            confidence=0.60,
            supporting_evidence=[evidence],
            alternatives=["Database schema inefficiency", "Query optimization needed"],
            recommended_fix="Profile memory operations and optimize bottleneck",
            regression_required=False
        )

    def _analyze_planner(self, reason: str, evidence: str, impact: str) -> RootCause:
        """Analyze planner-related issues."""
        if "retry" in reason.lower():
            return RootCause(
                category=IssueCategory.PLANNER,
                likely_cause="Initial plan quality insufficient - planner made invalid assumptions or missed constraints",
                confidence=0.75,
                supporting_evidence=[
                    evidence,
                    "Required retry to complete task",
                    "First plan failed validation or execution"
                ],
                alternatives=[
                    "Tool validation too strict",
                    "World state incomplete",
                    "Memory context insufficient"
                ],
                recommended_fix="Improve planner prompt with better constraints or enhance world state observation",
                regression_required=True
            )

        if "longer than 15s" in reason:
            return RootCause(
                category=IssueCategory.PERFORMANCE,
                likely_cause="Planner prompt too large or model latency high",
                confidence=0.80,
                supporting_evidence=[
                    evidence,
                    "Planning exceeded performance threshold",
                    "Model response time bottleneck"
                ],
                alternatives=[
                    "World state too verbose",
                    "Memory context too large",
                    "Network latency to model endpoint"
                ],
                recommended_fix="Reduce planner context size or optimize world state serialization",
                regression_required=False
            )

        return RootCause(
            category=IssueCategory.PLANNER,
            likely_cause="Planner behavior suboptimal",
            confidence=0.55,
            supporting_evidence=[evidence],
            alternatives=["Prompt engineering issue", "Model capability limitation"],
            recommended_fix="Analyze planner output and refine prompt",
            regression_required=True
        )

    def _analyze_executor(self, reason: str, evidence: str) -> RootCause:
        """Analyze executor-related issues."""
        if "failed after" in reason:
            return RootCause(
                category=IssueCategory.EXECUTOR,
                likely_cause="Tool execution failure - command error or environmental issue",
                confidence=0.90,
                supporting_evidence=[
                    evidence,
                    "Multiple retry attempts failed",
                    "Consistent failure pattern"
                ],
                alternatives=[
                    "Tool input validation insufficient",
                    "Environment not ready for operation",
                    "Resource limitation (permissions, disk, memory)"
                ],
                recommended_fix="Improve error recovery strategy or add pre-execution validation",
                regression_required=True
            )

        return RootCause(
            category=IssueCategory.EXECUTOR,
            likely_cause="Execution subsystem error",
            confidence=0.65,
            supporting_evidence=[evidence],
            alternatives=["Timeout issue", "Resource exhaustion"],
            recommended_fix="Add better error handling and retry logic",
            regression_required=True
        )

    def _analyze_tool(self, reason: str, evidence: str) -> RootCause:
        """Analyze tool-related issues."""
        return RootCause(
            category=IssueCategory.TOOL,
            likely_cause="Tool implementation error or incorrect usage",
            confidence=0.85,
            supporting_evidence=[
                evidence,
                "Tool-level failure detected"
            ],
            alternatives=[
                "Tool input format invalid",
                "Tool lacks error handling",
                "Tool assumptions violated"
            ],
            recommended_fix="Review tool implementation and add input validation",
            regression_required=True
        )

    def _analyze_performance(self, layer: str, reason: str, evidence: str) -> RootCause:
        """Analyze performance-related issues."""
        if "observation" in layer.lower():
            return RootCause(
                category=IssueCategory.PERFORMANCE,
                likely_cause="Observer collection too slow - sequential execution or expensive system calls",
                confidence=0.75,
                supporting_evidence=[
                    evidence,
                    "Observation phase exceeded threshold"
                ],
                alternatives=[
                    "Disk I/O bottleneck",
                    "Network latency",
                    "Sequential observer execution"
                ],
                recommended_fix="Parallelize observer collection or cache expensive observations",
                regression_required=False
            )

        return RootCause(
            category=IssueCategory.PERFORMANCE,
            likely_cause="Operation exceeded performance threshold",
            confidence=0.70,
            supporting_evidence=[evidence],
            alternatives=["Resource contention", "Inefficient algorithm"],
            recommended_fix="Profile operation and optimize bottleneck",
            regression_required=False
        )

    def _analyze_unknown(self, category: IssueCategory, reason: str, evidence: str) -> RootCause:
        """Analyze issues with unknown category."""
        return RootCause(
            category=category,
            likely_cause="Issue classification failed - insufficient data",
            confidence=0.30,
            supporting_evidence=[evidence],
            alternatives=["Novel failure mode", "Insufficient instrumentation"],
            recommended_fix="Add instrumentation and re-evaluate",
            regression_required=False
        )
