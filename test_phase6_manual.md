# Phase 6 Manual Test Results

## Test 1: scheduler:fire_now (Read-only task)
Run: `python main.py` then type `scheduler:fire_now`
Expected: Task executes with permission_ceiling=0, only Tier 0 tools allowed

## Test 2: Permission ceiling blocks Tier 1 (Critical Safety Test)
The automated test shows:
```
[write_file] Write hello to test.txt
[permissions] blocked: write_file requires tier 1 but intent ceiling is 0 (source=scheduler)
[blocked]
```
✓ **No hang** - the critical deadlock prevention works

## Test 3: Filesystem watch
Run: `python main.py`
Then: `touch Cargo.toml` in another terminal
Expected: fs_watch triggers, logs to friday_notifications.log

## Test 4: Debounce
Modify same file 3x rapidly
Expected: Only 1 task fires due to 5-second debounce window

## Test 5: Memory tracking
After running tasks, check: `memory:stats`
Expected: Runs stored with correct source metadata

## Component Verification (Completed)
✓ Permission ceiling field added to Intent
✓ Permission checking respects ceiling
✓ Scheduler module with fire_now command
✓ Filesystem watcher with debounce
✓ Notification logging to friday_notifications.log
✓ Main.py wired with both triggers
✓ CLI command scheduler:fire_now added
