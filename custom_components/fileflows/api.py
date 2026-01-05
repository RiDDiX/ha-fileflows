"""FileFlows API Client with Bearer Token Authentication."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = ClientTimeout(total=30)
TOKEN_CACHE_DURATION = timedelta(hours=23)  # Token typically valid for 24h, refresh before expiry

# =============================================================================
# Public Endpoints (no auth required) - used by Fenrus
# =============================================================================
REMOTE_STATUS = "/remote/info/status"
REMOTE_SHRINKAGE = "/remote/info/shrinkage-groups"
REMOTE_UPDATE_AVAILABLE = "/remote/info/update-available"
REMOTE_VERSION = "/remote/info/version"

# =============================================================================
# Authenticated API Endpoints
# =============================================================================
API_STATUS = "/api/status"
API_SYSTEM_VERSION = "/api/system/version"
API_SYSTEM_INFO = "/api/system/info"
API_SYSTEM_PAUSE = "/api/system/pause"
API_SYSTEM_RESTART = "/api/system/restart"
API_SETTINGS_FILEFLOWS_STATUS = "/api/settings/fileflows-status"
API_NODES = "/api/node"
API_LIBRARIES = "/api/library"
API_LIBRARY_STATE = "/api/library/state"
API_LIBRARY_RESCAN = "/api/library/rescan"
API_LIBRARY_RESCAN_ENABLED = "/api/library/rescan-enabled"
API_LIBRARY_FILE_STATUS = "/api/library-file/status"
API_LIBRARY_FILE_UPCOMING = "/api/library-file/upcoming"
API_LIBRARY_FILE_RECENTLY_FINISHED = "/api/library-file/recently-finished"
API_LIBRARY_FILE_REPROCESS = "/api/library-file/reprocess"
API_LIBRARY_FILE_UNHOLD = "/api/library-file/unhold"
API_FLOWS = "/api/flow"
API_WORKERS = "/api/worker"
API_TASKS = "/api/task"
API_PLUGINS = "/api/plugin"
API_NVIDIA_SMI = "/api/nvidia/smi"
API_STATISTICS_STORAGE_SAVED = "/api/statistics/storage-saved"


class FileFlowsApiError(Exception):
    """Exception for FileFlows API errors."""


class FileFlowsConnectionError(FileFlowsApiError):
    """Exception for connection errors."""


class FileFlowsAuthError(FileFlowsApiError):
    """Exception for authentication errors."""


class FileFlowsApi:
    """FileFlows API Client with Bearer Token Authentication."""

    def __init__(
        self,
        host: str,
        port: int = 8585,
        ssl: bool = False,
        verify_ssl: bool = True,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            host: FileFlows server hostname/IP
            port: FileFlows server port (default 8585)
            ssl: Use HTTPS instead of HTTP
            verify_ssl: Verify SSL certificates
            username: Username for Bearer token authentication (optional)
            password: Password for Bearer token authentication (optional)
            session: Existing aiohttp session (optional)
        """
        self._host = host
        self._port = port
        self._ssl = ssl
        self._verify_ssl = verify_ssl
        self._username = username
        self._password = password
        self._session = session
        self._close_session = False

        # Bearer token management
        self._bearer_token: str | None = None
        self._token_expires_at: datetime | None = None

        protocol = "https" if ssl else "http"
        self._base_url = f"{protocol}://{host}:{port}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            connector = aiohttp.TCPConnector(ssl=self._verify_ssl if self._ssl else None)
            self._session = aiohttp.ClientSession(connector=connector)
            self._close_session = True
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and self._close_session:
            await self._session.close()
            self._session = None

    async def _get_bearer_token(self) -> str | None:
        """Get Bearer token, login if needed or token expired.

        Returns:
            Bearer token string or None if auth not configured
        """
        # No credentials configured - can't authenticate
        if not self._username or not self._password:
            return None

        # Check if we have a valid cached token
        if self._bearer_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                _LOGGER.debug("Using cached Bearer token")
                return self._bearer_token

        # Need to login and get new token
        _LOGGER.debug("Acquiring new Bearer token for user: %s", self._username)

        session = await self._get_session()
        url = f"{self._base_url}/authorize"

        try:
            async with session.post(
                url,
                json={"username": self._username, "password": self._password},
                headers={"Content-Type": "application/json"},
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status == 401:
                    raise FileFlowsAuthError("Login failed - invalid username or password")

                response.raise_for_status()

                # Token is returned as plain text with quotes
                token = await response.text()
                token = token.strip().strip('"')  # Remove quotes and whitespace

                if not token:
                    raise FileFlowsAuthError("Login succeeded but no token received")

                # Cache the token
                self._bearer_token = token
                self._token_expires_at = datetime.now() + TOKEN_CACHE_DURATION

                _LOGGER.info("Bearer token acquired successfully")
                return token

        except ClientResponseError as err:
            _LOGGER.error("Login failed: HTTP %s", err.status)
            raise FileFlowsAuthError(f"Login failed: {err.status}") from err
        except ClientError as err:
            _LOGGER.error("Connection error during login: %s", err)
            raise FileFlowsConnectionError(f"Login connection failed: {err}") from err

    def _get_headers(self, use_auth: bool = True, bearer_token: str | None = None) -> dict[str, str]:
        """Get request headers.

        Args:
            use_auth: Whether to include authentication
            bearer_token: Bearer token to use (if available)

        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Add Bearer token if provided
        if use_auth and bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | list | None = None,
        params: dict[str, Any] | None = None,
        use_auth: bool = True,
    ) -> Any:
        """Make a request to the API with automatic Bearer token handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/api/status")
            data: JSON data for request body
            params: URL query parameters
            use_auth: Whether to use Bearer token authentication

        Returns:
            Response data (dict, list, or string)
        """
        session = await self._get_session()
        url = f"{self._base_url}{endpoint}"

        # Get Bearer token if authentication is requested and credentials are available
        bearer_token = None
        if use_auth:
            bearer_token = await self._get_bearer_token()
            if bearer_token:
                _LOGGER.debug("Using Bearer auth for: %s", endpoint)

        headers = self._get_headers(use_auth, bearer_token)

        _LOGGER.debug("Requesting %s %s", method, url)

        try:
            async with session.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                _LOGGER.debug("Response status: %s", response.status)

                if response.status == 401:
                    # Token might be expired, try to refresh once
                    if bearer_token and endpoint.startswith("/api"):
                        _LOGGER.warning("401 error, token might be expired. Clearing cache and retrying once...")
                        self._bearer_token = None
                        self._token_expires_at = None

                        # Retry once with fresh token
                        bearer_token = await self._get_bearer_token()
                        if bearer_token:
                            headers = self._get_headers(use_auth, bearer_token)
                            async with session.request(
                                method, url, json=data, params=params, headers=headers, timeout=DEFAULT_TIMEOUT
                            ) as retry_response:
                                if retry_response.status == 401:
                                    raise FileFlowsAuthError("Authentication failed - check credentials")
                                retry_response.raise_for_status()
                                return await self._parse_response(retry_response)
                        else:
                            raise FileFlowsAuthError("Authentication required but no credentials configured")
                    else:
                        raise FileFlowsAuthError("Authentication failed")

                if response.status == 403:
                    raise FileFlowsAuthError("Access forbidden")

                response.raise_for_status()

                return await self._parse_response(response)

        except ClientResponseError as err:
            _LOGGER.error("API response error for %s: %s", endpoint, err)
            raise FileFlowsApiError(f"API error: {err.status}") from err
        except ClientError as err:
            _LOGGER.error("Connection error for %s: %s", endpoint, err)
            raise FileFlowsConnectionError(f"Connection failed: {err}") from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Request timeout for %s", endpoint)
            raise FileFlowsConnectionError("Request timeout") from err

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Any:
        """Parse API response.

        Args:
            response: aiohttp response object

        Returns:
            Parsed response data
        """
        # Handle empty responses
        if response.status == 204:
            return None

        content_type = response.headers.get("Content-Type", "")
        text = await response.text()

        if not text:
            return None

        if "application/json" in content_type:
            return await response.json()

        # Try to parse as JSON anyway
        try:
            import json
            return json.loads(text)
        except:
            return text

    async def _get(
        self, endpoint: str, params: dict[str, Any] | None = None, use_auth: bool = True
    ) -> Any:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params, use_auth=use_auth)

    async def _post(
        self, endpoint: str, data: dict[str, Any] | list | None = None, use_auth: bool = True
    ) -> Any:
        """Make a POST request."""
        return await self._request("POST", endpoint, data=data, use_auth=use_auth)

    async def _put(
        self, endpoint: str, data: dict[str, Any] | list | None = None, use_auth: bool = True
    ) -> Any:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, data=data, use_auth=use_auth)

    async def _delete(
        self, endpoint: str, data: dict[str, Any] | list | None = None, use_auth: bool = True
    ) -> Any:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, data=data, use_auth=use_auth)

    # =========================================================================
    # Connection Test - Uses PUBLIC endpoint (no auth)
    # =========================================================================
    async def test_connection(self) -> bool:
        """Test connection to FileFlows.

        If credentials are configured, uses /api/status (requires auth).
        Otherwise tries /remote/info/status (public).
        """
        try:
            # If we have credentials, use authenticated /api/status endpoint
            if self._username and self._password:
                _LOGGER.debug("Testing connection with /api/status (authenticated)")
                result = await self._get(API_STATUS, use_auth=True)
            else:
                _LOGGER.debug("Testing connection with /remote/info/status (no auth)")
                result = await self._get(REMOTE_STATUS, use_auth=False)

            # Validate result
            if not isinstance(result, dict):
                _LOGGER.warning("Connection test returned non-dict: %s", type(result))
                return False

            # Check if we got valid data (queue should be present)
            if "queue" in result:
                _LOGGER.debug("Connection test successful, queue=%s", result.get("queue"))
                return True

            _LOGGER.warning("Connection test returned dict without 'queue' key")
            return False

        except FileFlowsApiError as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    # =========================================================================
    # Remote Endpoints - Use Bearer auth if credentials are available
    # =========================================================================
    async def get_remote_status(self) -> dict[str, Any]:
        """Get status from remote endpoint.

        Uses Bearer auth if credentials configured, otherwise no auth.
        Returns: {queue, processing, processed, time, processingFiles[]}
        """
        # Use auth if credentials are available
        use_auth = bool(self._username and self._password)
        result = await self._get(REMOTE_STATUS, use_auth=use_auth)
        return result if isinstance(result, dict) else {}

    async def get_remote_shrinkage(self) -> list[dict[str, Any]]:
        """Get shrinkage groups from remote endpoint.

        Uses Bearer auth if credentials configured.
        Returns: [{Library, OriginalSize, FinalSize}, ...]
        """
        use_auth = bool(self._username and self._password)
        result = await self._get(REMOTE_SHRINKAGE, use_auth=use_auth)
        return result if isinstance(result, list) else []

    async def get_remote_update_available(self) -> bool:
        """Check if update is available from remote endpoint.

        Uses Bearer auth if credentials configured.
        """
        try:
            use_auth = bool(self._username and self._password)
            result = await self._get(REMOTE_UPDATE_AVAILABLE, use_auth=use_auth)
            if isinstance(result, dict):
                return result.get("UpdateAvailable", False)
            return False
        except FileFlowsApiError:
            return False

    async def get_remote_version(self) -> str:
        """Get version from remote endpoint.

        Uses Bearer auth if credentials configured.
        """
        try:
            use_auth = bool(self._username and self._password)
            result = await self._get(REMOTE_VERSION, use_auth=use_auth)
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("Version", "Unknown")
            return "Unknown"
        except FileFlowsApiError:
            return "Unknown"

    # =========================================================================
    # Authenticated Endpoints - Require Bearer token authentication
    # =========================================================================
    
    # System Endpoints
    async def get_version(self) -> str:
        """Gets the version of FileFlows.

        If credentials are available, uses /api/system/version.
        Otherwise tries /remote/info/version.
        """
        # If we have credentials, use authenticated endpoint
        if self._username and self._password:
            try:
                result = await self._get(API_SYSTEM_VERSION)
                if isinstance(result, str):
                    return result
                return result.get("Version", "Unknown") if result else "Unknown"
            except FileFlowsApiError:
                pass  # Fall through to remote endpoint

        # Try public endpoint
        version = await self.get_remote_version()
        return version if version != "Unknown" else "Unknown"

    async def get_system_info(self) -> dict[str, Any]:
        """Gets system information (memory, CPU)."""
        try:
            return await self._get(API_SYSTEM_INFO)
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get system info: %s", err)
            return {}

    async def pause_system(self, minutes: int = 0) -> bool:
        """Pause the system. minutes=0 means indefinitely."""
        try:
            await self._post(API_SYSTEM_PAUSE, {"Minutes": minutes} if minutes > 0 else None)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to pause system: %s", err)
            return False

    async def resume_system(self) -> bool:
        """Resume the system (unpause)."""
        try:
            await self._post(API_SYSTEM_PAUSE, {"Minutes": -1})
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to resume system: %s", err)
            return False

    async def restart_system(self) -> bool:
        """Restart FileFlows server."""
        try:
            await self._post(API_SYSTEM_RESTART)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to restart system: %s", err)
            return False

    async def get_fileflows_status(self) -> dict[str, Any]:
        """Gets the system status of FileFlows."""
        try:
            return await self._get(API_SETTINGS_FILEFLOWS_STATUS)
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get fileflows status: %s", err)
            return {}

    # Node Endpoints
    async def get_nodes(self) -> list[dict[str, Any]]:
        """Gets all processing nodes."""
        try:
            result = await self._get(API_NODES)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get nodes: %s", err)
            return []

    async def set_node_state(self, uid: str, enabled: bool) -> bool:
        """Set state of a processing node."""
        try:
            await self._put(f"{API_NODES}/state/{uid}?enable={str(enabled).lower()}")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to set node state: %s", err)
            return False

    async def enable_node(self, uid: str) -> bool:
        """Enable a processing node."""
        return await self.set_node_state(uid, True)

    async def disable_node(self, uid: str) -> bool:
        """Disable a processing node."""
        return await self.set_node_state(uid, False)

    # Library Endpoints
    async def get_libraries(self) -> list[dict[str, Any]]:
        """Gets all libraries."""
        try:
            result = await self._get(API_LIBRARIES)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get libraries: %s", err)
            return []

    async def set_library_state(self, uid: str, enabled: bool) -> bool:
        """Set the enable state for a library."""
        try:
            await self._put(f"{API_LIBRARY_STATE}/{uid}?enable={str(enabled).lower()}")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to set library state: %s", err)
            return False

    async def enable_library(self, uid: str) -> bool:
        """Enable a library."""
        return await self.set_library_state(uid, True)

    async def disable_library(self, uid: str) -> bool:
        """Disable a library."""
        return await self.set_library_state(uid, False)

    async def rescan_libraries(self, uids: list[str] | None = None) -> bool:
        """Rescan libraries."""
        try:
            if uids:
                await self._put(API_LIBRARY_RESCAN, uids)
            else:
                await self._post(API_LIBRARY_RESCAN_ENABLED)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to rescan libraries: %s", err)
            return False

    async def rescan_all_libraries(self) -> bool:
        """Rescan all enabled libraries."""
        return await self.rescan_libraries()

    # Library File Endpoints
    async def get_library_file_status(self) -> dict[str, Any]:
        """Gets the library status overview."""
        try:
            return await self._get(API_LIBRARY_FILE_STATUS)
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get library file status: %s", err)
            return {}

    async def get_upcoming_files(self) -> list[dict[str, Any]]:
        """Get next 10 upcoming files to process."""
        try:
            result = await self._get(API_LIBRARY_FILE_UPCOMING)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get upcoming files: %s", err)
            return []

    async def get_recently_finished(self) -> list[dict[str, Any]]:
        """Gets the last 10 successfully processed files."""
        try:
            result = await self._get(API_LIBRARY_FILE_RECENTLY_FINISHED)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get recently finished: %s", err)
            return []

    async def reprocess_files(self, uids: list[str]) -> bool:
        """Reprocess library files."""
        try:
            await self._post(API_LIBRARY_FILE_REPROCESS, uids)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to reprocess files: %s", err)
            return False

    async def reprocess_file(self, uid: str) -> bool:
        """Reprocess a single library file."""
        return await self.reprocess_files([uid])

    async def unhold_files(self, uids: list[str]) -> bool:
        """Unhold library files."""
        try:
            await self._post(API_LIBRARY_FILE_UNHOLD, uids)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to unhold files: %s", err)
            return False

    # Flow Endpoints
    async def get_flows(self) -> list[dict[str, Any]]:
        """Get all flows."""
        try:
            result = await self._get(API_FLOWS)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get flows: %s", err)
            return []

    async def set_flow_state(self, uid: str, enabled: bool) -> bool:
        """Sets the enabled state of a flow."""
        try:
            await self._put(f"{API_FLOWS}/state/{uid}?enable={str(enabled).lower()}")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to set flow state: %s", err)
            return False

    async def enable_flow(self, uid: str) -> bool:
        """Enable a flow."""
        return await self.set_flow_state(uid, True)

    async def disable_flow(self, uid: str) -> bool:
        """Disable a flow."""
        return await self.set_flow_state(uid, False)

    # Worker Endpoints
    async def get_workers(self) -> list[dict[str, Any]]:
        """Get all running flow executors."""
        try:
            result = await self._get(API_WORKERS)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get workers: %s", err)
            return []

    async def abort_worker(self, uid: str) -> bool:
        """Abort work."""
        try:
            await self._delete(f"{API_WORKERS}/{uid}")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to abort worker: %s", err)
            return False

    async def abort_worker_by_file(self, file_uid: str) -> bool:
        """Abort work by library file."""
        try:
            await self._delete(f"{API_WORKERS}/by-file/{file_uid}")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to abort worker by file: %s", err)
            return False

    # Task Endpoints
    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get all scheduled tasks."""
        try:
            result = await self._get(API_TASKS)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get tasks: %s", err)
            return []

    async def run_task(self, uid: str) -> bool:
        """Runs a scheduled task now."""
        try:
            await self._post(f"{API_TASKS}/run/{uid}")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to run task: %s", err)
            return False

    # Plugin Endpoints
    async def get_plugins(self) -> list[dict[str, Any]]:
        """Get list of all plugins."""
        try:
            result = await self._get(API_PLUGINS)
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get plugins: %s", err)
            return []

    # NVIDIA Endpoints
    async def get_nvidia_smi(self) -> dict[str, Any]:
        """Gets the NVIDIA SMI data."""
        try:
            result = await self._get(API_NVIDIA_SMI)
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError:
            return {}

    # Statistics Endpoints
    async def get_storage_saved(self) -> dict[str, Any]:
        """Get storage saved statistics from /api/statistics/storage-saved.

        Returns aggregated storage savings data.
        """
        try:
            result = await self._get(API_STATISTICS_STORAGE_SAVED)
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get storage saved: %s", err)
            return {}

    # =========================================================================
    # Combined Data Fetch for Coordinator
    # =========================================================================
    async def get_all_data(self) -> dict[str, Any]:
        """Get all data needed for sensors.
        
        Uses PUBLIC endpoints for basic data (no auth required),
        and AUTHENTICATED endpoints for extended data.
        """
        data: dict[str, Any] = {
            # From public endpoints (always available)
            "remote_status": {},
            "shrinkage_groups": [],
            "update_available": False,
            "version": "Unknown",
            # From authenticated endpoints (may require token)
            "system_info": {},
            "fileflows_status": {},
            "nodes": [],
            "libraries": [],
            "flows": [],
            "workers": [],
            "tasks": [],
            "plugins": [],
            "upcoming_files": [],
            "recently_finished": [],
            "library_file_status": {},
            "nvidia": {},
            "storage_saved_stats": {},  # From /api/statistics/storage-saved
        }

        # =================================================================
        # STATUS ENDPOINT - Use /api/status if auth available, else /remote/info/status
        # =================================================================

        # Status - primary source for queue/processing info
        try:
            # Use /api/status if we have credentials (more reliable)
            if self._username and self._password:
                _LOGGER.debug("Fetching status from /api/status (authenticated)")
                data["remote_status"] = await self._get(API_STATUS, use_auth=True)
            else:
                _LOGGER.debug("Fetching status from /remote/info/status (public)")
                data["remote_status"] = await self.get_remote_status()
            _LOGGER.debug("Status data: %s", data["remote_status"])
        except FileFlowsApiError as err:
            _LOGGER.warning("Could not get status: %s", err)

        # Storage savings - use /api/statistics/storage-saved if auth available
        try:
            if self._username and self._password:
                _LOGGER.debug("Fetching storage savings from /api/statistics/storage-saved")
                data["storage_saved_stats"] = await self.get_storage_saved()
                # Also try old shrinkage endpoint for backward compatibility
                try:
                    data["shrinkage_groups"] = await self.get_remote_shrinkage()
                except FileFlowsApiError:
                    pass
            else:
                _LOGGER.debug("Fetching shrinkage from /remote/info/shrinkage-groups")
                data["shrinkage_groups"] = await self.get_remote_shrinkage()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get storage data: %s", err)

        # Update available
        try:
            data["update_available"] = await self.get_remote_update_available()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get update info: %s", err)

        # Version
        try:
            data["version"] = await self.get_version()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get version: %s", err)

        # =================================================================
        # AUTHENTICATED ENDPOINTS (require token if auth is enabled)
        # =================================================================

        # System info (CPU, Memory)
        try:
            data["system_info"] = await self.get_system_info()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get system info (auth required?): %s", err)

        # FileFlows status
        try:
            data["fileflows_status"] = await self.get_fileflows_status()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get fileflows status: %s", err)

        # Nodes
        try:
            data["nodes"] = await self.get_nodes()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get nodes: %s", err)

        # Libraries
        try:
            data["libraries"] = await self.get_libraries()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get libraries: %s", err)

        # Flows
        try:
            data["flows"] = await self.get_flows()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get flows: %s", err)

        # Workers
        try:
            data["workers"] = await self.get_workers()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get workers: %s", err)

        # Tasks
        try:
            data["tasks"] = await self.get_tasks()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get tasks: %s", err)

        # Plugins
        try:
            data["plugins"] = await self.get_plugins()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get plugins: %s", err)

        # Library file status
        try:
            data["library_file_status"] = await self.get_library_file_status()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get library file status: %s", err)

        # Upcoming files
        try:
            data["upcoming_files"] = await self.get_upcoming_files()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get upcoming files: %s", err)

        # Recently finished
        try:
            data["recently_finished"] = await self.get_recently_finished()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get recently finished: %s", err)

        # NVIDIA SMI (optional)
        try:
            data["nvidia"] = await self.get_nvidia_smi()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get nvidia info: %s", err)

        return data
