"""Operation Classifier - determines what the user wants to DO with a capability.

Phase 10.5: Classifies user intent into specific operations to distinguish
between advice ("how should I install requests?") and execution ("install requests").
"""

import re
from core.operations import Operation


class OperationClassifier:
    """Classifies user queries into operation types.

    Generic metadata-driven classification without hardcoded patterns.
    """

    # Operation signal words
    OPERATION_SIGNALS = {
        Operation.READ: [
            "current", "show", "what is", "get", "display", "view"
        ],
        Operation.LOOKUP: [
            "where is", "find", "locate", "which file"
        ],
        Operation.INSPECT: [
            "check", "status", "state", "inspect"
        ],
        Operation.EXPLAIN: [
            "explain", "why", "how does", "what does", "describe"
        ],
        Operation.SUMMARIZE: [
            "summarize", "summary", "overview", "outline"
        ],
        Operation.REVIEW: [
            "review", "audit", "analyze code", "look at", "review repository"
        ],
        Operation.COMPARE: [
            "compare", "difference", "diff", "versus", "vs"
        ],
        Operation.ANALYZE: [
            "analyze", "why is", "what's wrong", "debug"
        ],
        Operation.SEARCH: [
            "search", "grep", "find all", "search for"
        ],
        Operation.PLAN: [
            "plan", "design", "approach", "strategy", "how to"
        ],
        Operation.ADVISE: [
            "how should", "what command", "best way", "recommend",
            "should i", "what's the", "which tool", "advice"
        ],
        Operation.REMEMBER: [
            "remember", "teach", "learn", "note that"
        ],
        Operation.RECALL: [
            "recall", "what did i", "do you remember", "taught"
        ],
        Operation.REFLECT: [
            "reflect", "what went wrong", "lessons", "retrospect"
        ],
        Operation.EXECUTE: [
            "run", "execute", "do", "perform", "start", "launch"
        ],
        Operation.MODIFY: [
            "create", "modify", "edit", "update", "change", "write",
            "delete", "remove", "add", "install", "setup", "configure"
        ],
    }

    def classify(self, query: str) -> Operation:
        """Classify what operation the user wants to perform.

        Args:
            query: Natural language query

        Returns:
            Operation enum representing user intent
        """
        query_lower = query.lower().strip()

        # Score each operation based on signal words
        scores = {}
        for operation, signals in self.OPERATION_SIGNALS.items():
            score = sum(1 for signal in signals if signal in query_lower)
            if score > 0:
                scores[operation] = score

        # Special cases that override signal scoring

        # "Show me the command" / "show command" / "show the install" = ADVISE, not just READ
        if any(phrase in query_lower for phrase in [
            "show me the command", "show the command", "show command",
            "show the install", "show me how to", "show how to",
            "what command", "which command", "what's the command"
        ]):
            return Operation.ADVISE

        # "Where is" = LOOKUP, not READ
        if "where is" in query_lower or "where's" in query_lower:
            return Operation.LOOKUP

        # "How should I" / "What command" / "Best way" = ADVISE, not EXECUTE
        if any(phrase in query_lower for phrase in [
            "how should", "best way to", "what's the best"
        ]):
            return Operation.ADVISE

        # "Don't" / "Just show" = ADVISE or READ, not EXECUTE
        if any(phrase in query_lower for phrase in [
            "don't", "dont", "just show", "only show", "without"
        ]):
            # If there's also an action word, it's ADVISE
            if any(word in query_lower for word in ["install", "create", "run", "execute"]):
                return Operation.ADVISE
            return Operation.READ

        # Questions ("?") usually seek information, not execution
        if query.strip().endswith("?"):
            # But "Can you install?" is still EXECUTE if explicit
            if not any(phrase in query_lower for phrase in ["can you", "could you", "would you"]):
                # Questions are usually READ, EXPLAIN, or ADVISE
                if scores.get(Operation.EXPLAIN, 0) > 0:
                    return Operation.EXPLAIN
                if scores.get(Operation.ADVISE, 0) > 0:
                    return Operation.ADVISE
                if scores.get(Operation.RECALL, 0) > 0:
                    return Operation.RECALL
                return Operation.READ

        # Imperative without modifiers = EXECUTE
        # "Install requests" vs "How to install requests"
        imperative_verbs = ["install", "create", "run", "execute", "setup", "configure"]
        if any(query_lower.startswith(verb) for verb in imperative_verbs):
            return Operation.EXECUTE

        # Return highest scoring operation
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        # Default to READ for safety (never execute by default)
        return Operation.READ

    def requires_confirmation(self, operation: Operation) -> bool:
        """Check if operation requires user confirmation before execution."""
        return operation in {Operation.EXECUTE, Operation.MODIFY}

    def allows_execution(self, operation: Operation) -> bool:
        """Check if operation is allowed to execute tools/commands."""
        from core.operations import requires_execution
        return requires_execution(operation)
