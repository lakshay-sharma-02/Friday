"""End-to-end integration test for Phase 10 Capability Layer.

Verifies that queries actually traverse the Capability Layer.
Prints execution traces to prove routing works.
"""

import pytest
import asyncio
from core.capability_layer import CapabilityLayer


@pytest.mark.asyncio
class TestCapabilityLayerIntegration:
    """Test complete integration of capability layer."""

    async def test_system_state_routing(self):
        """Test that system state queries route through capability layer."""
        layer = CapabilityLayer()

        print("\n=== Test: Current RAM ===")
        answer, metadata = await layer.handle("Current RAM?", verbose=True)

        print(f"Answer: {answer}")
        print(f"Capability: {metadata.get('capability')}")
        print(f"Category: {metadata.get('category')}")
        print(f"Execution Path: {metadata.get('execution_path')}")
        print(f"Source: {metadata.get('source', 'N/A')}")

        assert metadata.get('category') == 'system_state'
        assert metadata.get('execution_path') == 'direct'

    async def test_workspace_routing(self):
        """Test that workspace queries route through capability layer."""
        layer = CapabilityLayer()

        print("\n=== Test: Current Project ===")
        answer, metadata = await layer.handle("What is the current project?", verbose=True)

        print(f"Answer: {answer}")
        print(f"Capability: {metadata.get('capability')}")
        print(f"Category: {metadata.get('category')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        assert metadata.get('category') == 'workspace'
        assert metadata.get('execution_path') == 'direct'

    async def test_git_routing(self):
        """Test that git queries route through capability layer."""
        layer = CapabilityLayer()

        print("\n=== Test: Git Branch ===")
        answer, metadata = await layer.handle("What is the current git branch?", verbose=True)

        print(f"Answer: {answer}")
        print(f"Capability: {metadata.get('capability')}")
        print(f"Category: {metadata.get('category')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        assert metadata.get('category') == 'git'
        assert metadata.get('execution_path') == 'direct'

    async def test_memory_routing(self):
        """Test that memory queries route through capability layer."""
        layer = CapabilityLayer()

        print("\n=== Test: Memory Recall ===")
        answer, metadata = await layer.handle("What did I teach you?", verbose=True)

        print(f"Answer: {answer[:100]}...")
        print(f"Capability: {metadata.get('capability')}")
        print(f"Category: {metadata.get('category')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        assert metadata.get('category') == 'memory'

    async def test_filesystem_routing(self):
        """Test that filesystem queries route through capability layer."""
        layer = CapabilityLayer()

        print("\n=== Test: File Search ===")
        answer, metadata = await layer.handle("Where is the MemoryManager class?", verbose=True)

        print(f"Answer: {answer[:100]}...")
        print(f"Capability: {metadata.get('capability')}")
        print(f"Category: {metadata.get('category')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        assert metadata.get('category') == 'filesystem'

    async def test_knowledge_routing(self):
        """Test that knowledge queries route through capability layer."""
        layer = CapabilityLayer()

        print("\n=== Test: Conceptual Knowledge ===")
        answer, metadata = await layer.handle("Explain Rust ownership", verbose=True)

        print(f"Answer: {answer[:100]}...")
        print(f"Capability: {metadata.get('capability')}")
        print(f"Category: {metadata.get('category')}")
        print(f"Execution Path: {metadata.get('execution_path')}")

        assert metadata.get('category') == 'knowledge'
        # Explanations now collect evidence then synthesize (synthesis path).
        assert metadata.get('execution_path') in ['direct', 'llm', 'synthesis']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
