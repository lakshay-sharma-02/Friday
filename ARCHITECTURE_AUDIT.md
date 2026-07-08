# Architecture Audit Report

This document contains the findings of a complete architectural audit of Friday, verifying whether the implementation matches the intended architecture.

## 1. Tool Registry

**Observed implementation:** `TOOL_REGISTRY` in `tools/registry.py` is a passive Python dictionary mapping tool names to schemas and handler functions. It does not execute anything itself.
**Expected architecture:** Tool Registry is a passive lookup service.
**Conclusion:** Implementation is correct. The architecture diagram showing `Executor -> Tool Registry -> Tools` accurately reflects the lookup relationship. The Executor (or Pipeline acting as Executor) retrieves the handler from the Registry, then executes the Tool.
**Recommended fix:** None required.

## 2. Memory

**Observed implementation:** `MemoryStore` is initialized independently in `core/pipeline.py`. It is queried before plan creation (`store.search(task)`), and its results are passed to the Planner alongside the World State. It is not owned by or part of `WorldState`.
**Expected architecture:** Memory is an independent subsystem.
**Conclusion:** Implementation is correct. Observation and retrieval are cleanly separated, and both are independently fed into the Planner.
**Recommended fix:** None required.

## 3. Hybrid Requests

**Observed implementation:** When a "hybrid" request (e.g., "Summarize README.md") is processed, the intent router flags it as `hybrid`. The orchestrator (`core/orchestrator.py`) runs the standard `run_pipeline(pipeline_run)`, which invokes the Planner exactly **once** to generate the tool plan (e.g., `read_file README.md`). Once execution completes, a secondary LLM call (`call_model`) is used purely to synthesize a response based on the execution log.
- Number of planner calls: 1
- Number of model calls: 2 (1 Planner, 1 Summarizer)
- Number of execution passes: 1
**Expected architecture:** Only one planner LLM call for execution decisions.
**Conclusion:** Implementation is correct. It does not perform a second planning step. The second LLM call acts only as a summarizer, preserving the single-planner invariant.
**Recommended fix:** None required.

## 4. Execution Pipeline

**Observed implementation:** The `core/pipeline.py` file completely bypasses the designated `Executor` module. It directly imports `validate_and_prepare_plan` from `core/plan_validation.py` and implements its own execution loop (`_execute_step_with_observation`). Meanwhile, `core/executor.py` contains unused legacy functions (`execute_plan`, `validate_plan`, `validate_step`) that duplicate this logic but are never called.
**Expected architecture:** `Validator -> Executor`. The Pipeline should hand off the validated plan to the Executor.
**Conclusion:** Both implementation and documentation have discrepancies. The implementation is wrong because `core/pipeline.py` has absorbed the responsibilities of the Executor, leaving dead code in `core/executor.py`. The documentation correctly conceptualizes an Executor, but the code does not reflect this separation.
**Recommended fix:** Remove the dead legacy code in `core/executor.py`. Extract `_execute_step_with_observation` and the step-execution loop from `pipeline.py` into `core/executor.py` so the Executor is genuinely responsible for execution.
**Estimated impact:** Low risk. It is a straightforward extraction and code deletion without changing behavior.

## 5. Ownership Audit

**Observed implementation:**
- **Intent Router**: Correctly owns classification, writes intent strings.
- **Planner**: Correctly owns decision-making, reads WorldState/Memory, writes Plan.
- **Validator**: Correctly owns schema checking and risk assessment (`core/plan_validation.py`).
- **Pipeline**: Owns execution looping, observation triggers, rule evaluation, and memory storage. It has absorbed Executor responsibilities.
- **Executor (`core/executor.py`)**: Owns nothing (dead code).

**Conclusion:** Implementation has responsibility leakage where `Pipeline` does too much.
**Recommended fix:** Migrate step-execution, tool handler resolution, and watchdog invocation into `Executor`.

## 6. Coupling Audit

**Observed implementation:** `core/pipeline.py` imports directly from `tools.registry` (to find handlers) instead of delegating to an Executor. It is highly coupled to Observers, Watchdog, Memory, and Tool Registry.
**Conclusion:** Implementation has hidden coupling due to the missing Executor abstraction.
**Recommended fix:** By moving execution logic into `core/executor.py`, the Pipeline will no longer need to import `TOOL_REGISTRY` or directly manage tool handler resolution, thereby decoupling the orchestrator from the tools.

## 7. Architecture Invariants

- **Planner only plans.** (Satisfied: Planner generates JSON, doesn't execute.)
- **Executor only executes.** (Violated: The component formally named `Executor` in `core/executor.py` is ignored, and `Pipeline` executes instead.)
- **Observers only observe.** (Satisfied: `inspect()` methods in observers only use non-mutating OS calls like `df`, `free`, `lscpu`).
- **Memory only remembers.** (Satisfied: Handles vector/store lookups and saves.)
- **World State only represents reality.** (Satisfied: Populated passively by observers.)
- **Validator only validates.** (Satisfied by `core/plan_validation.py`.)
- **Tool Registry only describes tools.** (Satisfied: It is a passive dictionary.)
- **Tools only perform actions.** (Satisfied.)

**Conclusion:** The only invariant violated is related to the Executor. The architectural role exists conceptually, but the intended file (`core/executor.py`) is bypassed in favor of a monolithic `pipeline.py`.
