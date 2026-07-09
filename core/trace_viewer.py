"""Trace Viewer - CLI for inspecting request traces.

Provides commands to view and analyze Friday request traces.
"""

import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def load_trace(trace_path: str) -> dict:
    """Load a trace file."""
    path = Path(trace_path)
    if not path.exists():
        raise FileNotFoundError(f"Trace not found: {trace_path}")

    return json.loads(path.read_text())


def find_latest_trace(directory: str = "logs/traces") -> Optional[Path]:
    """Find the most recent trace file."""
    trace_dir = Path(directory)
    if not trace_dir.exists():
        return None

    traces = list(trace_dir.glob("trace_*.json"))
    if not traces:
        return None

    # Sort by modification time
    return max(traces, key=lambda p: p.stat().st_mtime)


def print_trace_summary(trace: dict) -> None:
    """Print a high-level summary of the trace."""
    print("=" * 80)
    print(f"TRACE: {trace['trace_id']}")
    print(f"Time: {trace['timestamp']}")
    print(f"Success: {trace['success']}")
    print(f"Total Latency: {trace['total_latency_seconds']:.3f}s")
    print("=" * 80)

    print(f"\nOriginal Prompt: {trace['original_prompt']}")

    # Routing
    if trace.get('capability_selected'):
        print(f"\nCapability: {trace['capability_selected']}")
        print(f"Operation: {trace['operation_selected']}")
        print(f"Confidence: {trace.get('capability_confidence', 0):.2f}")

    # Error
    if trace.get('error_message'):
        print(f"\nError: {trace['error_message']}")


def print_pipeline_stages(trace: dict) -> None:
    """Print pipeline stage breakdown."""
    stages = trace.get('stages', [])
    if not stages:
        print("\nNo pipeline stages recorded.")
        return

    print("\n" + "=" * 80)
    print("PIPELINE STAGES")
    print("=" * 80)

    for stage in stages:
        stage_name = stage['stage']
        duration = stage['duration_seconds']
        errors = stage.get('errors', [])

        print(f"\n{stage_name}: {duration:.3f}s")

        if errors:
            print("  Errors:")
            for error in errors:
                print(f"    - {error}")


def print_evidence(trace: dict) -> None:
    """Print evidence collection details."""
    evidence = trace.get('evidence', [])
    if not evidence:
        print("\nNo evidence collected.")
        return

    print("\n" + "=" * 80)
    print("EVIDENCE COLLECTED")
    print("=" * 80)

    # Group by type
    by_type = {}
    for item in evidence:
        etype = item['type']
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(item)

    for etype, items in by_type.items():
        print(f"\n{etype.upper()} ({len(items)} items):")
        for item in items:
            print(f"  - {item['origin']}: {item['size']} bytes")
            print(f"    {item['summary']}")


def print_memory(trace: dict) -> None:
    """Print memory retrieval details."""
    retrieved = trace.get('memories_retrieved', [])
    selected = trace.get('memories_selected', [])
    rejected = trace.get('memories_rejected', [])

    print("\n" + "=" * 80)
    print("MEMORY")
    print("=" * 80)

    print(f"\nRetrieved: {len(retrieved)}")
    print(f"Selected: {len(selected)}")
    print(f"Rejected: {len(rejected)}")

    if selected:
        print("\nSELECTED MEMORIES:")
        for mem in selected:
            print(f"  - {mem['memory_type']} (ID: {mem['memory_id']})")
            print(f"    Similarity: {mem['similarity_score']:.3f}")
            print(f"    Ranking: {mem['ranking_score']:.3f}")
            print(f"    Preview: {mem['content_preview'][:100]}...")

    if rejected:
        print("\nREJECTED MEMORIES:")
        for mem in rejected[:5]:  # Show first 5
            print(f"  - {mem['memory_type']} (ID: {mem['memory_id']})")
            print(f"    Reason: {mem.get('rejection_reason', 'unknown')}")


def print_prompt(trace: dict) -> None:
    """Print the complete prompt payload."""
    prompt_trace = trace.get('prompt_trace')
    if not prompt_trace:
        print("\nNo prompt trace recorded.")
        return

    print("\n" + "=" * 80)
    print("PROMPT PAYLOAD")
    print("=" * 80)

    print("\nSYSTEM PROMPT:")
    print("-" * 40)
    print(prompt_trace['system_prompt'][:500] + "..." if len(prompt_trace['system_prompt']) > 500 else prompt_trace['system_prompt'])

    print("\n\nEVIDENCE BLOCK:")
    print("-" * 40)
    print(prompt_trace['evidence_block'][:500] + "..." if len(prompt_trace['evidence_block']) > 500 else prompt_trace['evidence_block'])

    print("\n\nUSER PROMPT:")
    print("-" * 40)
    print(prompt_trace['user_prompt'])

    print(f"\n\nToken Estimate: {prompt_trace['token_count_estimate']}")


