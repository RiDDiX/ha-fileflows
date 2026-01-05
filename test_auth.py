#!/usr/bin/env python3
"""Test different authentication methods for FileFlows API."""
import asyncio
import aiohttp

API_BASE = "http://192.168.178.8:8585"
API_TOKEN = "29ebda24d1c44973924c84a77c1622a0"

async def test_auth_methods():
    """Test different authentication header formats."""

    async with aiohttp.ClientSession() as session:
        print("Testing different authentication methods...\n")

        auth_methods = [
            ("No auth", {}),
            ("x-token (lowercase)", {"x-token": API_TOKEN}),
            ("X-Token (capitalized)", {"X-Token": API_TOKEN}),
            ("X-TOKEN (uppercase)", {"X-TOKEN": API_TOKEN}),
            ("Authorization Bearer", {"Authorization": f"Bearer {API_TOKEN}"}),
            ("Authorization (no Bearer)", {"Authorization": API_TOKEN}),
            ("x-api-key", {"x-api-key": API_TOKEN}),
            ("API-Key", {"API-Key": API_TOKEN}),
        ]

        test_endpoint = "api/status"

        for name, headers in auth_methods:
            url = f"{API_BASE}/{test_endpoint}"
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    status = response.status
                    if status == 200:
                        print(f"✅ {name:30} -> SUCCESS (200)")
                        try:
                            data = await response.json()
                            print(f"   Response keys: {list(data.keys())[:10]}")
                        except:
                            text = await response.text()
                            print(f"   Response (text): {text[:100]}")
                    elif status == 401:
                        print(f"🔒 {name:30} -> AUTH FAILED (401)")
                    else:
                        print(f"⚠️  {name:30} -> HTTP {status}")
            except Exception as e:
                print(f"💥 {name:30} -> ERROR: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(test_auth_methods())
