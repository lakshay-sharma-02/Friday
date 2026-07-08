"""Fast path handlers for simple queries that bypass the planner."""

import sys
from datetime import datetime
from typing import Optional


_GREETINGS = {
    "hi", "hello", "hey", "good morning", "good afternoon",
    "good evening", "howdy", "greetings", "yo"
}

_FAREWELLS = {
    "bye", "goodbye", "see you", "see ya", "later",
    "catch you later", "take care", "farewell"
}

_THANKS = {
    "thanks", "thank you", "thx", "ty", "appreciate it"
}


def is_fast_path(text: str) -> bool:
    """Check if a request can be handled by the fast path."""
    text_lower = text.strip().lower()

    # Simple greetings
    if text_lower in _GREETINGS:
        return True

    # Simple farewells
    if text_lower in _FAREWELLS:
        return True

    # Simple thanks
    if text_lower in _THANKS:
        return True

    # Time queries
    if text_lower in ("what time is it", "what's the time", "current time"):
        return True

    # Date queries
    if text_lower in ("what date is it", "what's the date", "today's date", "current date"):
        return True

    # Identity queries
    if text_lower in ("who are you", "what are you", "what's your name"):
        return True

    return False


def handle_fast_path(text: str) -> Optional[str]:
    """Handle simple queries without invoking the planner.

    Returns response string if handled, None otherwise.
    """
    text_lower = text.strip().lower()

    # Greetings
    if text_lower in _GREETINGS:
        return "Hi there."

    # Farewells
    if text_lower in _FAREWELLS:
        return "Goodbye."

    # Thanks
    if text_lower in _THANKS:
        return "You're welcome."

    # Time queries
    if text_lower in ("what time is it", "what's the time", "current time"):
        now = datetime.now()
        return f"It's {now.strftime('%I:%M %p')}."

    # Date queries
    if text_lower in ("what date is it", "what's the date", "today's date", "current date"):
        today = datetime.now()
        return f"Today is {today.strftime('%A, %B %d, %Y')}."

    # Identity queries
    if text_lower in ("who are you", "what are you", "what's your name"):
        return "I'm Friday, your personal assistant."

    return None
