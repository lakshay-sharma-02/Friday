"""Friday: boots the event bus, orchestrator, autonomous triggers, and CLI interface."""

import asyncio
from core import EventBus, Orchestrator
from core.model_client import close_client
from interfaces import run_cli
from triggers import start_scheduler, start_fs_watch


async def main():
    """Start Friday's core components and run the CLI."""

    # Create the event transport
    bus = EventBus()

    # Create the kernel
    orchestrator = Orchestrator(bus)

    # Start the orchestrator in the background
    orchestrator_task = asyncio.create_task(orchestrator.run())

    # Start autonomous triggers in the background
    scheduler_task = asyncio.create_task(start_scheduler(bus))
    fs_watch_task = asyncio.create_task(start_fs_watch(bus, watch_path=".", pattern="Cargo.toml"))

    try:
        # Run the CLI in the foreground
        await run_cli(bus)
    finally:
        # Clean up
        orchestrator_task.cancel()
        scheduler_task.cancel()
        fs_watch_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        try:
            await fs_watch_task
        except asyncio.CancelledError:
            pass
        await close_client()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        pass
