#!/usr/bin/env python3
"""Test FileFlows API endpoints to verify which ones work."""
import asyncio
import aiohttp
import json
from typing import Any

API_BASE = "http://192.168.178.8:8585"
API_TOKEN = "29ebda24d1c44973924c84a77c1622a0"

class EndpointTester:
    def __init__(self):
        self.results = {
            "working": [],
            "not_found": [],
            "auth_error": [],
            "other_error": []
        }

    async def test_endpoint(self, session: aiohttp.ClientSession, method: str, endpoint: str, description: str = "") -> dict[str, Any]:
        """Test a single endpoint."""
        url = f"{API_BASE}/{endpoint.lstrip('/')}"
        headers = {"x-token": API_TOKEN}

        try:
            async with session.request(method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                status = response.status

                result = {
                    "endpoint": endpoint,
                    "method": method,
                    "status": status,
                    "description": description,
                    "url": url
                }

                if status == 200:
                    try:
                        data = await response.json()
                        result["response_type"] = type(data).__name__
                        if isinstance(data, dict):
                            result["keys"] = list(data.keys())[:10]
                        elif isinstance(data, list):
                            result["count"] = len(data)
                        self.results["working"].append(result)
                        print(f"✅ {method:6} {endpoint:50} -> {status} ({type(data).__name__})")
                    except:
                        text = await response.text()
                        result["response_type"] = "text"
                        result["preview"] = text[:100]
                        self.results["working"].append(result)
                        print(f"✅ {method:6} {endpoint:50} -> {status} (text)")
                elif status == 404:
                    self.results["not_found"].append(result)
                    print(f"❌ {method:6} {endpoint:50} -> 404 NOT FOUND")
                elif status in [401, 403]:
                    self.results["auth_error"].append(result)
                    print(f"🔒 {method:6} {endpoint:50} -> {status} AUTH ERROR")
                else:
                    result["error"] = f"HTTP {status}"
                    self.results["other_error"].append(result)
                    print(f"⚠️  {method:6} {endpoint:50} -> {status}")

                return result

        except asyncio.TimeoutError:
            result = {"endpoint": endpoint, "method": method, "error": "Timeout"}
            self.results["other_error"].append(result)
            print(f"⏱️  {method:6} {endpoint:50} -> TIMEOUT")
            return result
        except Exception as e:
            result = {"endpoint": endpoint, "method": method, "error": str(e)}
            self.results["other_error"].append(result)
            print(f"💥 {method:6} {endpoint:50} -> ERROR: {str(e)[:50]}")
            return result

async def main():
    tester = EndpointTester()

    async with aiohttp.ClientSession() as session:
        print("=" * 100)
        print("TESTING FILEFLOWS API ENDPOINTS")
        print("=" * 100)

        # Test currently implemented endpoints
        print("\n" + "=" * 100)
        print("1. TESTING CURRENTLY IMPLEMENTED ENDPOINTS")
        print("=" * 100)

        current_endpoints = [
            # Public endpoints
            ("GET", "remote/info/status", "Public status endpoint"),
            ("GET", "remote/info/shrinkage-groups", "Public shrinkage data"),
            ("GET", "remote/info/update-available", "Public update check"),
            ("GET", "remote/info/version", "Public version"),

            # System endpoints
            ("GET", "api/system/info", "System info (SUSPECTED WRONG)"),
            ("GET", "api/system/version", "System version"),
            ("POST", "api/system/pause", "Pause system (skip POST test)"),
            ("POST", "api/system/restart", "Restart system (skip POST test)"),

            # Settings
            ("GET", "api/settings/fileflows-status", "FileFlows status (SUSPECTED WRONG)"),
            ("GET", "api/settings", "System settings"),
            ("GET", "api/settings/ui-settings", "UI settings"),

            # Nodes
            ("GET", "api/node", "List nodes"),

            # Libraries
            ("GET", "api/library", "List libraries"),

            # Library Files
            ("GET", "api/library-file/status", "Library file status"),
            ("GET", "api/library-file/upcoming", "Upcoming files (SUSPECTED WRONG)"),
            ("GET", "api/library-file/recently-finished", "Recently finished (SUSPECTED WRONG)"),

            # Flows
            ("GET", "api/flow", "List flows"),

            # Workers
            ("GET", "api/worker", "List workers (SUSPECTED WRONG)"),

            # Tasks
            ("GET", "api/task", "List tasks"),

            # Plugins
            ("GET", "api/plugin", "List plugins"),

            # NVIDIA
            ("GET", "api/nvidia/smi", "NVIDIA GPU status"),
        ]

        for method, endpoint, desc in current_endpoints:
            if "skip" in desc.lower():
                print(f"⏭️  {method:6} {endpoint:50} -> SKIPPED ({desc})")
                continue
            await tester.test_endpoint(session, method, endpoint, desc)

        # Test NEW endpoints from documentation
        print("\n" + "=" * 100)
        print("2. TESTING NEW ENDPOINTS FROM API DOCUMENTATION")
        print("=" * 100)

        new_endpoints = [
            ("GET", "api/status", "Main status endpoint (CRITICAL)"),
            ("GET", "api/status/update-available", "Update available check"),
            ("GET", "api/node/overview", "Node overview (CRITICAL)"),
            ("GET", "api/statistics/storage-saved", "Storage statistics"),
            ("GET", "api/statistics/storage-saved-raw", "Raw storage data"),
            ("GET", "api/library-file", "Library files list"),
            ("GET", "api/library-file/list-all", "All library files"),
        ]

        for method, endpoint, desc in new_endpoints:
            await tester.test_endpoint(session, method, endpoint, desc)

        # Test alternative endpoints
        print("\n" + "=" * 100)
        print("3. TESTING ALTERNATIVE ENDPOINTS")
        print("=" * 100)

        alternative_endpoints = [
            ("GET", "api/node/list", "Node list alternative"),
            ("GET", "api/flow/list-all", "Flow list alternative"),
            ("GET", "api/library-file/find-all-libraries", "Find all libraries"),
        ]

        for method, endpoint, desc in alternative_endpoints:
            await tester.test_endpoint(session, method, endpoint, desc)

    # Print summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(f"\n✅ WORKING ENDPOINTS: {len(tester.results['working'])}")
    for r in tester.results['working']:
        response_info = r.get('response_type', 'unknown')
        if 'keys' in r:
            response_info += f" with keys: {', '.join(r['keys'][:5])}"
        elif 'count' in r:
            response_info += f" with {r['count']} items"
        print(f"  ✓ {r['method']:6} {r['endpoint']:50} -> {response_info}")

    print(f"\n❌ NOT FOUND (404): {len(tester.results['not_found'])}")
    for r in tester.results['not_found']:
        print(f"  ✗ {r['method']:6} {r['endpoint']:50}")

    print(f"\n🔒 AUTH ERRORS: {len(tester.results['auth_error'])}")
    for r in tester.results['auth_error']:
        print(f"  ! {r['method']:6} {r['endpoint']:50} -> {r['status']}")

    print(f"\n⚠️  OTHER ERRORS: {len(tester.results['other_error'])}")
    for r in tester.results['other_error']:
        print(f"  ? {r['method']:6} {r['endpoint']:50} -> {r.get('error', 'Unknown')}")

    # Save results to JSON
    with open('/Users/maximilianhammerschmid/.claude-worktrees/ha-fileflows/youthful-euclid/api_test_results.json', 'w') as f:
        json.dump(tester.results, f, indent=2)

    print(f"\n📄 Full results saved to: api_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
