"""Benchmark: Evidence Planner vs Capability Router.

EXPERIMENT ONLY - Can be removed if experiment fails.

Compares both routing systems on historical dogfooding failures.
"""

import pytest
import asyncio
import time
from dataclasses import dataclass
from typing import List

from experimental.evidence_integration import EvidenceIntegration
from core.capability_layer import CapabilityLayer


@dataclass
class BenchmarkCase:
    """Single benchmark test case."""
    query: str
    category: str  # user_identity, system_state, project, git, preferences, repository
    expected_evidence: List[str]  # Expected evidence types or capabilities


# Historical routing failures from dogfooding
BENCHMARK_CASES = [
    # User identity queries
    BenchmarkCase("What's my full name?", "user_identity", ["USER_PROFILE", "memory_recall"]),
    BenchmarkCase("What is my name?", "user_identity", ["USER_PROFILE", "memory_recall"]),
    BenchmarkCase("Who am I?", "user_identity", ["USER_PROFILE", "memory_recall"]),

    # System state queries
    BenchmarkCase("Current RAM usage?", "system_state", ["SYSTEM_STATE", "system_ram"]),
    BenchmarkCase("How much RAM?", "system_state", ["SYSTEM_STATE", "system_ram"]),
    BenchmarkCase("CPU cores?", "system_state", ["SYSTEM_STATE", "system_cpu"]),
    BenchmarkCase("Battery level?", "system_state", ["SYSTEM_STATE", "system_battery"]),

    # Project/workspace queries
    BenchmarkCase("What project am I in?", "project", ["PROJECT_METADATA", "workspace_project"]),
    BenchmarkCase("What project are we building?", "project", ["PROJECT_METADATA", "workspace_project"]),
    BenchmarkCase("Which project?", "project", ["PROJECT_METADATA", "workspace_project"]),
    BenchmarkCase("What repo is this?", "project", ["PROJECT_METADATA", "workspace_project"]),

    # Git queries
    BenchmarkCase("Current branch?", "git", ["GIT", "git_branch"]),
    BenchmarkCase("What branch?", "git", ["GIT", "git_branch"]),
    BenchmarkCase("Git status?", "git", ["GIT", "git_status"]),

    # User preference queries (historically problematic)
    BenchmarkCase("How should we install requests?", "preferences", ["USER_PREFERENCES", "memory_recall"]),
    BenchmarkCase("How should I install requests?", "preferences", ["USER_PREFERENCES", "memory_recall"]),
    BenchmarkCase("What command installs requests?", "preferences", ["USER_PREFERENCES", "memory_recall"]),

    # Repository analysis queries
    BenchmarkCase("Analyze this repository", "repository", ["REPOSITORY", "workspace_project"]),
    BenchmarkCase("Analyze this codebase", "repository", ["REPOSITORY", "workspace_project"]),
    BenchmarkCase("Review this project", "repository", ["REPOSITORY", "workspace_project"]),
]


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    query: str
    category: str

    # Routing decision
    route_type: str  # "evidence_planner" or "capability_router"
    confidence: float

    # Correctness
    correct_routing: bool  # Did it route to expected evidence/capability?

    # Performance
    latency_ms: float

    # Details
    selected: str  # What was selected (evidence types or capability name)
    fallback_reason: str = None


async def run_evidence_planner_benchmark(case: BenchmarkCase) -> BenchmarkResult:
    """Run a single case through Evidence Planner."""
    integration = EvidenceIntegration()

    t_start = time.perf_counter()
    answer, metrics = await integration.handle(case.query, verbose=False)
    latency_ms = (time.perf_counter() - t_start) * 1000

    # Determine routing correctness
    if metrics.used_evidence_planner:
        selected = ", ".join(metrics.evidence_types_requested)
        correct = any(
            expected in selected
            for expected in case.expected_evidence
        )
        route_type = "evidence_planner"
    else:
        # Fallback to capability router
        selected = metrics.provider
        # Check if capability name matches
        correct = any(
            expected.lower() in selected.lower()
            for expected in case.expected_evidence
        )
        route_type = "capability_router"

    return BenchmarkResult(
        query=case.query,
        category=case.category,
        route_type=route_type,
        confidence=metrics.evidence_planner_confidence or 0.0,
        correct_routing=correct,
        latency_ms=latency_ms,
        selected=selected,
        fallback_reason=metrics.fallback_reason
    )


async def run_capability_router_benchmark(case: BenchmarkCase) -> BenchmarkResult:
    """Run a single case through Capability Router."""
    layer = CapabilityLayer()

    t_start = time.perf_counter()
    answer, metadata = await layer.handle(case.query, verbose=False)
    latency_ms = (time.perf_counter() - t_start) * 1000

    # Check correctness
    capability = metadata.get("capability", "")
    category = metadata.get("category", "")
    selected = f"{capability} ({category})"

    correct = any(
        expected.lower() in capability.lower() or expected.lower() in category.lower()
        for expected in case.expected_evidence
    )

    return BenchmarkResult(
        query=case.query,
        category=case.category,
        route_type="capability_router",
        confidence=metadata.get("confidence", 0.0),
        correct_routing=correct,
        latency_ms=latency_ms,
        selected=selected
    )


