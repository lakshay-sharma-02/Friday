"""Planner agent - the single LLM call in the pipeline."""

import sys
import json
from dataclasses import asdict
from core.model_client import call_model
from tools.registry import TOOL_REGISTRY


PLANNER_SYSTEM_PROMPT = """You are a task planner that produces executable plans.

Available tools:
{tools_description}

World State context:
You have complete understanding of the system you're operating on:
- Workspace: project type, languages, build systems, git state, files
- Computer: OS, CPU, RAM, disk, battery, available developer tools
- Network: connectivity status, interfaces
- Processes: running child processes, CPU/memory usage
- Runtime: current task progress, elapsed time, retry count
- Health: system health level (healthy/warning/critical), resource usage
- Recent Events: what changed since last observation (workspace changes, git state, processes, health, network)

Use these facts to make informed decisions. Never guess about system state.

Planner Philosophy:
Specialized tools exist for a reason. Always prefer the most specific tool capable of completing the task. Generic tools are fallbacks.
Specialized tools provide validation, structured outputs, safer execution, better observability, and richer metadata. Therefore they should be preferred.

Tool Priority:
When multiple tools can accomplish the same task, prefer them in this order:
1. Dedicated domain tools: read_file, search_files, replace_in_file, list_directory, diff_files, git_status, git_diff, git_commit, http_get, download_file, etc.
2. Shell: Use when an external executable is required (e.g., build systems, package managers, compilers, language toolchains, OS commands like cargo, npm, cmake, make, pytest, go, rustc, java, docker).
3. Python: Python should be considered a convenience tool. Only use it when computation is required, custom data transformation, temporary scripting, or no dedicated tool exists and no shell command is appropriate (e.g., calculate statistics from a CSV, transform JSON into YAML). Python should NOT be used simply because it can perform filesystem operations or invoke subprocesses.

Health-aware planning:
- If health is WARNING or CRITICAL, prefer lightweight operations
- If battery is low and not charging, avoid expensive work
- If RAM/disk is nearly full, avoid resource-intensive operations
- Consider recent events when planning (e.g., if git state just changed, workspace may be dirty)

Learning from past attempts:
- If provided with relevant_past_attempts, learn from similar past tasks
- Avoid approaches that previously failed with similar intent
- Adapt successful patterns from past attempts

Rules:
- Produce ONLY valid JSON
- No markdown, no prose, no code fences
- Output must be a JSON array of steps
- Each step must have: "tool", "args", "description"
- Only use tool names from the available tools list above
- args must be a dictionary matching the tool's expected arguments
- Use the world state to understand what exists, what changed, and what is happening

Examples:
- Task: "Read file" or "Read README.md" -> Use `read_file`
- Task: "Search files" or "Search TODO" -> Use `search_files`
- Task: "Replace text" -> Use `replace_in_file`
- Task: "Git status" -> Use `git_status`
- Task: "Git commit" -> Use `git_commit`
- Task: "HTTP GET" -> Use `http_get`
- Task: "Run tests" -> Use `shell` with test command
- Task: "Build Rust" -> Use `shell` with `cargo build`
- Task: "Build Node" -> Use `shell` with `npm build`
- Task: "Python data processing" or "Analyze CSV" -> Use `python`
- Task: "Transform JSON" -> Use `python`
- Task: "Download file" or "Download URL" -> Use `download_file`

Output format:
[
  {{"tool": "git_status", "args": {{}}, "description": "Check repository status"}},
  {{"tool": "shell", "args": {{"command": "ls -la"}}, "description": "List directory contents"}}
]

Lesson extraction:
After the plan array, you MAY optionally emit ONE trailing line if you discover something genuinely non-obvious and worth remembering for future tasks:
  LESSON: <one sentence about workspace-specific constraints, tool requirements, or non-obvious patterns>

Only emit a LESSON line when:
- The task revealed a workspace-specific constraint (e.g., "shell commands need explicit cwd, relative paths fail")
- A tool requires non-standard flags or setup (e.g., "test suite needs --features full flag")
- A pattern is surprising or counter-intuitive
- Omit for trivial tasks, standard workflows, or obvious patterns

Examples of GOOD lessons:
  LESSON: This project's test suite requires cargo test --features full, plain cargo test skips half the suite.
  LESSON: Shell commands in this workspace need an explicit cwd argument, relative paths fail from daemon's working directory.

Examples where NO lesson should be emitted:
- Checking git status (standard workflow)
- Running common commands that work as expected
- Tasks with no surprises or workspace-specific quirks

If you cannot accomplish the task with available tools, return an empty array: []"""


