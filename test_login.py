#!/usr/bin/env python3
"""Quick test for Bearer token login."""
import asyncio
import aiohttp
import sys

# REPLACE THESE WITH YOUR VALUES
API_BASE = "http://YOUR_IP:YOUR_PORT"  # e.g., "http://192.168.1.100:8585"
USERNAME = "your_username"
PASSWORD = "your_password"

async def test_login():
    """Test Bearer token login."""
    if API_BASE == "http://YOUR_IP:YOUR_PORT":
        print("❌ ERROR: Please edit this script and set your FileFlows details!")
        sys.exit(1)

    print(f"Testing login to: {API_BASE}")
    print(f"Username: {USERNAME}")
    print(f"Password: {'*' * len(PASSWORD)}")
    print()

    async with aiohttp.ClientSession() as session:
        # Step 1: Try to get Bearer token
        url = f"{API_BASE}/authorize"
        print(f"POST {url}")

        try:
            async with session.post(
                url,
                json={"username": USERNAME, "password": PASSWORD},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                print(f"Response Status: {response.status}")
                print(f"Response Headers: {dict(response.headers)}")

                if response.status == 200:
                    token = await response.text()
                    token = token.strip().strip('"')
                    print(f"\n✅ SUCCESS! Bearer token received:")
                    print(f"Token: {token[:20]}...{token[-20:]}")
                    print(f"Token length: {len(token)}")

                    # Step 2: Test token with an API endpoint
                    print(f"\nTesting token with /api/status...")
                    test_url = f"{API_BASE}/api/status"

                    async with session.get(
                        test_url,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as test_response:
                        print(f"API Status Response: {test_response.status}")

                        if test_response.status == 200:
                            data = await test_response.json()
                            print(f"✅ API call successful!")
                            print(f"Response data keys: {list(data.keys())[:10]}")
                        else:
                            error = await test_response.text()
                            print(f"❌ API call failed: {error}")

                elif response.status == 401:
                    error = await response.text()
                    print(f"\n❌ AUTHENTICATION FAILED!")
                    print(f"Error: {error}")
                    print(f"\nPlease check:")
                    print(f"  - Username is correct: {USERNAME}")
                    print(f"  - Password is correct")
                    print(f"  - You can log into FileFlows Web UI with these credentials")
                else:
                    error = await response.text()
                    print(f"\n❌ Unexpected response!")
                    print(f"Error: {error}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print(f"\nPlease check:")
            print(f"  - FileFlows is running")
            print(f"  - API_BASE URL is correct: {API_BASE}")
            print(f"  - You can access FileFlows Web UI")

if __name__ == "__main__":
    asyncio.run(test_login())
