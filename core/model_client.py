"""Model client: calls external LLM APIs on behalf of the orchestrator."""

import sys
import json
import time
import yaml
import httpx

_CONFIG_PATH = "config/models.yaml"

SYSTEM_PROMPT = (
    "You are Friday, a helpful personal assistant for a developer named Lakshay. "
    "Respond directly and concisely. Do not write code unless explicitly asked to. "
    "If you don't have real-time information (current date, time, live data), say so "
    "plainly in one sentence instead of raising exceptions or writing placeholder code."
)

# Load config once at module import
with open(_CONFIG_PATH) as f:
    _CONFIG = yaml.safe_load(f)

# Persistent HTTP client for connection reuse
_CLIENT = None


def _get_client():
    """Get or create the persistent HTTP client."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    return _CLIENT


async def close_client():
    """Close the persistent HTTP client on shutdown."""
    global _CLIENT
    if _CLIENT is not None:
        await _CLIENT.aclose()
        _CLIENT = None


async def call_model(text: str, route: str = "cheap_chat") -> str:
    """Send a chat prompt to the configured model backend with streaming.

    Returns the model's text reply, or the configured fallback string on failure.
    """
    try:
        routes = _CONFIG.get("routes", {})
        fallback = _CONFIG.get("fallback_response", "Friday couldn't reach a model right now.")

        if route not in routes:
            print(f"[model_client] unknown route '{route}'", file=sys.stderr)
            return fallback

        r = routes[route]
        model = r["model"]
        base_url = r["base_url"]
        api_key = r.get("api_key")
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "stream": True,
        }

        print(f"[model_client] routing to model={model} base_url={base_url}", file=sys.stderr)

        client = _get_client()
        t_start = time.perf_counter()
        t_first_token = None
        accumulated = []
        served_by_model = None

        async with client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line.strip() or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Strip "data: " prefix

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)

                    # Capture the model field from the first chunk that has it
                    if served_by_model is None and "model" in chunk:
                        served_by_model = chunk["model"]

                    # Extract content from delta
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")

                    if content:
                        if t_first_token is None:
                            t_first_token = time.perf_counter()

                        # Print chunk immediately for streaming effect
                        print(content, end="", flush=True)
                        accumulated.append(content)

                except json.JSONDecodeError:
                    # Skip malformed chunks
                    continue

        t_end = time.perf_counter()

        # Print newline after stream ends
        print()

        # Log served model
        if served_by_model:
            print(f"[model_client] response served by: {served_by_model}", file=sys.stderr)

        # Log timing breakdown
        if t_first_token is not None:
            first_token_time = t_first_token - t_start
            total_time = t_end - t_start
            print(f"[model_client] first_token: {first_token_time:.2f}s, total: {total_time:.2f}s", file=sys.stderr)

        return "".join(accumulated)

    except httpx.HTTPStatusError as e:
        print(f"[model_client] HTTP error: {e}", file=sys.stderr)
    except httpx.TimeoutException:
        print("[model_client] request timed out after 30s", file=sys.stderr)
    except httpx.RequestError as e:
        print(f"[model_client] network error: {e}", file=sys.stderr)
    except (KeyError, ValueError, OSError) as e:
        print(f"[model_client] config / parse error: {e}", file=sys.stderr)

    return fallback
