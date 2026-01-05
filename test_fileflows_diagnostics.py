#!/usr/bin/env python3
"""Diagnostic test for FileFlows API integration."""
import asyncio
import aiohttp
import json
import sys

# Configuration - REPLACE THESE VALUES
API_BASE = "http://YOUR_FILEFLOWS_IP:YOUR_PORT"  # e.g., "http://192.168.1.100:8585"
ACCESS_TOKEN = ""  # Optional: leave empty if no token configured

async def test_endpoint(session: aiohttp.ClientSession, method: str, endpoint: str, use_auth: bool = False) -> dict:
    """Test a single endpoint."""
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    headers = {"Content-Type": "application/json"}

    if use_auth and ACCESS_TOKEN:
        headers["x-token"] = ACCESS_TOKEN

    try:
        async with session.request(method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            status = response.status

            # Try to get response data
            try:
                if "application/json" in response.headers.get("Content-Type", ""):
                    data = await response.json()
                else:
                    data = await response.text()
            except:
                data = None

            return {
                "endpoint": endpoint,
                "status": status,
                "success": status == 200,
                "data": data,
                "auth_used": use_auth and bool(ACCESS_TOKEN)
            }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": 0,
            "success": False,
            "error": str(e),
            "auth_used": use_auth and bool(ACCESS_TOKEN)
        }

