"""Phase 10 Benchmark - Measure capability layer performance.

Benchmarks routing speed, execution latency, and system integration.
"""

import pytest
import asyncio
import time
from core.capability_router import CapabilityRouter
from core.capability_executor import CapabilityExecutor
from core.capability_layer import CapabilityLayer
from core.capability_registry import get_capability_registry, CapabilityCategory
from core.world import WorldState, WorkspaceState, ComputerState, NetworkState
from core.world import DeveloperState, RuntimeState, ProcessState
from core.project_context import ProjectContext
from datetime import datetime


class TestCapabilityRouting:
    """Benchmark routing performance."""

    def test_routing_latency(self):
        """Measure routing decision latency."""
        router = CapabilityRouter()

        queries = [
            "Current RAM?",
            "What project?",
            "Git branch?",
            "Where is MemoryManager?",
            "Explain Rust ownership",
        ]

        latencies = []
        for query in queries:
            start = time.perf_counter()
            decision = router.route(query)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)
            print(f"  {query:40} → {decision.capability.name:20} ({latency_ms:.2f}ms)")

        avg_latency = sum(latencies) / len(latencies)
        print(f"\n  Average routing latency: {avg_latency:.2f}ms")

        # Routing should be fast (<10ms average)
        assert avg_latency < 10, f"Routing too slow: {avg_latency:.2f}ms"

    def test_routing_accuracy(self):
        """Verify routing correctness."""
        router = CapabilityRouter()

        test_cases = [
            ("Current RAM?", "system_ram", CapabilityCategory.SYSTEM_STATE),
            ("What project?", "workspace_project", CapabilityCategory.WORKSPACE),
            ("Git branch?", "git_branch", CapabilityCategory.GIT),
            ("What did I teach you?", "memory_recall", CapabilityCategory.MEMORY),
            ("Explain ownership", "conceptual_knowledge", CapabilityCategory.KNOWLEDGE),
        ]

        correct = 0
        for query, expected_name, expected_category in test_cases:
            decision = router.route(query)
            if decision.capability.name == expected_name:
                correct += 1
                status = "✓"
            else:
                status = "✗"
            print(f"  {status} {query:40} → {decision.capability.name:20} (expected: {expected_name})")

        accuracy = correct / len(test_cases) * 100
        print(f"\n  Routing accuracy: {accuracy:.1f}%")

        assert accuracy >= 80, f"Routing accuracy too low: {accuracy:.1f}%"


@pytest.mark.asyncio
class TestCapabilityExecution:
    """Benchmark execution performance."""

    async def test_system_state_latency(self):
        """Measure system state query latency."""
        executor = CapabilityExecutor()
        registry = get_capability_registry()

        # Create world state
        computer = ComputerState(
            os="Linux",
            ram_gb=16,
            logical_cores=8,
            disk_use_percent="45%",
            battery_percent="85%"
        )
        network = NetworkState(internet_reachable=True, hostname="localhost")
        world = WorldState(
            workspace=WorkspaceState(cwd="."),
            computer=computer,
            network=network,
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now()
        )

        # Test multiple system state queries
        capabilities = [
            ("system_ram", "Current RAM?"),
            ("system_cpu", "CPU cores?"),
            ("system_disk", "Disk usage?"),
            ("system_battery", "Battery level?"),
            ("system_network", "Internet status?"),
        ]

        latencies = []
        for cap_name, query in capabilities:
            cap = registry.get(cap_name)
            start = time.perf_counter()
            result = await executor.execute(cap, query, world=world)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            status = "✓" if result.success else "✗"
            print(f"  {status} {cap_name:20} {latency_ms:6.2f}ms")

        avg_latency = sum(latencies) / len(latencies)
        print(f"\n  Average system state latency: {avg_latency:.2f}ms")

        # System state should be instant (<5ms)
        assert avg_latency < 5, f"System state too slow: {avg_latency:.2f}ms"

    async def test_workspace_query_latency(self):
        """Measure workspace query latency."""
        executor = CapabilityExecutor()
        registry = get_capability_registry()

        # Create workspace state
        workspace = WorkspaceState(
            cwd=".",
            project_type="python",
            languages=["python"],
            is_git_repo=True,
            git_branch="main",
            git_clean=True
        )
        world = WorldState(
            workspace=workspace,
            computer=ComputerState(),
            network=NetworkState(),
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now()
        )
        project = ProjectContext(
            name="Friday",
            purpose="Agentic OS",
            active_phase="Phase 10",
            project_type="python",
            languages=["python"]
        )

        # Test workspace queries
        capabilities = [
            ("workspace_project", "What project?"),
            ("workspace_phase", "What phase?"),
            ("workspace_languages", "What languages?"),
            ("workspace_type", "Project type?"),
        ]

        latencies = []
        for cap_name, query in capabilities:
            cap = registry.get(cap_name)
            start = time.perf_counter()
            result = await executor.execute(cap, query, world, project)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

            status = "✓" if result.success else "✗"
            print(f"  {status} {cap_name:20} {latency_ms:6.2f}ms")

        avg_latency = sum(latencies) / len(latencies)
        print(f"\n  Average workspace latency: {avg_latency:.2f}ms")

        # Workspace queries should be instant (<5ms)
        assert avg_latency < 5, f"Workspace queries too slow: {avg_latency:.2f}ms"


class TestEndToEndPerformance:
    """Benchmark end-to-end capability layer performance."""

    def test_capability_count(self):
        """Verify all expected capabilities are registered."""
        registry = get_capability_registry()
        capabilities = registry.list_all()

        by_category = {}
        for cap in capabilities:
            category = cap.category.value
            by_category[category] = by_category.get(category, 0) + 1

        print("\n  Capabilities by category:")
        for category, count in sorted(by_category.items()):
            print(f"    {category:20} {count:2} capabilities")

        total = len(capabilities)
        print(f"\n  Total capabilities: {total}")

        # Should have at least 17 capabilities registered
        assert total >= 17, f"Missing capabilities: only {total} registered"

    def test_ownership_coverage(self):
        """Verify all categories have proper ownership."""
        registry = get_capability_registry()

        categories_covered = set()
        for cap in registry.list_all():
            categories_covered.add(cap.category)

        expected_categories = {
            CapabilityCategory.SYSTEM_STATE,
            CapabilityCategory.WORKSPACE,
            CapabilityCategory.GIT,
            CapabilityCategory.MEMORY,
            CapabilityCategory.FILESYSTEM,
            CapabilityCategory.KNOWLEDGE,
            CapabilityCategory.EXECUTION,
        }

        missing = expected_categories - categories_covered

        print(f"\n  Categories covered: {len(categories_covered)}/{len(expected_categories)}")
        if missing:
            print(f"  Missing: {', '.join(c.value for c in missing)}")
        else:
            print("  ✓ All categories have capabilities")

        assert not missing, f"Missing coverage for: {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
