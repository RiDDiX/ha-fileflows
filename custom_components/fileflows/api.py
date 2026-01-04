"""FileFlows API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from .const import (
    API_DASHBOARD_SUMMARY,
    API_FLOWS,
    API_LIBRARIES,
    API_LIBRARY_BY_UID,
    API_LIBRARY_FILES,
    API_LIBRARY_FILES_FAILED,
    API_LIBRARY_FILES_PROCESSED,
    API_LIBRARY_FILES_PROCESSING,
    API_LIBRARY_FILES_UNPROCESSED,
    API_LIBRARY_FILE_REPROCESS,
    API_LIBRARY_RESCAN,
    API_LOG,
    API_NODE_BY_UID,
    API_NODE_DISABLE,
    API_NODE_ENABLE,
    API_NODES,
    API_SETTINGS,
    API_SHRINKAGE,
    API_STATISTICS,
    API_STATISTICS_RUNNING,
    API_STATUS,
    API_SYSTEM_INFO,
    API_SYSTEM_PAUSE,
    API_SYSTEM_RESUME,
    API_UPDATE_AVAILABLE,
    API_VERSION,
    API_WORKERS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = ClientTimeout(total=30)


class FileFlowsApiError(Exception):
    """Exception for FileFlows API errors."""


class FileFlowsConnectionError(FileFlowsApiError):
    """Exception for connection errors."""


class FileFlowsAuthError(FileFlowsApiError):
    """Exception for authentication errors."""


class FileFlowsApi:
    """FileFlows API Client."""

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
        self._access_token = access_token
        self._session = session
        self._close_session = False

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

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._access_token:
            headers["x-token"] = self._access_token
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a request to the API."""
        session = await self._get_session()
        url = f"{self._base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with session.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            ) as response:
                if response.status == 401:
                    raise FileFlowsAuthError("Authentication failed")
                if response.status == 403:
                    raise FileFlowsAuthError("Access forbidden")
                
                response.raise_for_status()
                
                # Handle empty responses
                if response.status == 204:
                    return None
                
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                return await response.text()

        except ClientResponseError as err:
            _LOGGER.error("API response error: %s", err)
            raise FileFlowsApiError(f"API error: {err.status}") from err
        except ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            raise FileFlowsConnectionError(f"Connection failed: {err}") from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Request timeout")
            raise FileFlowsConnectionError("Request timeout") from err

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params)

    async def _post(
        self, endpoint: str, data: dict[str, Any] | None = None
    ) -> Any:
        """Make a POST request."""
        return await self._request("POST", endpoint, data=data)

    async def _put(
        self, endpoint: str, data: dict[str, Any] | None = None
    ) -> Any:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, data=data)

    async def _delete(self, endpoint: str) -> Any:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint)

    # System endpoints
    async def test_connection(self) -> bool:
        """Test connection to FileFlows."""
        try:
            # Use status endpoint as it's the most reliable (used by Fenrus)
            result = await self.get_status()
            # Check if we got valid data
            return result is not None and "queue" in result or "processed" in result
        except FileFlowsApiError:
            return False

    async def get_system_info(self) -> dict[str, Any]:
        """Get system information."""
        try:
            return await self._get(API_SYSTEM_INFO)
        except FileFlowsApiError:
            # Fallback to status if system/info doesn't exist
            return await self.get_status()

    async def get_version(self) -> dict[str, Any]:
        """Get FileFlows version."""
        return await self._get(API_VERSION)

    async def get_status(self) -> dict[str, Any]:
        """Get system status."""
        return await self._get(API_STATUS)

    async def pause_system(self) -> bool:
        """Pause the system."""
        await self._post(API_SYSTEM_PAUSE)
        return True

    async def resume_system(self) -> bool:
        """Resume the system."""
        await self._post(API_SYSTEM_RESUME)
        return True

    async def get_settings(self) -> dict[str, Any]:
        """Get system settings."""
        return await self._get(API_SETTINGS)

    # Node endpoints
    async def get_nodes(self) -> list[dict[str, Any]]:
        """Get all processing nodes."""
        result = await self._get(API_NODES)
        return result if isinstance(result, list) else []

    async def get_node(self, uid: str) -> dict[str, Any]:
        """Get a specific node."""
        return await self._get(API_NODE_BY_UID.format(uid=uid))

    async def enable_node(self, uid: str) -> bool:
        """Enable a node."""
        await self._post(API_NODE_ENABLE.format(uid=uid))
        return True

    async def disable_node(self, uid: str) -> bool:
        """Disable a node."""
        await self._post(API_NODE_DISABLE.format(uid=uid))
        return True

    # Library endpoints
    async def get_libraries(self) -> list[dict[str, Any]]:
        """Get all libraries."""
        result = await self._get(API_LIBRARIES)
        return result if isinstance(result, list) else []

    async def get_library(self, uid: str) -> dict[str, Any]:
        """Get a specific library."""
        return await self._get(API_LIBRARY_BY_UID.format(uid=uid))

    async def rescan_library(self, uid: str) -> bool:
        """Rescan a library."""
        await self._post(API_LIBRARY_RESCAN.format(uid=uid))
        return True

    # Library files endpoints
    async def get_library_files(self) -> list[dict[str, Any]]:
        """Get all library files."""
        result = await self._get(API_LIBRARY_FILES)
        return result if isinstance(result, list) else []

    async def get_unprocessed_files(self) -> list[dict[str, Any]]:
        """Get unprocessed files."""
        result = await self._get(API_LIBRARY_FILES_UNPROCESSED)
        return result if isinstance(result, list) else []

    async def get_processing_files(self) -> list[dict[str, Any]]:
        """Get currently processing files."""
        result = await self._get(API_LIBRARY_FILES_PROCESSING)
        return result if isinstance(result, list) else []

    async def get_processed_files(self) -> list[dict[str, Any]]:
        """Get processed files."""
        result = await self._get(API_LIBRARY_FILES_PROCESSED)
        return result if isinstance(result, list) else []

    async def get_failed_files(self) -> list[dict[str, Any]]:
        """Get failed files."""
        result = await self._get(API_LIBRARY_FILES_FAILED)
        return result if isinstance(result, list) else []

    async def reprocess_file(self, uid: str) -> bool:
        """Reprocess a file."""
        await self._post(API_LIBRARY_FILE_REPROCESS.format(uid=uid))
        return True

    # Flow endpoints
    async def get_flows(self) -> list[dict[str, Any]]:
        """Get all flows."""
        result = await self._get(API_FLOWS)
        return result if isinstance(result, list) else []

    # Statistics endpoints
    async def get_statistics(self) -> dict[str, Any]:
        """Get statistics."""
        return await self._get(API_STATISTICS)

    async def get_running_statistics(self) -> dict[str, Any]:
        """Get running/processing statistics."""
        return await self._get(API_STATISTICS_RUNNING)

    async def get_shrinkage(self) -> list[dict[str, Any]]:
        """Get shrinkage/storage saved statistics."""
        result = await self._get(API_SHRINKAGE)
        return result if isinstance(result, list) else []

    async def get_update_available(self) -> dict[str, Any]:
        """Check if update is available."""
        try:
            return await self._get(API_UPDATE_AVAILABLE)
        except FileFlowsApiError:
            return {"UpdateAvailable": False}

    async def get_dashboard_summary(self) -> dict[str, Any]:
        """Get dashboard summary data."""
        return await self._get(API_DASHBOARD_SUMMARY)

    # Worker endpoints
    async def get_workers(self) -> list[dict[str, Any]]:
        """Get all workers."""
        result = await self._get(API_WORKERS)
        return result if isinstance(result, list) else []

    # Log endpoints
    async def get_logs(self, lines: int = 100) -> str:
        """Get recent logs."""
        return await self._get(API_LOG, params={"lines": lines})

    # Combined data for coordinator
    async def get_all_data(self) -> dict[str, Any]:
        """Get all data needed for sensors."""
        data: dict[str, Any] = {
            "status": {},
            "system_info": {},
            "nodes": [],
            "libraries": [],
            "unprocessed_files": [],
            "processing_files": [],
            "processed_count": 0,
            "failed_count": 0,
            "statistics": {},
            "shrinkage": [],
            "workers": [],
            "flows": [],
            "update_available": False,
        }

        try:
            # Get status (primary data source - used by Fenrus)
            # Returns: queue, processing, processed, time, processingFiles
            try:
                status = await self.get_status()
                data["status"] = status
                data["processing_files"] = status.get("processingFiles", [])
                data["processed_count"] = status.get("processed", 0)
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get status: %s", err)

            # Get shrinkage (storage savings)
            try:
                data["shrinkage"] = await self.get_shrinkage()
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get shrinkage: %s", err)

            # Get update available
            try:
                update_info = await self.get_update_available()
                data["update_available"] = update_info.get("UpdateAvailable", False)
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get update info: %s", err)

            # Get nodes (may require auth)
            try:
                data["nodes"] = await self.get_nodes()
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get nodes: %s", err)

            # Get libraries (may require auth)
            try:
                data["libraries"] = await self.get_libraries()
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get libraries: %s", err)

            # Get flows (may require auth)
            try:
                data["flows"] = await self.get_flows()
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get flows: %s", err)

            # Optional: Get detailed file lists if available
            try:
                data["unprocessed_files"] = await self.get_unprocessed_files()
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get unprocessed files: %s", err)

            try:
                failed = await self.get_failed_files()
                data["failed_count"] = len(failed) if failed else 0
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get failed files: %s", err)

            # Get workers (may require auth)
            try:
                data["workers"] = await self.get_workers()
            except FileFlowsApiError as err:
                _LOGGER.debug("Could not get workers: %s", err)

        except Exception as err:
            _LOGGER.error("Error fetching FileFlows data: %s", err)
            raise FileFlowsApiError(f"Failed to fetch data: {err}") from err

        return data