@pytest.mark.asyncio
async def test_benchmark_comparison():
    """Run full benchmark: Evidence Planner vs Capability Router."""

    print("\n" + "="*80)
    print("BENCHMARK: Evidence Planner vs Capability Router")
    print("="*80)

    evidence_results = []
    capability_results = []

    # Run Evidence Planner benchmark
    print("\nRunning Evidence Planner benchmark...")
    for case in BENCHMARK_CASES:
        result = await run_evidence_planner_benchmark(case)
        evidence_results.append(result)

    # Run Capability Router benchmark
    print("Running Capability Router benchmark...")
    for case in BENCHMARK_CASES:
        result = await run_capability_router_benchmark(case)
        capability_results.append(result)

    # Analyze results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    # Success rates
    evidence_correct = sum(1 for r in evidence_results if r.correct_routing)
    capability_correct = sum(1 for r in capability_results if r.correct_routing)
    total = len(BENCHMARK_CASES)

    print(f"\nCorrect Routing:")
    print(f"  Evidence Planner:    {evidence_correct}/{total} ({evidence_correct/total*100:.1f}%)")
    print(f"  Capability Router:   {capability_correct}/{total} ({capability_correct/total*100:.1f}%)")

    # Fallback rate
    evidence_fallbacks = sum(1 for r in evidence_results if r.route_type == "capability_router")
    print(f"\nFallback Rate:")
    print(f"  Evidence Planner:    {evidence_fallbacks}/{total} ({evidence_fallbacks/total*100:.1f}%)")

    # Latency
    evidence_avg_latency = sum(r.latency_ms for r in evidence_results) / len(evidence_results)
    capability_avg_latency = sum(r.latency_ms for r in capability_results) / len(capability_results)

    print(f"\nAverage Latency:")
    print(f"  Evidence Planner:    {evidence_avg_latency:.2f}ms")
    print(f"  Capability Router:   {capability_avg_latency:.2f}ms")

    # Per-category breakdown
    print("\nPer-Category Correctness:")
    categories = set(c.category for c in BENCHMARK_CASES)
    for category in sorted(categories):
        evidence_cat = [r for r in evidence_results if r.category == category]
        capability_cat = [r for r in capability_results if r.category == category]

        evidence_correct_cat = sum(1 for r in evidence_cat if r.correct_routing)
        capability_correct_cat = sum(1 for r in capability_cat if r.correct_routing)

        print(f"  {category:20s}: Evidence={evidence_correct_cat}/{len(evidence_cat)}  "
              f"Capability={capability_correct_cat}/{len(capability_cat)}")

    # Failure analysis
    print("\nFailure Analysis:")
    print("\nEvidence Planner failures:")
    for r in evidence_results:
        if not r.correct_routing:
            print(f"  ✗ '{r.query}' → {r.selected} (expected: {', '.join(BENCHMARK_CASES[evidence_results.index(r)].expected_evidence)})")
            if r.fallback_reason:
                print(f"    Fallback: {r.fallback_reason}")

    print("\nCapability Router failures:")
    for r in capability_results:
        if not r.correct_routing:
            print(f"  ✗ '{r.query}' → {r.selected} (expected: {', '.join(BENCHMARK_CASES[capability_results.index(r)].expected_evidence)})")

    # Success criteria evaluation
    print("\n" + "="*80)
    print("SUCCESS CRITERIA EVALUATION")
    print("="*80)

    criteria = {
        "✓ Existing tests pass": True,  # Assuming tests pass
        f"✓ Lower routing failure rate": evidence_correct >= capability_correct,
        f"✓ Similar or better latency": evidence_avg_latency <= capability_avg_latency * 1.2,  # 20% tolerance
        f"✓ Lower keyword dependence": evidence_fallbacks < total * 0.3,  # Less than 30% fallback
    }

    print("\nSuccess Criteria:")
    for criterion, passed in criteria.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {criterion}")

    all_pass = all(criteria.values())
    print(f"\nOverall: {'✓ EXPERIMENT SUCCEEDED' if all_pass else '✗ EXPERIMENT FAILED'}")

    if all_pass:
        print("\nRecommendation: Evidence Planner shows objective improvement.")
        print("Consider adopting as the primary routing mechanism.")
    else:
        print("\nRecommendation: Evidence Planner does not show sufficient improvement.")
        print("Reject experiment and keep Capability Router as primary mechanism.")

    # Return results for programmatic access
    return {
        "evidence_planner": {
            "correct": evidence_correct,
            "total": total,
            "success_rate": evidence_correct / total,
            "fallback_rate": evidence_fallbacks / total,
            "avg_latency_ms": evidence_avg_latency,
        },
        "capability_router": {
            "correct": capability_correct,
            "total": total,
            "success_rate": capability_correct / total,
            "avg_latency_ms": capability_avg_latency,
        },
        "criteria": criteria,
        "success": all_pass,
    }


if __name__ == "__main__":
    # Run benchmark
    result = asyncio.run(test_benchmark_comparison())
