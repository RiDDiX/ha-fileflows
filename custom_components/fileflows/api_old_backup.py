"""FileFlows API Client - Optimized for /remote/info/* endpoints."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

_LOGGER = logging.getLogger(__name__)

# Faster timeout for remote/info endpoints (they respond quickly)
DEFAULT_TIMEOUT = ClientTimeout(total=10)


class FileFlowsApiError(Exception):
    """Exception for FileFlows API errors."""


class FileFlowsConnectionError(FileFlowsApiError):
    """Exception for connection errors."""


class FileFlowsAuthError(FileFlowsApiError):
    """Exception for authentication errors."""


class FileFlowsApi:
    """FileFlows API Client - Optimized for public remote/info/* endpoints.

    This client focuses on the working /remote/info/* endpoints which provide
    all necessary monitoring data without requiring complex authentication.
    """

    def __init__(
        self,
        host: str,
        port: int = 19200,
        ssl: bool = False,
        verify_ssl: bool = True,
        access_token: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._ssl = ssl
        self._verify_ssl = verify_ssl
        # Store token, but empty string should be treated as None
        self._access_token = access_token if access_token else None
        self._session = session
        self._close_session = False

        # Build base URL - ensure it ends with /
        protocol = "https" if ssl else "http"
        self._base_url = f"{protocol}://{host}:{port}/"

        _LOGGER.info("FileFlows API initialized: %s (using /remote/info/* endpoints)", self._base_url)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            if self._ssl:
                connector = aiohttp.TCPConnector(ssl=self._verify_ssl)
            else:
                connector = aiohttp.TCPConnector()
            self._session = aiohttp.ClientSession(connector=connector)
            self._close_session = True
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and self._close_session:
            await self._session.close()
            self._session = None

    async def _fetch(self, endpoint: str, method: str = "GET", json_data: Any = None) -> Any:
        """
        Fetch data from FileFlows - matching Fenrus implementation.
        
        Fenrus code:
        ```javascript
        fetch(args, url) {
            let prefix = args.url;
            if(prefix.endsWith('/') === false)
                prefix += '/';
            url = prefix + url;
            if(!args.properties["apiToken"])
                return args.fetch(url).data;
            return args.fetch({
                url: url,
                method: 'GET',
                headers: {
                    'x-token': args.properties['apiToken']                
                }            
            }).data;
        }
        ```
        """
        session = await self._get_session()
        
        # Build URL - endpoint should NOT have leading slash (like Fenrus)
        # Remove leading slash if present
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        
        url = f"{self._base_url}{endpoint}"
        
        _LOGGER.debug("Fetching: %s %s", method, url)
        
        # Build headers - EXACTLY like Fenrus
        # Fenrus only adds x-token header, nothing else for GET
        headers: dict[str, str] = {}
        
        if self._access_token:
            headers["x-token"] = self._access_token
            _LOGGER.debug("Using x-token authentication")
        
        # Only add Content-Type for requests with body
        if json_data is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with session.request(
                method,
                url,
                json=json_data if json_data is not None else None,
                headers=headers if headers else None,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                _LOGGER.debug("Response: %s %s", response.status, response.reason)
                
                if response.status == 401:
                    raise FileFlowsAuthError("Authentication failed (401)")
                if response.status == 403:
                    raise FileFlowsAuthError("Access forbidden (403)")
                if response.status == 404:
                    _LOGGER.debug("Endpoint not found: %s", endpoint)
                    return None
                
                response.raise_for_status()

                # Handle empty responses
                if response.status == 204:
                    return None

                text = await response.text()
                if not text:
                    return None
                
                # Try to parse as JSON
                try:
                    import json
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text

        except ClientResponseError as err:
            _LOGGER.error("API error %s: %s", err.status, err.message)
            raise FileFlowsApiError(f"API error: {err.status}") from err
        except ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            raise FileFlowsConnectionError(f"Connection failed: {err}") from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Request timeout for %s", url)
            raise FileFlowsConnectionError("Request timeout") from err

    # =========================================================================
    # Connection Test - Uses PUBLIC endpoint (exactly like Fenrus test method)
    # =========================================================================
    async def test_connection(self) -> bool:
        """
        Test connection to FileFlows.
        
        Fenrus test method:
        ```javascript
        test(args){        
            let data = this.fetch(args, 'remote/info/status');
            args.log('data: ' + (data === null ? 'null' : JSON.stringify(data)));
            return isNaN(data.processed) === false;          
        }
        ```
        """
        try:
            data = await self._fetch("remote/info/status")
            _LOGGER.debug("Test connection data: %s", data)
            
            if data is None:
                _LOGGER.error("Test connection: No data returned")
                return False
            
            # Fenrus checks: isNaN(data.processed) === false
            # So we check if 'processed' is a number
            if isinstance(data, dict):
                processed = data.get("processed")
                if processed is not None and isinstance(processed, (int, float)):
                    _LOGGER.info("Test connection successful - processed: %s", processed)
                    return True
                # Also accept if queue is present
                queue = data.get("queue")
                if queue is not None and isinstance(queue, (int, float)):
                    _LOGGER.info("Test connection successful - queue: %s", queue)
                    return True
            
            _LOGGER.error("Test connection: Invalid data format")
            return False
            
        except Exception as err:
            _LOGGER.error("Test connection failed: %s", err)
            return False

    # =========================================================================
    # PUBLIC Endpoints (/remote/info/*) - No auth required
    # These are the same endpoints Fenrus uses
    # =========================================================================
    
    async def get_remote_status(self) -> dict[str, Any]:
        """
        Get status from public endpoint.
        
        Fenrus: this.fetch(args, 'remote/info/status')
        Returns: {queue, processing, processed, time, processingFiles[]}
        """
        result = await self._fetch("remote/info/status")
        return result if isinstance(result, dict) else {}

    async def get_remote_shrinkage(self) -> list[dict[str, Any]]:
        """
        Get shrinkage groups from public endpoint.
        
        Fenrus: this.fetch(args, 'remote/info/shrinkage-groups')
        Returns: [{Library, OriginalSize, FinalSize}, ...]
        """
        result = await self._fetch("remote/info/shrinkage-groups")
        return result if isinstance(result, list) else []

    async def get_remote_update_available(self) -> bool:
        """
        Check if update is available.
        
        Fenrus: this.fetch(args, 'remote/info/update-available')
        Returns: {UpdateAvailable: bool}
        """
        try:
            result = await self._fetch("remote/info/update-available")
            if isinstance(result, dict):
                return result.get("UpdateAvailable", False) is True
            return False
        except FileFlowsApiError:
            return False

    async def get_version(self) -> str:
        """Get FileFlows version."""
        try:
            # Try public endpoint first
            result = await self._fetch("remote/info/version")
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("Version", "Unknown")
            
            # Fall back to authenticated endpoint
            result = await self._fetch("api/system/version")
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("Version", "Unknown")
            
            return "Unknown"
        except FileFlowsApiError:
            return "Unknown"

    # =========================================================================
    # System Control Endpoints - POST/PUT operations for control
    # These still use /api/* but are only called when user triggers an action
    # =========================================================================

    async def pause_system(self, minutes: int = 0) -> bool:
        """Pause the system."""
        try:
            data = {"Minutes": minutes} if minutes > 0 else None
            await self._fetch("api/system/pause", method="POST", json_data=data)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to pause: %s", err)
            return False

    async def resume_system(self) -> bool:
        """Resume the system."""
        try:
            await self._fetch("api/system/pause", method="POST", json_data={"Minutes": -1})
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to resume: %s", err)
            return False

    async def restart_system(self) -> bool:
        """Restart FileFlows server."""
        try:
            await self._fetch("api/system/restart", method="POST")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to restart: %s", err)
            return False

    # =========================================================================
    # Library Control Endpoints
    # =========================================================================

    async def rescan_libraries(self, uids: list[str] | None = None) -> bool:
        """Rescan libraries."""
        try:
            if uids:
                await self._fetch("api/library/rescan", method="PUT", json_data=uids)
            else:
                await self._fetch("api/library/rescan-enabled", method="POST")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to rescan: %s", err)
            return False

    async def rescan_all_libraries(self) -> bool:
        """Rescan all enabled libraries."""
        return await self.rescan_libraries()

    # =========================================================================
    # Combined Data Fetch for Coordinator - OPTIMIZED
    # Only fetches from working /remote/info/* endpoints
    # =========================================================================
    async def get_all_data(self) -> dict[str, Any]:
        """Get all data needed for sensors from /remote/info/* endpoints.

        This method ONLY uses the working public endpoints that respond quickly
        and reliably. All /api/* endpoints that timeout or fail have been removed.
        """
        data: dict[str, Any] = {
            "remote_status": {},
            "shrinkage_groups": [],
            "update_available": False,
            "version": "Unknown",
        }

        # Fetch all working endpoints in parallel for better performance
        try:
            results = await asyncio.gather(
                self.get_remote_status(),
                self.get_remote_shrinkage(),
                self.get_remote_update_available(),
                self.get_version(),
                return_exceptions=True,
            )

            # Process results
            if not isinstance(results[0], Exception):
                data["remote_status"] = results[0]
            else:
                _LOGGER.warning("Could not get remote status: %s", results[0])

            if not isinstance(results[1], Exception):
                data["shrinkage_groups"] = results[1]
            else:
                _LOGGER.debug("Could not get shrinkage: %s", results[1])

            if not isinstance(results[2], Exception):
                data["update_available"] = results[2]
            else:
                _LOGGER.debug("Could not get update info: %s", results[2])

            if not isinstance(results[3], Exception):
                data["version"] = results[3]
            else:
                _LOGGER.debug("Could not get version: %s", results[3])

        except Exception as err:
            _LOGGER.error("Error fetching FileFlows data: %s", err)

        return data
