"""Filesystem watcher trigger - fires tasks when watched files change."""

import asyncio
import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from core.bus import EventBus
from core.intent import Intent


class DebounceHandler(FileSystemEventHandler):
    """Handler that debounces rapid file changes."""

    def __init__(self, bus: EventBus, pattern: str, debounce_seconds: float = 5.0):
        self.bus = bus
        self.pattern = pattern
        self.debounce_seconds = debounce_seconds
        self.last_fire = {}
        self.loop = None

    def on_modified(self, event):
        if event.is_directory:
            return

        # Check if path matches pattern
        path = Path(event.src_path)
        if not path.match(self.pattern):
            return

        # Debounce: only fire if enough time passed since last event for this file
        now = time.time()
        last = self.last_fire.get(event.src_path, 0)
        if now - last < self.debounce_seconds:
            print(f"[fs_watch] debouncing {path.name}", file=sys.stderr)
            return

        self.last_fire[event.src_path] = now

        # Fire intent via thread-safe bridge to asyncio
        if self.loop:
            self.loop.call_soon_threadsafe(
                asyncio.create_task,
                self._fire_intent(event.src_path)
            )

    async def _fire_intent(self, changed_path: str):
        """Fire an intent for the file change."""
        task_text = f"a watched file changed: {changed_path}, report what changed"

        intent = Intent(
            source="fs_watch",
            kind="task",
            payload={"text": task_text},
            permission_ceiling="0",  # Read-only ceiling
            response_future=self.loop.create_future()
        )

        print(f"[fs_watch] firing for: {changed_path}", file=sys.stderr)
        await self.bus.publish(intent)

        # Wait for completion and log result
        try:
            result = await intent.response_future
            _log_notification("fs_watch", task_text, result)
        except Exception as e:
            _log_notification("fs_watch", task_text, f"Error: {e}")


def _log_notification(source: str, task: str, result: str):
    """Append autonomous task result to notification log."""
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    with open("friday_notifications.log", "a") as f:
        f.write(f"[{timestamp}] source={source} task={task[:50]}... result={result[:100]}...\n")


async def start_fs_watch(bus: EventBus, watch_path: str = ".", pattern: str = "Cargo.toml"):
    """Start filesystem watcher.

    Args:
        bus: EventBus to publish file-change Intents to
        watch_path: Directory to watch
        pattern: Glob pattern to match files (e.g. "*.py", "Cargo.toml")
    """
    handler = DebounceHandler(bus, pattern)
    handler.loop = asyncio.get_event_loop()

    observer = Observer()
    observer.schedule(handler, watch_path, recursive=True)
    observer.start()

    print(f"[fs_watch] watching {watch_path} for {pattern}", file=sys.stderr)

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        observer.stop()
        observer.join()
