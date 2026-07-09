#!/usr/bin/env python3
"""Friday trace CLI - Convenience commands for trace inspection."""

import sys
import argparse
from pathlib import Path

# Add Friday to path
sys.path.insert(0, str(Path(__file__).parent))

from core.trace_viewer import (
    load_trace,
    find_latest_trace,
    print_trace_summary,
    print_pipeline_stages,
    print_evidence,
    print_memory,
    print_prompt,
    print_full_payload,
    print_model_response,
    print_contamination,
    search_payload
)


def cmd_trace(args):
    """Show trace summary."""
    trace_path = args.trace or find_latest_trace()
    if not trace_path:
        print("No traces found", file=sys.stderr)
        return 1

    if not args.trace:
        print(f"Using latest trace: {trace_path}", file=sys.stderr)

    trace = load_trace(str(trace_path))
    print_trace_summary(trace)
    print_pipeline_stages(trace)
    return 0


def cmd_debug_last(args):
    """Debug the last request."""
    latest = find_latest_trace()
    if not latest:
        print("No traces found", file=sys.stderr)
        return 1

    print(f"Debugging: {latest}", file=sys.stderr)
    trace = load_trace(str(latest))

    # Full debug view
    print_trace_summary(trace)
    print_pipeline_stages(trace)
    print_evidence(trace)
    print_memory(trace)
    print_contamination(trace)

    # Auto-search for suspicious keywords
    suspicious = [
        "requests", "pip", "uv", "install", "failed", "failure",
        "history", "memory", "previous", "past"
    ]

    print("\n" + "=" * 80)
    print("AUTO-SEARCH FOR SUSPICIOUS KEYWORDS")
    print("=" * 80)

    search_payload(trace, *suspicious)
    return 0


def cmd_payload(args):
    """Show complete payload."""
    trace_path = args.trace or find_latest_trace()
    if not trace_path:
        print("No traces found", file=sys.stderr)
        return 1

    trace = load_trace(str(trace_path))
    print_full_payload(trace)
    return 0


def cmd_search(args):
    """Search payload for keywords."""
    trace_path = args.trace or find_latest_trace()
    if not trace_path:
        print("No traces found", file=sys.stderr)
        return 1

    if not args.keywords:
        print("Error: --keywords required", file=sys.stderr)
        return 1

    trace = load_trace(str(trace_path))
    print_trace_summary(trace)
    search_payload(trace, *args.keywords)
    return 0


def cmd_list(args):
    """List all traces."""
    trace_dir = Path("logs/traces")
    if not trace_dir.exists():
        print("No traces directory found", file=sys.stderr)
        return 1

    traces = sorted(trace_dir.glob("trace_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not traces:
        print("No traces found")
        return 0

    print(f"Found {len(traces)} trace(s):\n")

    for trace_path in traces[:20]:  # Show last 20
        try:
            trace = load_trace(str(trace_path))
            timestamp = trace.get('timestamp', 'unknown')
            success = "✓" if trace.get('success') else "✗"
            capability = trace.get('capability_selected', 'unknown')
            prompt = trace.get('original_prompt', '')[:60]

            print(f"{success} {timestamp} [{capability}]")
            print(f"   {prompt}...")
            print(f"   {trace_path.name}")
            print()
        except Exception as e:
            print(f"Error loading {trace_path.name}: {e}", file=sys.stderr)

    if len(traces) > 20:
        print(f"... and {len(traces) - 20} more")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Friday Request Trace CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  friday trace                  # Show summary of latest trace
  friday debug-last             # Full debug view of latest trace
  friday payload                # Show complete payload sent to model
  friday search requests pip    # Search for keywords in payload
  friday list                   # List all traces
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # trace command
    trace_parser = subparsers.add_parser('trace', help='Show trace summary')
    trace_parser.add_argument('--trace', help='Path to specific trace file')

    # debug-last command
    debug_parser = subparsers.add_parser('debug-last', help='Debug latest request')

    # payload command
    payload_parser = subparsers.add_parser('payload', help='Show complete payload')
    payload_parser.add_argument('--trace', help='Path to specific trace file')

    # search command
    search_parser = subparsers.add_parser('search', help='Search payload for keywords')
    search_parser.add_argument('keywords', nargs='+', help='Keywords to search for')
    search_parser.add_argument('--trace', help='Path to specific trace file')

    # list command
    list_parser = subparsers.add_parser('list', help='List all traces')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'trace': cmd_trace,
        'debug-last': cmd_debug_last,
        'payload': cmd_payload,
        'search': cmd_search,
        'list': cmd_list,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
