"""Intent router for classifying requests."""
import re

def route_intent(text: str) -> str:
    """Classify user input into chat, task, or hybrid."""
    text_lower = text.lower()
    
    # Task indicators
    task_patterns = [
        r'\bread\b', r'\bopen\b', r'\bshow\b', r'\bsearch\b', r'\bfind\b',
        r'\breplace\b', r'\bwrite\b', r'\bcreate\b', r'\bdelete\b',
        r'\blist\b', r'\brun\b', r'\bexecute\b', r'\bbuild\b',
        r'\bcompile\b', r'\bcommit\b', r'\bgit\b', r'\bdiff\b',
        r'\brename\b', r'\bmove\b', r'\bcopy\b'
    ]
    
    # Explain/summarize indicators
    explain_patterns = [
        r'\bexplain\b', r'\bsummarize\b', r'\bwhat\b', r'\bhow\b', r'\bwhy\b'
    ]
    
    # File/workspace indicators
    file_patterns = [
        r'\b[\w-]+\.(py|md|txt|json|yaml|yml|toml|rs|js|ts|html|css|sh|ini|cfg|conf)\b',
        r'\breadme\b', r'\blicense\b', r'\btodo\b', r'\bfile[s]?\b',
        r'\bfolder[s]?\b', r'\bdirector(y|ies)\b', r'\bconfig\b', r'\bmain\b'
    ]
    
    has_task = any(re.search(p, text_lower) for p in task_patterns)
    has_explain = any(re.search(p, text_lower) for p in explain_patterns)
    has_file = any(re.search(p, text_lower) for p in file_patterns)
    
    if has_explain and has_file:
        return "hybrid"
    elif has_task or has_file:
        if has_explain and not has_file:
            return "chat"
        return "task"
    else:
        return "chat"