async def main():
    """Run diagnostic tests."""
    print("=" * 80)
    print("FILEFLOWS API DIAGNOSTIC TEST")
    print("=" * 80)
    print(f"\nAPI Base URL: {API_BASE}")
    print(f"Access Token configured: {'Yes' if ACCESS_TOKEN and ACCESS_TOKEN != 'YOUR_ACCESS_TOKEN' else 'No'}")
    print()

    async with aiohttp.ClientSession() as session:
        results = {
            "public_endpoints": [],
            "auth_endpoints_no_token": [],
            "auth_endpoints_with_token": []
        }

        # Test 1: PUBLIC endpoints (should work without auth)
        print("=" * 80)
        print("TEST 1: PUBLIC ENDPOINTS (No Auth Required)")
        print("=" * 80)

        public_endpoints = [
            ("GET", "/remote/info/status"),
            ("GET", "/remote/info/shrinkage-groups"),
            ("GET", "/remote/info/update-available"),
            ("GET", "/remote/info/version"),
        ]

        for method, endpoint in public_endpoints:
            result = await test_endpoint(session, method, endpoint, use_auth=False)
            results["public_endpoints"].append(result)

            status_icon = "✅" if result["success"] else "❌"
            print(f"{status_icon} {method:6} {endpoint:50} -> {result['status']}")

            if result["success"] and result["data"]:
                if isinstance(result["data"], dict):
                    print(f"   Data keys: {list(result['data'].keys())[:5]}")
                elif isinstance(result["data"], list):
                    print(f"   Data: {len(result['data'])} items")

        # Test 2: AUTHENTICATED endpoints WITHOUT token
        print("\n" + "=" * 80)
        print("TEST 2: AUTHENTICATED ENDPOINTS (No Token)")
        print("=" * 80)

        auth_endpoints = [
            ("GET", "/api/status"),
            ("GET", "/api/system/info"),
            ("GET", "/api/node"),
            ("GET", "/api/library"),
            ("GET", "/api/flow"),
            ("GET", "/api/plugin"),
            ("GET", "/api/task"),
            ("GET", "/api/library-file/status"),
        ]

        for method, endpoint in auth_endpoints:
            result = await test_endpoint(session, method, endpoint, use_auth=False)
            results["auth_endpoints_no_token"].append(result)

            status_icon = "✅" if result["success"] else "❌"
            auth_icon = "🔓" if result["status"] != 401 else "🔒"
            print(f"{status_icon} {auth_icon} {method:6} {endpoint:50} -> {result['status']}")

            if result["success"] and result["data"]:
                if isinstance(result["data"], dict):
                    print(f"   Data keys: {list(result['data'].keys())[:5]}")
                elif isinstance(result["data"], list):
                    print(f"   Data: {len(result['data'])} items")

        # Test 3: AUTHENTICATED endpoints WITH token (if configured)
        if ACCESS_TOKEN and ACCESS_TOKEN != "YOUR_ACCESS_TOKEN":
            print("\n" + "=" * 80)
            print("TEST 3: AUTHENTICATED ENDPOINTS (With Token)")
            print("=" * 80)

            for method, endpoint in auth_endpoints:
                result = await test_endpoint(session, method, endpoint, use_auth=True)
                results["auth_endpoints_with_token"].append(result)

                status_icon = "✅" if result["success"] else "❌"
                print(f"{status_icon} {method:6} {endpoint:50} -> {result['status']}")

                if result["success"] and result["data"]:
                    if isinstance(result["data"], dict):
                        print(f"   Data keys: {list(result['data'].keys())[:5]}")
                    elif isinstance(result["data"], list):
                        print(f"   Data: {len(result['data'])} items")

        # ANALYSIS
        print("\n" + "=" * 80)
        print("ANALYSIS")
        print("=" * 80)

        public_working = sum(1 for r in results["public_endpoints"] if r["success"])
        auth_no_token_working = sum(1 for r in results["auth_endpoints_no_token"] if r["success"])
        auth_no_token_401 = sum(1 for r in results["auth_endpoints_no_token"] if r["status"] == 401)

        print(f"\nPublic endpoints working: {public_working}/{len(results['public_endpoints'])}")
        print(f"Authenticated endpoints (no token) working: {auth_no_token_working}/{len(results['auth_endpoints_no_token'])}")
        print(f"Authenticated endpoints returning 401 (Auth Required): {auth_no_token_401}/{len(results['auth_endpoints_no_token'])}")

        if ACCESS_TOKEN and ACCESS_TOKEN != "YOUR_ACCESS_TOKEN":
            auth_with_token_working = sum(1 for r in results["auth_endpoints_with_token"] if r["success"])
            print(f"Authenticated endpoints (with token) working: {auth_with_token_working}/{len(results['auth_endpoints_with_token'])}")

        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)

        if public_working > 0:
            print("\n✅ PUBLIC endpoints are working!")
            print("   → Integration will show basic data (version, queue, storage)")
        else:
            print("\n❌ PUBLIC endpoints are NOT working!")
            print("   → Check if FileFlows server is running and accessible")
            print("   → Verify the API_BASE URL is correct")

        if auth_no_token_401 > 0:
            print("\n🔒 Your FileFlows server REQUIRES authentication!")
            print("   → You MUST configure an access token in Home Assistant")
            print("\n   How to get an access token:")
            print("   1. Open FileFlows web UI")
            print("   2. Go to Settings → Security")
            print("   3. Create or copy an API access token")
            print("   4. Add it to your Home Assistant FileFlows integration configuration")
        elif auth_no_token_working > 0:
            print("\n🔓 Your FileFlows server does NOT require authentication!")
            print("   → No access token needed")
            print("   → Integration should show all data")

        if ACCESS_TOKEN and ACCESS_TOKEN != "YOUR_ACCESS_TOKEN":
            if auth_with_token_working > 0:
                print("\n✅ Authentication with token is working!")
                print("   → Make sure this token is configured in Home Assistant")
            else:
                print("\n❌ Authentication with token FAILED!")
                print("   → Token might be invalid or expired")
                print("   → Generate a new token in FileFlows Settings → Security")

        # Save detailed results
        with open("fileflows_diagnostic_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print("\n📄 Detailed results saved to: fileflows_diagnostic_results.json")

if __name__ == "__main__":
    if API_BASE == "http://YOUR_FILEFLOWS_IP:YOUR_PORT":
        print("❌ ERROR: Please edit the script and set API_BASE to your FileFlows server address!")
        print("   Example: API_BASE = 'http://192.168.1.100:8585'")
        sys.exit(1)

    asyncio.run(main())
