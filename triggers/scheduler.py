"""Scheduler trigger - runs tasks at scheduled times."""

import asyncio
import sys
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.bus import EventBus
from core.intent import Intent


# Configuration
SCHEDULED_TASK = "check git status and report any uncommitted changes"
SCHEDULE_HOUR = 2  # 2am daily


async def _fire_scheduled_task(bus: EventBus):
    """Fire the scheduled task by publishing an Intent."""
    loop = asyncio.get_event_loop()

    intent = Intent(
        source="scheduler",
        kind="task",
        payload={"text": SCHEDULED_TASK},
        permission_ceiling="0",  # Read-only ceiling
        response_future=loop.create_future()
    )

    print(f"[scheduler] firing task: {SCHEDULED_TASK}", file=sys.stderr)
    await bus.publish(intent)

    # Wait for completion and log result
    try:
        result = await intent.response_future
        _log_notification("scheduler", SCHEDULED_TASK, result)
    except Exception as e:
        _log_notification("scheduler", SCHEDULED_TASK, f"Error: {e}")


def _log_notification(source: str, task: str, result: str):
    """Append autonomous task result to notification log."""
    timestamp = datetime.now().isoformat()
    with open("friday_notifications.log", "a") as f:
        f.write(f"[{timestamp}] source={source} task={task[:50]}... result={result[:100]}...\n")


async def start_scheduler(bus: EventBus):
    """Start the scheduler with daily task.

    Args:
        bus: EventBus to publish scheduled Intents to
    """
    scheduler = AsyncIOScheduler()

    # Schedule daily task at configured hour
    scheduler.add_job(
        _fire_scheduled_task,
        CronTrigger(hour=SCHEDULE_HOUR, minute=0),
        args=[bus],
        id="daily_git_check"
    )

    scheduler.start()
    print(f"[scheduler] started, daily task at {SCHEDULE_HOUR}:00", file=sys.stderr)

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        scheduler.shutdown()


async def fire_now(bus: EventBus):
    """Manually fire the scheduled task immediately (for testing)."""
    await _fire_scheduled_task(bus)
