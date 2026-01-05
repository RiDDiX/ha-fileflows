#!/usr/bin/env python3
"""Test script that simulates Home Assistant integration setup."""
import asyncio
import aiohttp
import sys

# REPLACE THESE WITH YOUR VALUES
HOST = "YOUR_IP"  # e.g., "192.168.178.8"
PORT = 8585
USERNAME = "YOUR_USERNAME"  # e.g., "riddix"
PASSWORD = "YOUR_PASSWORD"


async def test_integration_setup():
    """Simulate the exact flow that Home Assistant uses during setup."""
    if HOST == "YOUR_IP":
        print("❌ ERROR: Please edit this script and set HOST, USERNAME, and PASSWORD!")
        sys.exit(1)

    print("=" * 70)
    print("FileFlows Integration Setup Test")
    print("=" * 70)
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Username: {USERNAME}")
    print(f"Password: {'*' * len(PASSWORD)}")
    print()

    # Create session (like Home Assistant does)
    async with aiohttp.ClientSession() as session:
        base_url = f"http://{HOST}:{PORT}"

        # =====================================================================
        # STEP 1: Get Bearer token FIRST (required for ALL endpoints!)
        # =====================================================================
        print("[STEP 1] Getting Bearer token...")

        # Clean username/password
        username_clean = USERNAME.strip() or None
        password_clean = PASSWORD.strip() or None

        if not username_clean or not password_clean:
            print("  ❌ No credentials provided!")
            return

        # Get Bearer token
        print(f"  Requesting Bearer token for user: {username_clean}")
        try:
            async with session.post(
                f"{base_url}/authorize",
                json={"username": username_clean, "password": password_clean},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"  Status: {response.status}")

                if response.status == 401:
                    print(f"  ❌ Authentication failed - invalid username or password")
                    return

                if response.status != 200:
                    error_text = await response.text()
                    print(f"  ❌ Login failed: {error_text}")
                    return

                token = await response.text()
                token = token.strip().strip('"')

                if not token:
                    print(f"  ❌ Login succeeded but no token received")
                    return

                print(f"  ✅ Bearer token acquired successfully")
                print(f"  Token length: {len(token)}")
                print(f"  Token preview: {token[:20]}...{token[-20:]}")
        except Exception as err:
            print(f"  ❌ Token request error: {err}")
            return

        print()

        # =====================================================================
        # STEP 2: Test /api/status endpoint (authenticated)
        # =====================================================================
        print("[STEP 2] Testing /api/status with Bearer token...")
        try:
            async with session.get(
                f"{base_url}/api/status",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"  Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ Authenticated API access successful")
                    if data:
                        print(f"  Data keys: {list(data.keys())[:10]}")
                else:
                    print(f"  ❌ API call failed with status {response.status}")
                    return
        except Exception as err:
            print(f"  ❌ API error: {err}")
            return

        print()

        # =====================================================================
        # STEP 3: Try /remote/info/status (may require auth on your server)
        # =====================================================================
        print("[STEP 3] Testing /remote/info/status...")
        try:
            async with session.get(
                f"{base_url}/api/system/info",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"  Status: {response.status}")

                if response.status == 401:
                    print(f"  ❌ Token rejected (401) - authentication failed")
                    return

                if response.status != 200:
                    error_text = await response.text()
                    print(f"  ❌ API call failed: {error_text}")
                    return

                data = await response.json()
                print(f"  ✅ Authenticated API access successful")

                if data:
                    print(f"  Response data keys: {list(data.keys())[:10]}")
                else:
                    print(f"  ⚠️  Empty response data")
        except Exception as err:
            print(f"  ❌ API test error: {err}")
            return

        print()

        # =====================================================================
        # SUCCESS
        # =====================================================================
        print("=" * 70)
        print("✅ SUCCESS - All setup steps completed successfully!")
        print("=" * 70)
        print()
        print("The integration should work in Home Assistant with these settings:")
        print(f"  Host: {HOST}")
        print(f"  Port: {PORT}")
        print(f"  SSL: false")
        print(f"  Verify SSL: true")
        print(f"  Username: {username_clean}")
        print(f"  Password: {password_clean}")
        print()


if __name__ == "__main__":
    asyncio.run(test_integration_setup())
