#!/usr/bin/env python3
"""
Performance Profiling Script
Analyzes API endpoints, database queries, and identifies bottlenecks
"""

import asyncio
import statistics
import time
from typing import Dict, List

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_ITERATIONS = 10


class PerformanceProfiler:
    """Profile API endpoint performance"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: Dict[str, List[float]] = {}

    async def profile_endpoint(
        self, method: str, endpoint: str, headers: Dict = None, json_data: Dict = None
    ) -> float:
        """Profile a single endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()

            try:
                if method == "GET":
                    response = await client.get(f"{self.base_url}{endpoint}", headers=headers)
                elif method == "POST":
                    response = await client.post(
                        f"{self.base_url}{endpoint}", headers=headers, json=json_data
                    )
                else:
                    raise ValueError(f"Unsupported method: {method}")

                response.raise_for_status()
                duration = time.time() - start

                # Extract server processing time if available
                process_time = response.headers.get("X-Process-Time")
                if process_time:
                    print(
                        f"  {method} {endpoint}: {duration:.3f}s (server: {process_time}s) - {response.status_code}"
                    )
                else:
                    print(f"  {method} {endpoint}: {duration:.3f}s - {response.status_code}")

                return duration

            except Exception as e:
                print(f"  ERROR {method} {endpoint}: {str(e)}")
                return -1.0

    async def run_profile(
        self, name: str, method: str, endpoint: str, headers: Dict = None, json_data: Dict = None
    ):
        """Run multiple iterations and collect statistics"""
        print(f"\nProfiling {name}...")
        durations = []

        for i in range(TEST_ITERATIONS):
            duration = await self.profile_endpoint(method, endpoint, headers, json_data)
            if duration > 0:
                durations.append(duration)

        if durations:
            self.results[name] = durations
            avg = statistics.mean(durations)
            median = statistics.median(durations)
            stdev = statistics.stdev(durations) if len(durations) > 1 else 0
            min_time = min(durations)
            max_time = max(durations)

            print(f"\n{name} Statistics:")
            print(f"  Average: {avg:.3f}s")
            print(f"  Median:  {median:.3f}s")
            print(f"  StdDev:  {stdev:.3f}s")
            print(f"  Min:     {min_time:.3f}s")
            print(f"  Max:     {max_time:.3f}s")

    def print_summary(self):
        """Print summary of all profiling results"""
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)

        if not self.results:
            print("No results to display")
            return

        # Sort by average response time
        sorted_results = sorted(
            self.results.items(), key=lambda x: statistics.mean(x[1]), reverse=True
        )

        print(f"\n{'Endpoint':<40} {'Avg':<10} {'Median':<10} {'Max':<10}")
        print("-" * 80)

        for name, durations in sorted_results:
            avg = statistics.mean(durations)
            median = statistics.median(durations)
            max_time = max(durations)

            status = "🔴" if avg > 1.0 else "🟡" if avg > 0.5 else "🟢"
            print(f"{status} {name:<38} {avg:.3f}s    {median:.3f}s    {max_time:.3f}s")

        print("\n" + "=" * 80)
        print("Legend: 🟢 Fast (<0.5s) | 🟡 Moderate (0.5-1s) | 🔴 Slow (>1s)")
        print("=" * 80)


async def main():
    """Run performance profiling"""
    profiler = PerformanceProfiler(API_BASE_URL)

    # Test endpoints (adjust based on your authentication)
    endpoints = [
        # Public endpoints
        ("Health Check", "GET", "/health", None, None),
        ("Root", "GET", "/", None, None),
        # Add more endpoints here after authentication
    ]

    print("Starting performance profiling...")
    print(f"Base URL: {API_BASE_URL}")
    print(f"Iterations per endpoint: {TEST_ITERATIONS}")

    for name, method, endpoint, headers, json_data in endpoints:
        await profiler.run_profile(name, method, endpoint, headers, json_data)

    profiler.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
