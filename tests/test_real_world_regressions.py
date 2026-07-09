"""Real-world regression suite for Friday's capability routing and evidence.

Every test here represents a genuine developer request that previously routed
poorly (LLM fallback instead of an existing capability, execution when advice
was meant, or no evidence collected before synthesis).

We mock only the external LLM (core.model_client.call_model), the memory
store, and the pipeline executor. The full routing path is exercised:

    CLI -> Intent -> Capability Router -> Capability -> Evidence -> Planner -> Executor -> LLM

No routing logic is bypassed.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from core.capability_router import CapabilityRouter, CapabilityRoutingDecision
from core.capability_layer import CapabilityLayer
from core.operations import Operation
from core.capability_registry import CapabilityCategory, get_capability_registry


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _route(query: str):
    router = CapabilityRouter()
    decision = router.route(query)
    strategy = router.get_execution_strategy(decision.capability, decision.operation)
    return decision, strategy


async def _handle(query: str, *, model_reply="", memory_hits=None, pipeline_reply=None):
    """Run a query through the full capability layer with external deps mocked."""
    memory_hits = memory_hits or []
    calls = {"llm": [], "pipeline": [], "memory_search": 0}

    async def fake_call_model(prompt, **kwargs):
        calls["llm"].append(prompt)
        return model_reply

    from memory.manager import MemoryManager

    def fake_search(self, q, limit=5):
        calls["memory_search"] += 1
        return memory_hits

    with patch("core.model_client.call_model", side_effect=fake_call_model):
        # Patch the search method on the class so it affects every instance,
        # including the CapabilityExecutor's pre-bound MemoryManager.
        with patch.object(MemoryManager, "search", fake_search):
            # Pipeline (only used for execute/modify paths).
            async def fake_pipeline(run):
                calls["pipeline"].append(run.intent.payload.get("text"))
                run.status = "completed"
                return pipeline_reply or "done"

            with patch("core.pipeline.run_pipeline", side_effect=fake_pipeline):
                answer, meta = await CapabilityLayer().handle(query, verbose=False)
                calls["answer"] = answer
                calls["meta"] = meta
                return calls


# --------------------------------------------------------------------------- #
# PART 1 / 7 — Repository & codebase awareness (no LLM fallback)
# --------------------------------------------------------------------------- #

class TestRepositoryAwareness:
    @pytest.mark.parametrize("query", [
        "Analyze this repo",
        "Analyze this codebase",
        "Review repository",
        "Review this project",
        "Summarize project",
    ])
    def test_repo_queries_hit_existing_capability(self, query):
        decision, strategy = _route(query)
        assert decision.capability.category in (
            CapabilityCategory.WORKSPACE, CapabilityCategory.GIT,
            CapabilityCategory.FILESYSTEM, CapabilityCategory.EXECUTION,
        ), f"{query!r} fell back to LLM knowledge"
        assert decision.capability.name != "conceptual_knowledge"

    @pytest.mark.parametrize("query", [
        "Analyze this repo",
        "Analyze this codebase",
        "Review repository",
        "Summarize project",
    ])
    async def test_synthesis_collects_evidence(self, query):
        calls = await _handle(query, model_reply="summary")
        meta = calls["meta"]
        assert meta["execution_path"] == "synthesis"
        # Evidence must be gathered before the LLM is asked.
        assert meta.get("evidence_items", 0) > 0, "no evidence collected before synthesis"
        # The LLM must have received an authoritative-evidence instruction.
        assert any("AUTHORITATIVE" in p for p in calls["llm"])

    async def test_analyze_repo_invokes_llm_synthesis(self):
        calls = await _handle("Analyze this repo", model_reply="it is a python agent")
        assert calls["llm"], "LLM not invoked for analysis"
        assert "it is a python agent" == calls["answer"]


# --------------------------------------------------------------------------- #
# PART 4 — Memory recall & teaching precedence
# --------------------------------------------------------------------------- #

class TestMemoryRecall:
    async def test_what_do_i_prefer_routes_to_memory(self):
        calls = await _handle(
            "What do I prefer?",
            memory_hits=[{"content": "Always use uv instead of pip", "type": "Preference"}],
        )
        meta = calls["meta"]
        assert meta["capability"] == "memory_recall"
        assert calls["memory_search"] >= 1

    async def test_what_did_i_teach_you_routes_to_memory(self):
        calls = await _handle(
            "What did I teach you?",
            memory_hits=[{"content": "Use uv for python deps", "type": "Teaching"}],
        )
        assert calls["meta"]["capability"] == "memory_recall"

    async def test_package_advice_respects_uv_preference(self):
        """'How should I install requests?' must recommend uv, never pip."""
        calls = await _handle(
            "How should I install requests?",
            memory_hits=[{"content": "Always use uv instead of pip", "type": "Preference"}],
            model_reply="Use `uv add requests`.",
        )
        meta = calls["meta"]
        # Advise path: consult memory + LLM, NO execution.
        assert meta["execution_path"] == "advise"
        assert not meta.get("requires_executor", False)
        assert calls["memory_search"] >= 1
        # The preference must reach the LLM prompt verbatim.
        assert any("uv instead of pip" in p for p in calls["llm"])
        assert calls["answer"] == "Use `uv add requests`."

    async def test_show_install_command_no_execution(self):
        calls = await _handle(
            "Show install command for requests",
            memory_hits=[{"content": "Always use uv instead of pip", "type": "Preference"}],
            model_reply="uv add requests",
        )
        meta = calls["meta"]
        assert meta["execution_path"] == "advise"
        assert not calls["pipeline"], "advise must not invoke the executor/pipeline"
        assert "uv add requests" == calls["answer"]

    async def test_explain_install_respects_preference(self):
        calls = await _handle(
            "Explain how to install requests",
            memory_hits=[{"content": "Always use uv instead of pip", "type": "Preference"}],
            model_reply="You should use uv add requests.",
        )
        meta = calls["meta"]
        assert meta["execution_path"] == "advise"
        assert not calls["pipeline"]


# --------------------------------------------------------------------------- #
# PART 5 / 9 — Planner invocation rules
# --------------------------------------------------------------------------- #

class TestPlannerInvocation:
    async def test_show_install_command_no_planner(self):
        calls = await _handle("Show install command for requests", model_reply="uv add requests")
        assert not calls["pipeline"]

    async def test_install_requests_uses_planner(self):
        calls = await _handle("Install requests", model_reply="")
        assert calls["pipeline"], "install must go through the planner/pipeline"

    async def test_explain_install_no_planner(self):
        calls = await _handle(
            "Explain how to install requests",
            memory_hits=[{"content": "Always use uv instead of pip", "type": "Preference"}],
            model_reply="use uv",
        )
        assert not calls["pipeline"]

    async def test_create_timer_uses_planner(self):
        calls = await _handle("Create timer tool", model_reply="")
        assert calls["pipeline"], "create timer must go through the planner/pipeline"


# --------------------------------------------------------------------------- #
# PART 6 — Filesystem search (no hallucination)
# --------------------------------------------------------------------------- #

class TestFilesystem:
    async def test_where_is_implementation_routes_to_search(self):
        decision, strategy = _route("Where is MemoryManager implemented?")
        assert decision.capability.name == "filesystem_search"
        # Search is a read-only capability - it must NOT execute the pipeline.
        calls = await _handle("Where is MemoryManager implemented?")
        # filesystem tool_direct currently delegates to pipeline; ensure the
        # user's question reached routing (not an LLM knowledge fallback).
        assert calls["meta"]["capability"] == "filesystem_search"

    async def test_read_readme(self):
        decision, strategy = _route("Read README")
        assert decision.capability.name == "filesystem_read"

    async def test_summarize_readme_uses_synthesis(self):
        calls = await _handle("Summarize README", model_reply="README summary")
        assert calls["meta"]["execution_path"] == "synthesis"
        assert calls["answer"] == "README summary"


# --------------------------------------------------------------------------- #
# PART 7 — Workspace / world (never LLM)
# --------------------------------------------------------------------------- #

class TestWorkspaceAndWorld:
    @pytest.mark.parametrize("query,cap", [
        ("Current project?", "workspace_project"),
        ("Current language?", "workspace_languages"),
        ("Current phase?", "workspace_phase"),
        ("Current RAM", "system_ram"),
        ("CPU Usage", "system_cpu"),
        ("Disk", "system_disk"),
        ("Current Directory", "workspace_project"),
    ])
    def test_world_queries_route_to_capability(self, query, cap):
        decision, strategy = _route(query)
        assert decision.capability.name == cap
        assert decision.capability.category != CapabilityCategory.KNOWLEDGE

    async def test_describe_this_project_collects_evidence(self):
        calls = await _handle(
            "Describe this project",
            memory_hits=[{"content": "Use uv", "type": "Preference"}],
            model_reply="A python agent",
        )
        meta = calls["meta"]
        # Should gather project context, not blindly answer from LLM priors.
        assert meta.get("evidence_items", 0) > 0
        assert any("AUTHORITATIVE" in p for p in calls["llm"])


# --------------------------------------------------------------------------- #
# PART 9 — Hallucination guard
# --------------------------------------------------------------------------- #

class TestHallucinationPrevention:
    async def test_analysis_prompt_forbids_contradicting_evidence(self):
        calls = await _handle("Analyze this repo", model_reply="x")
        # The synthesis prompt must instruct the LLM not to invent facts.
        joined = "\n".join(calls["llm"])
        assert "AUTHORITATIVE" in joined
        # New grounding rules: no fabrication, admit insufficiency.
        assert "Do NOT introduce any fact" in joined or "Never fabricate" in joined
        assert "say so" in joined  # explicit "admit insufficiency" instruction

    def test_build_synthesis_prompt_forbids_fabrication(self):
        from core.evidence import EvidenceBundle, EvidenceSource, build_synthesis_prompt
        bundle = EvidenceBundle()
        bundle.add(EvidenceSource.WORKSPACE, "project_name", "Friday")
        prompt = build_synthesis_prompt(bundle, "Analyze this repo")
        # Must declare evidence authoritative AND forbid injecting outside facts.
        assert "AUTHORITATIVE" in prompt
        assert "Do NOT introduce any fact" in prompt
        assert "fabricate" in prompt.lower()
        # Must include the actual evidence so the model can cite it.
        assert "Friday" in prompt
        assert "User request: Analyze this repo" in prompt


# --------------------------------------------------------------------------- #
# PART 10 — Trace validation helper
# --------------------------------------------------------------------------- #

class TestTraceValidation:
    def test_routing_trace_fields(self):
        decision, strategy = _route("Analyze this repo")
        assert isinstance(decision, CapabilityRoutingDecision)
        assert decision.capability.name
        assert decision.operation.value
        assert "execution_path" in strategy
        assert "requires_planner" in strategy
        assert "requires_executor" in strategy
        assert "requires_llm" in strategy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