def print_full_payload(trace: dict) -> None:
    """Print the COMPLETE final payload sent to the model."""
    prompt_trace = trace.get('prompt_trace')
    if not prompt_trace:
        print("\nNo prompt trace recorded.")
        return

    print("\n" + "=" * 80)
    print("COMPLETE FINAL PAYLOAD")
    print("=" * 80)
    print(prompt_trace['final_payload'])
    print("=" * 80)


def print_model_response(trace: dict) -> None:
    """Print model response details."""
    response = trace.get('model_response')
    if not response:
        print("\nNo model response recorded.")
        return

    print("\n" + "=" * 80)
    print("MODEL RESPONSE")
    print("=" * 80)

    print("\nRAW OUTPUT:")
    print("-" * 40)
    print(response['raw_output'][:500] + "..." if len(response['raw_output']) > 500 else response['raw_output'])

    if response.get('input_tokens'):
        print(f"\nInput Tokens: {response['input_tokens']}")
    if response.get('output_tokens'):
        print(f"Output Tokens: {response['output_tokens']}")
    print(f"Latency: {response['latency_seconds']:.3f}s")


def print_contamination(trace: dict) -> None:
    """Print context leak detection results."""
    sources = trace.get('contamination_sources', [])

    print("\n" + "=" * 80)
    print("CONTEXT LEAK DETECTION")
    print("=" * 80)

    if not sources:
        print("\n✓ No contamination detected")
        return

    print(f"\n✗ CONTAMINATION DETECTED: {len(sources)} source(s)")

    if trace.get('contains_conversation_history'):
        print("  - Contains conversation history")
    if trace.get('contains_previous_tasks'):
        print("  - Contains previous tasks")
    if trace.get('contains_planner_output'):
        print("  - Contains planner output")
    if trace.get('contains_unintended_memory'):
        print("  - Contains unintended memory")

    print("\nSources:")
    for source in sources:
        print(f"  - {source}")


def search_payload(trace: dict, *keywords: str) -> None:
    """Search for keywords in the final payload."""
    prompt_trace = trace.get('prompt_trace')
    if not prompt_trace:
        print("\nNo prompt trace recorded.")
        return

    payload = prompt_trace['final_payload'].lower()

    print("\n" + "=" * 80)
    print("PAYLOAD SEARCH")
    print("=" * 80)

    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in payload:
            # Count occurrences
            count = payload.count(keyword_lower)
            print(f"\n✓ Found '{keyword}': {count} occurrence(s)")

            # Show context
            idx = payload.find(keyword_lower)
            start = max(0, idx - 50)
            end = min(len(payload), idx + len(keyword_lower) + 50)
            context = payload[start:end]
            print(f"  Context: ...{context}...")
        else:
            print(f"\n✗ Not found: '{keyword}'")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Friday Request Trace Viewer")
    parser.add_argument("command", choices=[
        "summary", "pipeline", "evidence", "memory",
        "prompt", "payload", "response", "contamination", "search", "full"
    ], help="What to display")
    parser.add_argument("--trace", help="Path to trace file (default: latest)")
    parser.add_argument("--keywords", nargs="+", help="Keywords to search for (with 'search' command)")

    args = parser.parse_args()

    # Load trace
    if args.trace:
        trace_path = args.trace
    else:
        latest = find_latest_trace()
        if not latest:
            print("No traces found in logs/traces/", file=sys.stderr)
            sys.exit(1)
        trace_path = str(latest)
        print(f"Using latest trace: {trace_path}", file=sys.stderr)

    try:
        trace = load_trace(trace_path)
    except Exception as e:
        print(f"Error loading trace: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute command
    if args.command == "summary":
        print_trace_summary(trace)
    elif args.command == "pipeline":
        print_trace_summary(trace)
        print_pipeline_stages(trace)
    elif args.command == "evidence":
        print_trace_summary(trace)
        print_evidence(trace)
    elif args.command == "memory":
        print_trace_summary(trace)
        print_memory(trace)
    elif args.command == "prompt":
        print_trace_summary(trace)
        print_prompt(trace)
    elif args.command == "payload":
        print_full_payload(trace)
    elif args.command == "response":
        print_trace_summary(trace)
        print_model_response(trace)
    elif args.command == "contamination":
        print_trace_summary(trace)
        print_contamination(trace)
    elif args.command == "search":
        if not args.keywords:
            print("Error: --keywords required for search command", file=sys.stderr)
            sys.exit(1)
        print_trace_summary(trace)
        search_payload(trace, *args.keywords)
    elif args.command == "full":
        # Full report
        print_trace_summary(trace)
        print_pipeline_stages(trace)
        print_evidence(trace)
        print_memory(trace)
        print_prompt(trace)
        print_model_response(trace)
        print_contamination(trace)


if __name__ == "__main__":
    main()
