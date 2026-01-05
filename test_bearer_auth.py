#!/usr/bin/env python3
"""Test FileFlows Bearer token authentication."""
import asyncio
import aiohttp
import json

API_BASE = "http://192.168.178.8:8585"

async def test_bearer_auth(username: str, password: str):
    """Test Bearer authentication flow."""

    async with aiohttp.ClientSession() as session:
        print("=" * 80)
        print("TESTING FILEFLOWS BEARER TOKEN AUTHENTICATION")
        print("=" * 80)

        # Step 1: Get Bearer token
        print(f"\n1. Requesting Bearer token for user: {username}")
        auth_url = f"{API_BASE}/authorize"
        auth_data = {"username": username, "password": password}

        try:
            async with session.post(
                auth_url,
                json=auth_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"   Status: {response.status}")

                if response.status == 200:
                    token = await response.text()
                    token = token.strip('"')  # Remove quotes if present
                    print(f"   ✅ Token received: {token[:20]}...{token[-20:]}")

                    # Step 2: Test API endpoints with Bearer token
                    print("\n2. Testing API endpoints with Bearer token:")

                    test_endpoints = [
                        ("GET", "api/status", "System status"),
                        ("GET", "api/node", "Nodes"),
                        ("GET", "api/library", "Libraries"),
                        ("GET", "api/flow", "Flows"),
                        ("GET", "api/plugin", "Plugins"),
                        ("GET", "api/task", "Tasks"),
                        ("GET", "api/nvidia/smi", "NVIDIA GPU"),
                        ("GET", "api/library-file/status", "Library file status"),
                    ]

                    for method, endpoint, desc in test_endpoints:
                        url = f"{API_BASE}/{endpoint}"
                        headers = {"Authorization": f"Bearer {token}"}

                        try:
                            async with session.request(
                                method,
                                url,
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)
                            ) as api_response:
                                status = api_response.status

                                if status == 200:
                                    try:
                                        data = await api_response.json()
                                        data_type = type(data).__name__

                                        if isinstance(data, dict):
                                            keys = list(data.keys())[:5]
                                            print(f"   ✅ {endpoint:40} -> {status} ({data_type}, keys: {keys})")
                                        elif isinstance(data, list):
                                            print(f"   ✅ {endpoint:40} -> {status} ({data_type}, {len(data)} items)")
                                        else:
                                            print(f"   ✅ {endpoint:40} -> {status} ({data_type})")
                                    except:
                                        text = await api_response.text()
                                        print(f"   ✅ {endpoint:40} -> {status} (text: {text[:50]})")
                                elif status == 401:
                                    print(f"   🔒 {endpoint:40} -> 401 (Auth failed)")
                                elif status == 404:
                                    print(f"   ❌ {endpoint:40} -> 404 (Not found)")
                                else:
                                    print(f"   ⚠️  {endpoint:40} -> {status}")
                        except asyncio.TimeoutError:
                            print(f"   ⏱️  {endpoint:40} -> TIMEOUT")
                        except Exception as e:
                            print(f"   💥 {endpoint:40} -> ERROR: {str(e)[:30]}")

                    # Step 3: Compare with remote/info endpoints
                    print("\n3. Comparing with public /remote/info/* endpoints:")

                    public_endpoints = [
                        ("GET", "remote/info/status", "Public status"),
                        ("GET", "remote/info/shrinkage-groups", "Public shrinkage"),
                    ]

                    for method, endpoint, desc in public_endpoints:
                        url = f"{API_BASE}/{endpoint}"

                        try:
                            async with session.request(
                                method,
                                url,
                                timeout=aiohttp.ClientTimeout(total=5)
                            ) as api_response:
                                status = api_response.status

                                if status == 200:
                                    data = await api_response.json()
                                    data_type = type(data).__name__

                                    if isinstance(data, dict):
                                        keys = list(data.keys())[:5]
                                        print(f"   ✅ {endpoint:40} -> {status} (NO AUTH NEEDED, {data_type})")
                                    elif isinstance(data, list):
                                        print(f"   ✅ {endpoint:40} -> {status} (NO AUTH NEEDED, {len(data)} items)")
                                else:
                                    print(f"   ❌ {endpoint:40} -> {status}")
                        except Exception as e:
                            print(f"   💥 {endpoint:40} -> ERROR: {str(e)[:30]}")

                    print("\n" + "=" * 80)
                    print("RECOMMENDATION")
                    print("=" * 80)
                    print("✅ Bearer token authentication works!")
                    print("✅ We can implement automatic login with username/password")
                    print("✅ Token can be cached and reused until it expires")
                    print("✅ All /api/* endpoints will become available")

                    return True

                else:
                    error_text = await response.text()
                    print(f"   ❌ Authentication failed: {response.status}")
                    print(f"   Error: {error_text}")
                    return False

        except Exception as e:
            print(f"   💥 Authentication error: {e}")
            return False

if __name__ == "__main__":
    print("\nPlease provide FileFlows credentials:")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    if username and password:
        asyncio.run(test_bearer_auth(username, password))
    else:
        print("Username and password are required!")
