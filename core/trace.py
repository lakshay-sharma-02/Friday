"""Request Tracing - Complete observability into every Friday request.

Every LLM request becomes fully inspectable.
No more guessing where information came from.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class TraceStage(Enum):
    """Pipeline stages that can be traced."""
    INTENT_CLASSIFICATION = "intent_classification"
    CAPABILITY_ROUTING = "capability_routing"
    MEMORY_SEARCH = "memory_search"
    EVIDENCE_COLLECTION = "evidence_collection"
    WORKSPACE_SNAPSHOT = "workspace_snapshot"
    PLANNING = "planning"
    EXECUTION = "execution"
    LLM_CALL = "llm_call"
    FORMATTING = "formatting"


@dataclass
class EvidenceTrace:
    """Trace of a single piece of evidence."""
    type: str
    origin: str
    size: int
    summary: str
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryTrace:
    """Trace of memory retrieval."""
    memory_id: str
    memory_type: str
    similarity_score: float
    ranking_score: float
    importance: float
    project_relevance: float
    content_preview: str
    selected: bool
    rejection_reason: Optional[str] = None


@dataclass
class PromptTrace:
    """Complete prompt payload trace."""
    system_prompt: str
    evidence_block: str
    user_prompt: str
    final_payload: str
    token_count_estimate: int


@dataclass
class ModelResponseTrace:
    """LLM response trace."""
    raw_output: str
    parsed_output: Any
    reasoning_metadata: dict = field(default_factory=dict)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_seconds: float = 0.0


@dataclass
class StageTrace:
    """Trace of a single pipeline stage."""
    stage: TraceStage
    start_time: float
    end_time: float
    duration_seconds: float
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class RequestTrace:
    """Complete trace of a single Friday request."""
    trace_id: str
    timestamp: str
    original_prompt: str

    # Intent & Routing
    intent_classification: Optional[str] = None
    capability_selected: Optional[str] = None
    operation_selected: Optional[str] = None
    capability_confidence: Optional[float] = None

    # Evidence Collection
    evidence: list[EvidenceTrace] = field(default_factory=list)

    # Memory
    memories_retrieved: list[MemoryTrace] = field(default_factory=list)
    memories_selected: list[MemoryTrace] = field(default_factory=list)
    memories_rejected: list[MemoryTrace] = field(default_factory=list)

    # Workspace
    workspace_snapshot: dict = field(default_factory=dict)
    project_metadata: dict = field(default_factory=dict)
    git_metadata: dict = field(default_factory=dict)
    repository_snapshot: dict = field(default_factory=dict)
    documents_loaded: list[str] = field(default_factory=list)

    # Prompts (exact payload)
    prompt_trace: Optional[PromptTrace] = None

    # Model Response
    model_response: Optional[ModelResponseTrace] = None

    # Pipeline execution
    stages: list[StageTrace] = field(default_factory=list)

    # Overall metrics
    total_latency_seconds: float = 0.0
    success: bool = False
    error_message: Optional[str] = None

    # Context leak detection flags
    contains_conversation_history: bool = False
    contains_previous_tasks: bool = False
    contains_planner_output: bool = False
    contains_unintended_memory: bool = False
    contamination_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert trace to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert enums to strings
        for stage in data.get("stages", []):
            if "stage" in stage:
                stage["stage"] = stage["stage"] if isinstance(stage["stage"], str) else stage["stage"].value
        return data

    def to_json(self) -> str:
        """Convert trace to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def save(self, directory: str = "logs/traces") -> Path:
        """Save trace to disk."""
        trace_dir = Path(directory)
        trace_dir.mkdir(parents=True, exist_ok=True)

        filename = f"trace_{self.trace_id}.json"
        filepath = trace_dir / filename

        filepath.write_text(self.to_json())
        return filepath


