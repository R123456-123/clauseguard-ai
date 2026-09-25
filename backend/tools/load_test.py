"""Small async HTTP load test for health or API endpoints.

Examples:
    python tools/load_test.py --url http://localhost:8000/health
    python tools/load_test.py --url https://api.example.com/health --requests 100 --concurrency 10
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx


async def run_request(client: httpx.AsyncClient, url: str) -> tuple[int, float]:
    started = time.perf_counter()
    response = await client.get(url)
    return response.status_code, time.perf_counter() - started


async def main(url: str, request_count: int, concurrency: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=15) as client:
        async def bounded_request() -> tuple[int, float]:
            async with semaphore:
                return await run_request(client, url)

        results = await asyncio.gather(
            *(bounded_request() for _ in range(request_count)),
            return_exceptions=True,
        )

    successful = [result for result in results if isinstance(result, tuple)]
    failures = len(results) - len(successful)
    durations = [duration for _, duration in successful]
    status_counts: dict[int, int] = {}
    for status, _ in successful:
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"requests={request_count} concurrency={concurrency}")
    print(f"statuses={status_counts} transport_failures={failures}")
    if durations:
        print(
            f"latency_ms_avg={statistics.mean(durations) * 1000:.1f} "
            f"p95_ms={sorted(durations)[max(0, int(len(durations) * 0.95) - 1)] * 1000:.1f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000/health")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(main(args.url, args.requests, args.concurrency))