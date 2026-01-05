"""FileFlows API Client with Bearer Token Authentication."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = ClientTimeout(total=10)
TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)  # Refresh token 5 minutes before expiry


class FileFlowsApiError(Exception):
    """Exception for FileFlows API errors."""


class FileFlowsConnectionError(FileFlowsApiError):
    """Exception for connection errors."""


class FileFlowsAuthError(FileFlowsApiError):
    """Exception for authentication errors."""


class FileFlowsApi:
    """FileFlows API Client with automatic Bearer token authentication.

    Supports both authenticated (/api/*) and public (/remote/info/*) endpoints.
    Automatically handles Bearer token login, caching, and refresh.
    """

    def __init__(
        self,
        host: str,
        port: int = 19200,
        ssl: bool = False,
        verify_ssl: bool = True,
        username: str | None = None,
        password: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            host: FileFlows server hostname/IP
            port: FileFlows server port
            ssl: Use HTTPS
            verify_ssl: Verify SSL certificates
            username: FileFlows username (optional, for authenticated endpoints)
            password: FileFlows password (optional, for authenticated endpoints)
            session: Existing aiohttp session (optional)
        """
        self._host = host
        self._port = port
        self._ssl = ssl
        self._verify_ssl = verify_ssl
        self._username = username if username else None
        self._password = password if password else None
        self._session = session
        self._close_session = False

        # Bearer token management
        self._bearer_token: str | None = None
        self._token_expiry: datetime | None = None

        # Build base URL
        protocol = "https" if ssl else "http"
        self._base_url = f"{protocol}://{host}:{port}/"

        auth_mode = "authenticated" if (username and password) else "public"
        _LOGGER.info(
            "FileFlows API initialized: %s (mode: %s)",
            self._base_url,
            auth_mode,
        )

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

    async def _get_bearer_token(self) -> str | None:
        """Get Bearer token, login if needed.

        Returns:
            Bearer token string or None if auth not configured
        """
        # Check if we have credentials
        if not self._username or not self._password:
            return None

        # Check if current token is still valid
        if self._bearer_token and self._token_expiry:
            if datetime.now() < self._token_expiry - TOKEN_EXPIRY_BUFFER:
                return self._bearer_token

        # Need to login
        _LOGGER.debug("Acquiring new Bearer token for user: %s", self._username)

        session = await self._get_session()
        auth_url = f"{self._base_url}authorize"
        auth_data = {
            "username": self._username,
            "password": self._password,
        }

        try:
            async with session.post(
                auth_url,
                json=auth_data,
                headers={"Content-Type": "application/json"},
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status == 200:
                    token = await response.text()
                    # Remove quotes if present
                    token = token.strip('"')

                    self._bearer_token = token
                    # Assume token valid for 24 hours (typical JWT expiry)
                    self._token_expiry = datetime.now() + timedelta(hours=24)

                    _LOGGER.info("Bearer token acquired successfully")
                    return self._bearer_token
                else:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Authentication failed: %s - %s",
                        response.status,
                        error_text,
                    )
                    raise FileFlowsAuthError(
                        f"Authentication failed: {response.status}"
                    )

        except ClientError as err:
            _LOGGER.error("Connection error during authentication: %s", err)
            raise FileFlowsConnectionError(f"Auth connection failed: {err}") from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Authentication timeout")
            raise FileFlowsConnectionError("Auth timeout") from err

    async def _fetch(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: Any = None,
        require_auth: bool = True,
    ) -> Any:
        """Fetch data from FileFlows with automatic Bearer auth.

        Args:
            endpoint: API endpoint (without leading slash)
            method: HTTP method
            json_data: JSON payload for POST/PUT requests
            require_auth: Whether this endpoint requires authentication

        Returns:
            Parsed JSON response or text
        """
        session = await self._get_session()

        # Remove leading slash if present
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]

        url = f"{self._base_url}{endpoint}"

        # Build headers
        headers: dict[str, str] = {}

        # Add Bearer token if auth required and configured
        if require_auth:
            try:
                token = await self._get_bearer_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    _LOGGER.debug("Using Bearer auth for: %s", endpoint)
                else:
                    _LOGGER.debug("No auth configured for: %s", endpoint)
            except FileFlowsAuthError:
                _LOGGER.warning("Auth failed, trying without auth for: %s", endpoint)

        # Add Content-Type for requests with body
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
                _LOGGER.debug(
                    "%s %s -> %s %s",
                    method,
                    endpoint,
                    response.status,
                    response.reason,
                )

                # Handle auth errors
                if response.status == 401:
                    # Token might be expired, clear it and retry once
                    if self._bearer_token and require_auth:
                        _LOGGER.warning("Token expired, clearing and will retry")
                        self._bearer_token = None
                        self._token_expiry = None
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
    # Connection Test
    # =========================================================================
    async def test_connection(self) -> bool:
        """Test connection to FileFlows.

        Tries authenticated endpoint first, falls back to public endpoint.
        """
        try:
            # Try /api/status first (authenticated)
            data = await self._fetch("api/status", require_auth=True)
            if data and isinstance(data, dict):
                if "queue" in data or "processing" in data:
                    _LOGGER.info("Connection test successful (authenticated)")
                    return True
        except Exception as err:
            _LOGGER.debug("Authenticated test failed, trying public: %s", err)

        try:
            # Fall back to public endpoint
            data = await self._fetch("remote/info/status", require_auth=False)
            if data and isinstance(data, dict):
                if "queue" in data or "processing" in data:
                    _LOGGER.info("Connection test successful (public)")
                    return True
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)

        return False

    # =========================================================================
    # Public Endpoints (/remote/info/*) - Fallback when no auth
    # =========================================================================
    async def get_remote_status(self) -> dict[str, Any]:
        """Get status from public endpoint (fallback)."""
        result = await self._fetch("remote/info/status", require_auth=False)
        return result if isinstance(result, dict) else {}

    async def get_remote_shrinkage(self) -> list[dict[str, Any]]:
        """Get shrinkage from public endpoint (fallback)."""
        result = await self._fetch("remote/info/shrinkage-groups", require_auth=False)
        return result if isinstance(result, list) else []

    async def get_remote_update_available(self) -> bool:
        """Check update from public endpoint (fallback)."""
        try:
            result = await self._fetch("remote/info/update-available", require_auth=False)
            if isinstance(result, dict):
                return result.get("UpdateAvailable", False) is True
            return False
        except FileFlowsApiError:
            return False

    # =========================================================================
    # Authenticated Endpoints (/api/*) - Primary source when auth available
    # =========================================================================

    async def get_status(self) -> dict[str, Any]:
        """Get comprehensive status from /api/status (authenticated).

        Returns queue, processing, processed, time, processingFiles, and more.
        """
        try:
            result = await self._fetch("api/status")
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError:
            return {}

    async def get_system_info(self) -> dict[str, Any]:
        """Get system info (CPU, Memory, etc.) from /api/system/info."""
        try:
            result = await self._fetch("api/system")
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError:
            return {}

    async def get_version(self) -> str:
        """Get FileFlows version."""
        try:
            result = await self._fetch("api/system/version")
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("Version", "Unknown")
            return "Unknown"
        except FileFlowsApiError:
            return "Unknown"

    # Nodes
    async def get_nodes(self) -> list[dict[str, Any]]:
        """Get all processing nodes."""
        try:
            result = await self._fetch("api/node")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # Libraries
    async def get_libraries(self) -> list[dict[str, Any]]:
        """Get all libraries."""
        try:
            result = await self._fetch("api/library")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # Flows
    async def get_flows(self) -> list[dict[str, Any]]:
        """Get all flows."""
        try:
            result = await self._fetch("api/flow")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # Plugins
    async def get_plugins(self) -> list[dict[str, Any]]:
        """Get all plugins."""
        try:
            result = await self._fetch("api/plugin")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # Tasks
    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get all scheduled tasks."""
        try:
            result = await self._fetch("api/task")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # Library Files
    async def get_library_file_status(self) -> list[dict[str, Any]]:
        """Get library file status."""
        try:
            result = await self._fetch("api/library-file/status")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # NVIDIA
    async def get_nvidia_smi(self) -> list[dict[str, Any]]:
        """Get NVIDIA GPU info."""
        try:
            result = await self._fetch("api/nvidia/smi")
            return result if isinstance(result, list) else []
        except FileFlowsApiError:
            return []

    # =========================================================================
    # Control Endpoints
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
    # Combined Data Fetch - Smart fallback
    # =========================================================================
    async def get_all_data(self) -> dict[str, Any]:
        """Get all data with smart fallback between authenticated and public APIs.

        If username/password configured: Use /api/* endpoints (full data)
        Otherwise: Use /remote/info/* endpoints (basic monitoring)
        """
        has_auth = bool(self._username and self._password)

        if has_auth:
            _LOGGER.debug("Fetching data using authenticated endpoints")
            return await self._get_authenticated_data()
        else:
            _LOGGER.debug("Fetching data using public endpoints")
            return await self._get_public_data()

    async def _get_authenticated_data(self) -> dict[str, Any]:
        """Fetch all data from authenticated /api/* endpoints."""
        data: dict[str, Any] = {
            "status": {},
            "system_info": {},
            "nodes": [],
            "libraries": [],
            "flows": [],
            "plugins": [],
            "tasks": [],
            "library_file_status": [],
            "nvidia": [],
            "version": "Unknown",
        }

        try:
            results = await asyncio.gather(
                self.get_status(),
                self.get_system_info(),
                self.get_nodes(),
                self.get_libraries(),
                self.get_flows(),
                self.get_plugins(),
                self.get_tasks(),
                self.get_library_file_status(),
                self.get_nvidia_smi(),
                self.get_version(),
                return_exceptions=True,
            )

            # Process results
            if not isinstance(results[0], Exception):
                data["status"] = results[0]
            if not isinstance(results[1], Exception):
                data["system_info"] = results[1]
            if not isinstance(results[2], Exception):
                data["nodes"] = results[2]
            if not isinstance(results[3], Exception):
                data["libraries"] = results[3]
            if not isinstance(results[4], Exception):
                data["flows"] = results[4]
            if not isinstance(results[5], Exception):
                data["plugins"] = results[5]
            if not isinstance(results[6], Exception):
                data["tasks"] = results[6]
            if not isinstance(results[7], Exception):
                data["library_file_status"] = results[7]
            if not isinstance(results[8], Exception):
                data["nvidia"] = results[8]
            if not isinstance(results[9], Exception):
                data["version"] = results[9]

        except Exception as err:
            _LOGGER.error("Error fetching authenticated data: %s", err)

        return data

    async def _get_public_data(self) -> dict[str, Any]:
        """Fetch data from public /remote/info/* endpoints (fallback)."""
        data: dict[str, Any] = {
            "remote_status": {},
            "shrinkage_groups": [],
            "update_available": False,
            "version": "Unknown",
        }

        try:
            results = await asyncio.gather(
                self.get_remote_status(),
                self.get_remote_shrinkage(),
                self.get_remote_update_available(),
                self.get_version(),
                return_exceptions=True,
            )

            if not isinstance(results[0], Exception):
                data["remote_status"] = results[0]
            if not isinstance(results[1], Exception):
                data["shrinkage_groups"] = results[1]
            if not isinstance(results[2], Exception):
                data["update_available"] = results[2]
            if not isinstance(results[3], Exception):
                data["version"] = results[3]

        except Exception as err:
            _LOGGER.error("Error fetching public data: %s", err)

        return data