class TraceContext:
    """Context manager for building a request trace."""

    def __init__(self, original_prompt: str, trace_id: Optional[str] = None):
        if trace_id is None:
            trace_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        self.trace = RequestTrace(
            trace_id=trace_id,
            timestamp=datetime.now().isoformat(),
            original_prompt=original_prompt
        )
        self.start_time = time.perf_counter()
        self.current_stage: Optional[StageTrace] = None

    def start_stage(self, stage: TraceStage, input_data: dict = None) -> None:
        """Start tracing a pipeline stage."""
        if self.current_stage is not None:
            # Finish previous stage
            self.end_stage()

        self.current_stage = StageTrace(
            stage=stage,
            start_time=time.perf_counter(),
            end_time=0.0,
            duration_seconds=0.0,
            input_data=input_data or {}
        )

    def end_stage(self, output_data: dict = None, errors: list[str] = None) -> None:
        """End current stage."""
        if self.current_stage is None:
            return

        self.current_stage.end_time = time.perf_counter()
        self.current_stage.duration_seconds = self.current_stage.end_time - self.current_stage.start_time

        if output_data:
            self.current_stage.output_data = output_data
        if errors:
            self.current_stage.errors = errors

        self.trace.stages.append(self.current_stage)
        self.current_stage = None

    def add_evidence(self, evidence_type: str, origin: str, content: Any,
                     confidence: float = 1.0, **metadata) -> None:
        """Record evidence collection."""
        content_str = str(content)
        self.trace.evidence.append(EvidenceTrace(
            type=evidence_type,
            origin=origin,
            size=len(content_str),
            summary=content_str[:200] + "..." if len(content_str) > 200 else content_str,
            confidence=confidence,
            metadata=metadata
        ))

    def add_memory(self, memory_id: str, memory_type: str, similarity: float,
                   ranking: float, importance: float, relevance: float,
                   content_preview: str, selected: bool, rejection_reason: str = None) -> None:
        """Record memory retrieval."""
        memory_trace = MemoryTrace(
            memory_id=memory_id,
            memory_type=memory_type,
            similarity_score=similarity,
            ranking_score=ranking,
            importance=importance,
            project_relevance=relevance,
            content_preview=content_preview,
            selected=selected,
            rejection_reason=rejection_reason
        )

        self.trace.memories_retrieved.append(memory_trace)
        if selected:
            self.trace.memories_selected.append(memory_trace)
        else:
            self.trace.memories_rejected.append(memory_trace)

    def set_routing(self, capability: str, operation: str, confidence: float,
                    intent: str = None) -> None:
        """Record routing decision."""
        self.trace.capability_selected = capability
        self.trace.operation_selected = operation
        self.trace.capability_confidence = confidence
        if intent:
            self.trace.intent_classification = intent

    def set_workspace_snapshot(self, workspace: dict, project: dict,
                              git: dict, repo: dict, documents: list[str]) -> None:
        """Record workspace snapshot."""
        self.trace.workspace_snapshot = workspace
        self.trace.project_metadata = project
        self.trace.git_metadata = git
        self.trace.repository_snapshot = repo
        self.trace.documents_loaded = documents

    def set_prompt_trace(self, system_prompt: str, evidence_block: str,
                        user_prompt: str, final_payload: str, token_estimate: int) -> None:
        """Record complete prompt payload."""
        self.trace.prompt_trace = PromptTrace(
            system_prompt=system_prompt,
            evidence_block=evidence_block,
            user_prompt=user_prompt,
            final_payload=final_payload,
            token_count_estimate=token_estimate
        )

        # Context leak detection
        self._detect_contamination(final_payload)

    def set_model_response(self, raw_output: str, parsed_output: Any,
                          input_tokens: int = None, output_tokens: int = None,
                          latency: float = 0.0, reasoning: dict = None) -> None:
        """Record model response."""
        self.trace.model_response = ModelResponseTrace(
            raw_output=raw_output,
            parsed_output=parsed_output,
            reasoning_metadata=reasoning or {},
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=latency
        )

    def _detect_contamination(self, payload: str) -> None:
        """Detect potential context leaks in the final payload."""
        payload_lower = payload.lower()

        # Check for conversation history markers
        conversation_markers = [
            "previous conversation",
            "earlier we discussed",
            "you mentioned",
            "in our last chat"
        ]
        if any(marker in payload_lower for marker in conversation_markers):
            self.trace.contains_conversation_history = True
            self.trace.contamination_sources.append("conversation_history")

        # Check for task history markers
        task_markers = [
            "previous task",
            "last attempt",
            "earlier attempt",
            "previous execution"
        ]
        if any(marker in payload_lower for marker in task_markers):
            self.trace.contains_previous_tasks = True
            self.trace.contamination_sources.append("previous_tasks")

        # Check for planner output leakage
        planner_markers = [
            "planner output",
            "generated plan",
            "planning result"
        ]
        if any(marker in payload_lower for marker in planner_markers):
            self.trace.contains_planner_output = True
            self.trace.contamination_sources.append("planner_output")

        # Check for unintended memory
        # Look for common memory section headers that shouldn't be there
        unintended_markers = [
            "memory:",
            "history:",
            "installs:",
            "past attempts:",
            "failed:",
            "failure:"
        ]
        # Only flag if they appear but aren't in the evidence block
        evidence_block = self.trace.prompt_trace.evidence_block if self.trace.prompt_trace else ""
        for marker in unintended_markers:
            if marker in payload_lower and marker not in evidence_block.lower():
                self.trace.contains_unintended_memory = True
                self.trace.contamination_sources.append(f"unintended_memory:{marker}")
                break

    def finalize(self, success: bool = True, error: str = None) -> RequestTrace:
        """Finalize the trace."""
        if self.current_stage is not None:
            self.end_stage()

        self.trace.total_latency_seconds = time.perf_counter() - self.start_time
        self.trace.success = success
        if error:
            self.trace.error_message = error

        return self.trace


# Global trace storage for current request
_current_trace: Optional[TraceContext] = None


def start_trace(original_prompt: str, trace_id: Optional[str] = None) -> TraceContext:
    """Start tracing a new request."""
    global _current_trace
    _current_trace = TraceContext(original_prompt, trace_id)
    return _current_trace


def get_current_trace() -> Optional[TraceContext]:
    """Get the current trace context."""
    return _current_trace


def end_trace(success: bool = True, error: str = None) -> Optional[RequestTrace]:
    """End the current trace and return it."""
    global _current_trace
    if _current_trace is None:
        return None

    trace = _current_trace.finalize(success, error)
    _current_trace = None
    return trace


def save_current_trace(directory: str = "logs/traces") -> Optional[Path]:
    """Save the current trace to disk."""
    if _current_trace is None:
        return None

    trace = _current_trace.trace
    return trace.save(directory)
