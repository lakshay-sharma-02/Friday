# Phase 6D: Plan Validation & Execution Reliability

## Objective Completed
Successfully implemented deterministic plan validation, tool execution guards, plan repair, risk analysis, and error reporting without introducing any additional LLM calls.

## Summary of Changes
1. **Plan Validation & Repair**: 
   - `core/plan_validation.py` acts as the single source of truth for validation against the `TOOL_REGISTRY`.
   - Structural issues (malformed plans, unknown tools, missing required fields) are deterministically rejected.
   - Minor errors (tool name casing, unused unknown fields, missing optional `args` objects) are automatically repaired.
   
2. **Risk Analysis**:
   - Every tool execution is classified dynamically based on risk (LOW, MEDIUM, HIGH).
   - This metadata is injected into the execution log, fulfilling the executor's requirements for risk-awareness without altering runtime behaviour immediately.

3. **Execution Guards**:
   - Built a comprehensive execution guard via `verify_execution_guards`.
   - Verified before *every* step in `core/pipeline.py`:
     - Tool exists in `TOOL_REGISTRY`
     - Plan arguments conform to expectations
     - Proper permissions (e.g., ceiling limitations, non-interactive shell bypass)
     - Target workspace validation (`cwd` checking)
     - Execution prerequisites (e.g., ensuring `git_status` doesn't fire outside of a git repository)

4. **Testing**:
   - `test_plan_validation.py` tests all deterministic behaviors including valid plans, malformed structs, mismatched arguments, missing paths, repair capabilities, risk propagation, and the newly implemented `test_execution_guards`.

The `pipeline.py` agent architecture remains unmodified; the executor was safely protected behind the new validation and execution guarding facade.