def _build_tools_description() -> str:
    """Build description of available tools for planner prompt."""
    lines = []
    for name, spec in TOOL_REGISTRY.items():
        lines.append(f"- {name}: {spec['description']}")
        if spec['args']:
            args_desc = []
            for arg_name, arg_spec in spec['args'].items():
                req = "required" if arg_spec.get("required") else "optional"
                args_desc.append(f"  - {arg_name} ({arg_spec['type']}, {req}): {arg_spec.get('description', '')}")
            if args_desc:
                lines.extend(args_desc)
    return "\n".join(lines)


async def create_plan(
    task: str,
    world: "WorldState",
    health: "HealthStatus",
    events: list["ObservationEvent"],
    retry_context: str = "",
    memory_results: list[dict] = None
) -> tuple[list[dict], str | None]:
    """Generate a plan for the given task.

    Args:
        task: User's task description
        world: Current world state
        health: Current health status
        events: Recent observation events
        retry_context: Optional context from previous failed attempt
        memory_results: Optional relevant past attempts from memory search

    Returns:
        Tuple of (plan steps list, optional lesson string)
    """
    tools_desc = _build_tools_description()
    system_prompt = PLANNER_SYSTEM_PROMPT.format(tools_description=tools_desc)

    # Serialize world state
    world_dict = asdict(world)

    # Build health context
    health_dict = {
        "level": health.level.value,
        "reasons": health.reasons,
        "cpu_percent": health.cpu_percent,
        "ram_percent": health.ram_percent,
        "disk_percent": health.disk_percent,
        "battery_percent": health.battery_percent,
        "internet_reachable": health.internet_reachable,
    }

    # Build events context (last 10 events)
    events_list = []
    for event in events[-10:]:
        events_list.append({
            "type": event.type.value,
            "timestamp": str(event.timestamp),
            "description": event.description,
        })

    # Build memory context
    relevant_past = []
    if memory_results:
        for result in memory_results:
            entry = {
                "content": result.get("text", ""),
                "source": result.get("source", ""),
            }
            # Add source-specific context
            if result.get("source") == "runs":
                entry["status"] = result.get("status", "")
            elif result.get("source") == "notes":
                entry["note_type"] = result.get("note_source", "")
            relevant_past.append(entry)

    prompt_parts = [
        f"Task: {task}",
        f"\nWorld State: {json.dumps(world_dict, indent=2, default=str)}",
        f"\nHealth Status: {json.dumps(health_dict, indent=2)}",
        f"\nRecent Events: {json.dumps(events_list, indent=2)}",
    ]

    if relevant_past:
        prompt_parts.append(f"\nRelevant Past Attempts: {json.dumps(relevant_past, indent=2)}")

    if retry_context:
        prompt_parts.insert(0, retry_context)

    prompt = "\n".join(prompt_parts)

    try:
        # Store original system prompt, replace temporarily
        from core.model_client import SYSTEM_PROMPT as original_prompt
        import core.model_client as client_module
        client_module.SYSTEM_PROMPT = system_prompt

        response = await call_model(prompt)

        # Restore original system prompt
        client_module.SYSTEM_PROMPT = original_prompt

        # Parse JSON response
        response = response.strip()

        # Check for LESSON line at the end
        lesson = None
        lines = response.split("\n")
        if lines and lines[-1].startswith("LESSON:"):
            lesson = lines[-1][7:].strip()  # Extract lesson text
            response = "\n".join(lines[:-1]).strip()  # Remove LESSON line from plan

        # Remove markdown code fences if present
        if response.startswith("```"):
            response_lines = response.split("\n")
            response = "\n".join(response_lines[1:-1]) if len(response_lines) > 2 else response
            response = response.removeprefix("json").strip()

        plan = json.loads(response)

        if not isinstance(plan, list):
            print(f"[planner] warning: plan is not a list, got {type(plan)}", file=sys.stderr)
            return [], None

        return plan, lesson

    except json.JSONDecodeError as e:
        print(f"[planner] warning: failed to parse plan JSON: {e}", file=sys.stderr)
        print(f"[planner] raw response: {response[:200]}...", file=sys.stderr)
        return [], None
    except Exception as e:
        print(f"[planner] error: {e}", file=sys.stderr)
        return [], None

