"""FileFlows API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from .const import (
    API_DASHBOARD,
    API_DASHBOARD_LIST,
    API_FLOWS,
    API_FLOW_BY_UID,
    API_FLOW_STATE,
    API_LIBRARIES,
    API_LIBRARY_BY_UID,
    API_LIBRARY_FILE_REPROCESS,
    API_LIBRARY_FILE_RECENTLY_FINISHED,
    API_LIBRARY_FILE_SHRINKAGE_GROUPS,
    API_LIBRARY_FILE_STATUS,
    API_LIBRARY_FILE_UNHOLD,
    API_LIBRARY_FILE_UPCOMING,
    API_LIBRARY_RESCAN,
    API_LIBRARY_RESCAN_ENABLED,
    API_LIBRARY_STATE,
    API_LOG,
    API_NODE_BY_UID,
    API_NODE_STATE,
    API_NODES,
    API_NVIDIA_SMI,
    API_PLUGINS,
    API_SCRIPTS,
    API_SETTINGS,
    API_SETTINGS_FILEFLOWS_STATUS,
    API_STATUS,
    API_STATUS_UPDATE_AVAILABLE,
    API_SYSTEM_HISTORY_CPU,
    API_SYSTEM_HISTORY_MEMORY,
    API_SYSTEM_INFO,
    API_SYSTEM_PAUSE,
    API_SYSTEM_RESTART,
    API_SYSTEM_VERSION,
    API_TASKS,
    API_TASK_RUN,
    API_VARIABLES,
    API_WEBHOOKS,
    API_WORKER_ABORT,
    API_WORKER_ABORT_BY_FILE,
    API_WORKERS,
    AUTH_HEADER,
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
            headers[AUTH_HEADER] = self._access_token
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | list | None = None,
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
                
                # Try to parse as JSON anyway
                text = await response.text()
                if text:
                    try:
                        import json
                        return json.loads(text)
                    except:
                        return text
                return None

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
        self, endpoint: str, data: dict[str, Any] | list | None = None
    ) -> Any:
        """Make a POST request."""
        return await self._request("POST", endpoint, data=data)

    async def _put(
        self, endpoint: str, data: dict[str, Any] | list | None = None
    ) -> Any:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, data=data)

    async def _delete(self, endpoint: str, data: dict[str, Any] | list | None = None) -> Any:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, data=data)

    # =========================================================================
    # Connection Test
    # =========================================================================
    async def test_connection(self) -> bool:
        """Test connection to FileFlows."""
        try:
            result = await self.get_status()
            return result is not None
        except FileFlowsApiError:
            return False

    # =========================================================================
    # Status Endpoints
    # =========================================================================
    async def get_status(self) -> dict[str, Any]:
        """Get the current status."""
        return await self._get(API_STATUS)

    async def get_update_available(self) -> dict[str, Any]:
        """Gets if an update is available."""
        try:
            return await self._get(API_STATUS_UPDATE_AVAILABLE)
        except FileFlowsApiError:
            return {"UpdateAvailable": False}

    # =========================================================================
    # System Endpoints
    # =========================================================================
    async def get_version(self) -> str:
        """Gets the version of FileFlows."""
        result = await self._get(API_SYSTEM_VERSION)
        if isinstance(result, str):
            return result
        return result.get("Version", "Unknown") if result else "Unknown"

    async def get_system_info(self) -> dict[str, Any]:
        """Gets system information (memory, CPU)."""
        return await self._get(API_SYSTEM_INFO)

    async def pause_system(self, minutes: int = 0) -> bool:
        """Pause the system. minutes=0 means indefinitely."""
        await self._post(API_SYSTEM_PAUSE, {"Minutes": minutes} if minutes > 0 else None)
        return True

    async def resume_system(self) -> bool:
        """Resume the system (unpause)."""
        # Pause with -1 or specific endpoint - FileFlows uses pause toggle
        await self._post(API_SYSTEM_PAUSE, {"Minutes": -1})
        return True

    async def restart_system(self) -> bool:
        """Restart FileFlows server."""
        await self._post(API_SYSTEM_RESTART)
        return True

    async def get_cpu_history(self) -> list[dict[str, Any]]:
        """Gets history CPU data."""
        result = await self._get(API_SYSTEM_HISTORY_CPU)
        return result if isinstance(result, list) else []

    async def get_memory_history(self) -> list[dict[str, Any]]:
        """Gets history memory data."""
        result = await self._get(API_SYSTEM_HISTORY_MEMORY)
        return result if isinstance(result, list) else []

    # =========================================================================
    # Settings Endpoints
    # =========================================================================
    async def get_settings(self) -> dict[str, Any]:
        """Get the system settings."""
        return await self._get(API_SETTINGS)

    async def get_fileflows_status(self) -> dict[str, Any]:
        """Gets the system status of FileFlows."""
        return await self._get(API_SETTINGS_FILEFLOWS_STATUS)

    # =========================================================================
    # Dashboard Endpoints
    # =========================================================================
    async def get_dashboards(self) -> list[dict[str, Any]]:
        """Get all dashboards in the system."""
        result = await self._get(API_DASHBOARD)
        return result if isinstance(result, list) else []

    async def get_dashboard_list(self) -> list[dict[str, Any]]:
        """Get a list of all dashboards."""
        result = await self._get(API_DASHBOARD_LIST)
        return result if isinstance(result, list) else []

    # =========================================================================
    # Node Endpoints
    # =========================================================================
    async def get_nodes(self) -> list[dict[str, Any]]:
        """Gets all processing nodes."""
        result = await self._get(API_NODES)
        return result if isinstance(result, list) else []

    async def get_node(self, uid: str) -> dict[str, Any]:
        """Get a specific processing node."""
        return await self._get(API_NODE_BY_UID.format(uid=uid))

    async def set_node_state(self, uid: str, enabled: bool) -> bool:
        """Set state of a processing node."""
        await self._put(f"{API_NODE_STATE.format(uid=uid)}?enable={str(enabled).lower()}")
        return True

    async def enable_node(self, uid: str) -> bool:
        """Enable a processing node."""
        return await self.set_node_state(uid, True)

    async def disable_node(self, uid: str) -> bool:
        """Disable a processing node."""
        return await self.set_node_state(uid, False)

    # =========================================================================
    # Library Endpoints
    # =========================================================================
    async def get_libraries(self) -> list[dict[str, Any]]:
        """Gets all libraries."""
        result = await self._get(API_LIBRARIES)
        return result if isinstance(result, list) else []

    async def get_library(self, uid: str) -> dict[str, Any]:
        """Get a specific library."""
        return await self._get(API_LIBRARY_BY_UID.format(uid=uid))

    async def set_library_state(self, uid: str, enabled: bool) -> bool:
        """Set the enable state for a library."""
        await self._put(f"{API_LIBRARY_STATE.format(uid=uid)}?enable={str(enabled).lower()}")
        return True

    async def enable_library(self, uid: str) -> bool:
        """Enable a library."""
        return await self.set_library_state(uid, True)

    async def disable_library(self, uid: str) -> bool:
        """Disable a library."""
        return await self.set_library_state(uid, False)

    async def rescan_libraries(self, uids: list[str] | None = None) -> bool:
        """Rescan libraries."""
        if uids:
            await self._put(API_LIBRARY_RESCAN, uids)
        else:
            await self._post(API_LIBRARY_RESCAN_ENABLED)
        return True

    async def rescan_all_libraries(self) -> bool:
        """Rescan all enabled libraries."""
        await self._post(API_LIBRARY_RESCAN_ENABLED)
        return True

    # =========================================================================
    # Library File Endpoints
    # =========================================================================
    async def get_library_file_status(self) -> dict[str, Any]:
        """Gets the library status overview."""
        return await self._get(API_LIBRARY_FILE_STATUS)

    async def get_upcoming_files(self) -> list[dict[str, Any]]:
        """Get next 10 upcoming files to process."""
        result = await self._get(API_LIBRARY_FILE_UPCOMING)
        return result if isinstance(result, list) else []

    async def get_recently_finished(self) -> list[dict[str, Any]]:
        """Gets the last 10 successfully processed files."""
        result = await self._get(API_LIBRARY_FILE_RECENTLY_FINISHED)
        return result if isinstance(result, list) else []

    async def get_shrinkage_groups(self) -> list[dict[str, Any]]:
        """Get library file shrinkage grouped by library."""
        result = await self._get(API_LIBRARY_FILE_SHRINKAGE_GROUPS)
        return result if isinstance(result, list) else []

    async def reprocess_files(self, uids: list[str]) -> bool:
        """Reprocess library files."""
        await self._post(API_LIBRARY_FILE_REPROCESS, uids)
        return True

    async def reprocess_file(self, uid: str) -> bool:
        """Reprocess a single library file."""
        return await self.reprocess_files([uid])

    async def unhold_files(self, uids: list[str]) -> bool:
        """Unhold library files."""
        await self._post(API_LIBRARY_FILE_UNHOLD, uids)
        return True

    # =========================================================================
    # Flow Endpoints
    # =========================================================================
    async def get_flows(self) -> list[dict[str, Any]]:
        """Get all flows."""
        result = await self._get(API_FLOWS)
        return result if isinstance(result, list) else []

    async def get_flow(self, uid: str) -> dict[str, Any]:
        """Get a specific flow."""
        return await self._get(API_FLOW_BY_UID.format(uid=uid))

    async def set_flow_state(self, uid: str, enabled: bool) -> bool:
        """Sets the enabled state of a flow."""
        await self._put(f"{API_FLOW_STATE.format(uid=uid)}?enable={str(enabled).lower()}")
        return True

    async def enable_flow(self, uid: str) -> bool:
        """Enable a flow."""
        return await self.set_flow_state(uid, True)

    async def disable_flow(self, uid: str) -> bool:
        """Disable a flow."""
        return await self.set_flow_state(uid, False)

    # =========================================================================
    # Worker Endpoints
    # =========================================================================
    async def get_workers(self) -> list[dict[str, Any]]:
        """Get all running flow executors."""
        result = await self._get(API_WORKERS)
        return result if isinstance(result, list) else []

    async def abort_worker(self, uid: str) -> bool:
        """Abort work."""
        await self._delete(API_WORKER_ABORT.format(uid=uid))
        return True

    async def abort_worker_by_file(self, file_uid: str) -> bool:
        """Abort work by library file."""
        await self._delete(API_WORKER_ABORT_BY_FILE.format(uid=file_uid))
        return True

    # =========================================================================
    # Task Endpoints
    # =========================================================================
    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get all scheduled tasks."""
        result = await self._get(API_TASKS)
        return result if isinstance(result, list) else []

    async def run_task(self, uid: str) -> bool:
        """Runs a scheduled task now."""
        await self._post(API_TASK_RUN.format(uid=uid))
        return True

    # =========================================================================
    # Plugin Endpoints
    # =========================================================================
    async def get_plugins(self) -> list[dict[str, Any]]:
        """Get list of all plugins."""
        result = await self._get(API_PLUGINS)
        return result if isinstance(result, list) else []

    # =========================================================================
    # Variable Endpoints
    # =========================================================================
    async def get_variables(self) -> list[dict[str, Any]]:
        """Get all variables."""
        result = await self._get(API_VARIABLES)
        return result if isinstance(result, list) else []

    # =========================================================================
    # Script Endpoints
    # =========================================================================
    async def get_scripts(self) -> list[dict[str, Any]]:
        """Get all scripts."""
        result = await self._get(API_SCRIPTS)
        return result if isinstance(result, list) else []

    # =========================================================================
    # Webhook Endpoints
    # =========================================================================
    async def get_webhooks(self) -> list[dict[str, Any]]:
        """Get all webhooks."""
        result = await self._get(API_WEBHOOKS)
        return result if isinstance(result, list) else []

    # =========================================================================
    # NVIDIA Endpoints
    # =========================================================================
    async def get_nvidia_smi(self) -> dict[str, Any]:
        """Gets the NVIDIA SMI data."""
        try:
            return await self._get(API_NVIDIA_SMI)
        except FileFlowsApiError:
            return {}

    # =========================================================================
    # Log Endpoints
    # =========================================================================
    async def get_log(self) -> str:
        """Gets the system log."""
        result = await self._get(API_LOG)
        return result if isinstance(result, str) else ""

    # =========================================================================
    # Combined Data Fetch for Coordinator
    # =========================================================================
    async def get_all_data(self) -> dict[str, Any]:
        """Get all data needed for sensors."""
        data: dict[str, Any] = {
            "status": {},
            "system_info": {},
            "fileflows_status": {},
            "version": "Unknown",
            "update_available": False,
            "nodes": [],
            "libraries": [],
            "flows": [],
            "workers": [],
            "tasks": [],
            "plugins": [],
            "upcoming_files": [],
            "recently_finished": [],
            "shrinkage_groups": [],
            "library_file_status": {},
            "nvidia": {},
        }

        # Primary status endpoint
        try:
            data["status"] = await self.get_status()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get status: %s", err)

        # System info (CPU, Memory)
        try:
            data["system_info"] = await self.get_system_info()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get system info: %s", err)

        # FileFlows status
        try:
            data["fileflows_status"] = await self.get_fileflows_status()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get fileflows status: %s", err)

        # Version
        try:
            data["version"] = await self.get_version()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get version: %s", err)

        # Update available
        try:
            update_info = await self.get_update_available()
            data["update_available"] = update_info.get("UpdateAvailable", False) if update_info else False
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get update info: %s", err)

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

        # Shrinkage groups
        try:
            data["shrinkage_groups"] = await self.get_shrinkage_groups()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get shrinkage groups: %s", err)

        # NVIDIA SMI (optional)
        try:
            data["nvidia"] = await self.get_nvidia_smi()
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get nvidia info: %s", err)

        return data
