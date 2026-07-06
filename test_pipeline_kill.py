"""Test killing running process through pipeline."""

import subprocess
import time
import os


def test_pipeline_kill():
    """Test killing via real pipeline with lowered timeout."""

    print("=== PIPELINE KILL TEST ===")
    print()

    # Create a test script that spawns sleep via pipeline
    test_script = """
import asyncio
import sys
sys.path.insert(0, '/home/lakshay/Projects/Friday')

async def test():
    from core.run import PipelineRun
    from core.intent import Intent
    from core.pipeline import run_pipeline
    import agents.planner as planner_module
    import json

    # Mock planner to return sleep command
    original = planner_module.create_plan

    async def mock_plan(task, world, health, events, retry_context):
        # Return sleep 30 command
        return [{
            "tool": "shell",
            "args": {"command": "sleep 30", "timeout": 3},
            "description": "Long running sleep"
        }]

    planner_module.create_plan = mock_plan

    # Create task
    intent = Intent(kind="task", payload={"text": "run sleep test"})
    run = PipelineRun(intent=intent)

    # Start pipeline
    print("[Starting pipeline with sleep 30, timeout=3s]")
    result = await run_pipeline(run)

    planner_module.create_plan = original

    print(f"\\nResult: {result}")
    print(f"\\nExecution log entries: {len(run.execution_log)}")
    for entry in run.execution_log:
        print(f"  - {entry['tool']}: success={entry['success']}, killed={entry.get('killed', False)}")
        if entry.get('pid'):
            print(f"    PID: {entry['pid']}")

asyncio.run(test())
"""

    with open('/tmp/test_pipeline_kill.py', 'w') as f:
        f.write(test_script)

    print("[1] Capturing ps BEFORE running pipeline:")
    subprocess.run("ps aux | grep '[s]leep 30' | head -5", shell=True)

    print("\n[2] Running pipeline (this will take ~3 seconds)...")
    result = subprocess.run(
        "cd /home/lakshay/Projects/Friday && python /tmp/test_pipeline_kill.py",
        shell=True,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])

    print("\n[3] Capturing ps AFTER pipeline completed:")
    ps_after = subprocess.run(
        "ps aux | grep '[s]leep 30' | head -5",
        shell=True,
        capture_output=True,
        text=True
    )

    if ps_after.stdout.strip():
        print("Process still running:")
        print(ps_after.stdout)
    else:
        print("Process not found (killed successfully)")


if __name__ == "__main__":
    test_pipeline_kill()
