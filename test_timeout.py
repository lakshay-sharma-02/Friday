import asyncio
import httpx
import time

async def main():
    client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    t0 = time.perf_counter()
    try:
        # Connecting to a blackhole IP to force a connection timeout
        async with client.stream("POST", "http://10.255.255.1/v1/chat/completions") as resp:
            pass
    except httpx.TimeoutException:
        print(f"Timeout occurred after {time.perf_counter() - t0:.2f}s")
    except Exception as e:
        print(f"Other error after {time.perf_counter() - t0:.2f}s: {e}")

if __name__ == "__main__":
    asyncio.run(main())
