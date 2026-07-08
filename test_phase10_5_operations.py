"""Phase 10.5 Acceptance Tests - Operation Semantics

Verifies that Friday distinguishes between:
- Advice ("how should I install requests?") - NO execution
- Execution ("install requests") - YES execution
- Explanation ("explain ownership") - NO execution
- Inspection ("current RAM") - NO execution
"""

import pytest
import asyncio
from core.capability_layer import CapabilityLayer
from core.operations import Operation


@pytest.mark.asyncio
class TestOperationSemantics:
    """Test that operation semantics prevent inappropriate execution."""

    async def test_advise_never_executes(self):
        """CRITICAL: ADVISE operations must NEVER execute tools."""
        layer = CapabilityLayer()

        print("\n=== Test: How should I install requests? ===")
        answer, metadata = await layer.handle("How should I install requests?", verbose=True)

        print(f"Answer: {answer[:200]}...")
        print(f"Operation: {metadata.get('operation')}")
        print(f"Execution Path: {metadata.get('execution_path')}")
        print(f"Planner: {metadata.get('requires_planner', 'N/A')}")
        print(f"Executor: {metadata.get('requires_executor', 'N/A')}")
        print(f"Executed Tools: {metadata.get('executed_tools', False)}")

        # MUST be advise operation
        assert metadata.get('operation') == 'advise'
        # MUST use advise path
        assert metadata.get('execution_path') == 'advise'
        # MUST NOT execute tools
        assert metadata.get('executed_tools') == False

    async def test_execute_requires_planner(self):
        """EXECUTE operations must go through planner."""
        layer = CapabilityLayer()

        print("\n=== Test: Install requests ===")
        answer, metadata = await layer.handle("Install requests", verbose=True)

        print(f"Answer: {answer[:200]}...")
        print(f"Operation: {metadata.get('operation')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        # MUST be execute operation
        assert metadata.get('operation') == 'execute'
        # MUST use pipeline path
        assert metadata.get('execution_path') in ['pipeline', 'tool_direct']

    async def test_read_never_executes(self):
        """READ operations must never modify state."""
        layer = CapabilityLayer()

        print("\n=== Test: Current RAM ===")
        answer, metadata = await layer.handle("Current RAM", verbose=True)

        print(f"Answer: {answer[:100]}")
        print(f"Operation: {metadata.get('operation')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        # MUST be read operation
        assert metadata.get('operation') == 'read'
        # MUST use direct path (no execution)
        assert metadata.get('execution_path') == 'direct'

    async def test_show_command_is_advise(self):
        """'Show the command' must be ADVISE, not EXECUTE."""
        layer = CapabilityLayer()

        print("\n=== Test: Show the install command ===")
        answer, metadata = await layer.handle("Show the install command", verbose=True)

        print(f"Answer: {answer[:200]}...")
        print(f"Operation: {metadata.get('operation')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        # MUST be advise, not execute
        assert metadata.get('operation') == 'advise'
        assert metadata.get('execution_path') == 'advise'

    async def test_explain_never_executes(self):
        """EXPLAIN operations use LLM only, no execution."""
        layer = CapabilityLayer()

        print("\n=== Test: Explain Rust ownership ===")
        answer, metadata = await layer.handle("Explain Rust ownership", verbose=True)

        print(f"Answer: {answer[:200]}...")
        print(f"Operation: {metadata.get('operation')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        # MUST be explain operation
        assert metadata.get('operation') == 'explain'
        # MUST NOT execute tools (synthesis or llm path)
        assert metadata.get('execution_path') in ['synthesis', 'llm', 'direct']


@pytest.mark.asyncio
class TestOperationMatrix:
    """Test operation-capability matrix."""

    async def test_operation_classification_accuracy(self):
        """Verify operation classifier works correctly."""
        from core.operation_classifier import OperationClassifier

        classifier = OperationClassifier()

        test_cases = [
            ("How should I install requests?", Operation.ADVISE),
            ("Install requests", Operation.EXECUTE),
            ("Show the install command", Operation.ADVISE),
            ("Current RAM", Operation.READ),
            ("Where is MemoryManager?", Operation.LOOKUP),
            ("Explain Rust ownership", Operation.EXPLAIN),
            ("Summarize this project", Operation.SUMMARIZE),
        ]

        print("\n=== Operation Classification Accuracy ===")
        passed = 0
        for query, expected in test_cases:
            result = classifier.classify(query)
            status = "✓" if result == expected else "✗"
            if result == expected:
                passed += 1
            print(f"{status} '{query}' → {result.value} (expected: {expected.value})")

        print(f"\nAccuracy: {passed}/{len(test_cases)} ({100*passed//len(test_cases)}%)")
        assert passed >= len(test_cases) * 0.85  # At least 85% accuracy


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
