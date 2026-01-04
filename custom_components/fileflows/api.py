"""FileFlows API Client - Built to match Fenrus implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = ClientTimeout(total=30)


class FileFlowsApiError(Exception):
    """Exception for FileFlows API errors."""


class FileFlowsConnectionError(FileFlowsApiError):
    """Exception for connection errors."""


class FileFlowsAuthError(FileFlowsApiError):
    """Exception for authentication errors."""


class FileFlowsApi:
    """FileFlows API Client - Matching Fenrus implementation."""

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
        
        _LOGGER.debug("FileFlows API initialized: %s", self._base_url)

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
    # AUTHENTICATED Endpoints (/api/*) - Require x-token if auth enabled
    # =========================================================================

    async def get_system_info(self) -> dict[str, Any]:
        """Get system information (memory, CPU)."""
        try:
            result = await self._fetch("api/system/info")
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get system info: %s", err)
            return {}

    async def get_fileflows_status(self) -> dict[str, Any]:
        """Get FileFlows status."""
        try:
            result = await self._fetch("api/settings/fileflows-status")
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get fileflows status: %s", err)
            return {}

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

    # Node Endpoints
    async def get_nodes(self) -> list[dict[str, Any]]:
        """Get all processing nodes."""
        try:
            result = await self._fetch("api/node")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get nodes: %s", err)
            return []

    async def set_node_state(self, uid: str, enabled: bool) -> bool:
        """Set state of a processing node."""
        try:
            state = "true" if enabled else "false"
            await self._fetch(f"api/node/state/{uid}?enable={state}", method="PUT")
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
        """Get all libraries."""
        try:
            result = await self._fetch("api/library")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get libraries: %s", err)
            return []

    async def set_library_state(self, uid: str, enabled: bool) -> bool:
        """Set library state."""
        try:
            state = "true" if enabled else "false"
            await self._fetch(f"api/library/state/{uid}?enable={state}", method="PUT")
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

    # Library File Endpoints
    async def get_library_file_status(self) -> dict[str, Any]:
        """Get library file status overview."""
        try:
            result = await self._fetch("api/library-file/status")
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get library file status: %s", err)
            return {}

    async def get_upcoming_files(self) -> list[dict[str, Any]]:
        """Get next 10 upcoming files."""
        try:
            result = await self._fetch("api/library-file/upcoming")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get upcoming files: %s", err)
            return []

    async def get_recently_finished(self) -> list[dict[str, Any]]:
        """Get last 10 finished files."""
        try:
            result = await self._fetch("api/library-file/recently-finished")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get recently finished: %s", err)
            return []

    async def reprocess_files(self, uids: list[str]) -> bool:
        """Reprocess library files."""
        try:
            await self._fetch("api/library-file/reprocess", method="POST", json_data=uids)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to reprocess: %s", err)
            return False

    async def reprocess_file(self, uid: str) -> bool:
        """Reprocess a single file."""
        return await self.reprocess_files([uid])

    async def unhold_files(self, uids: list[str]) -> bool:
        """Unhold library files."""
        try:
            await self._fetch("api/library-file/unhold", method="POST", json_data=uids)
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to unhold: %s", err)
            return False

    # Flow Endpoints
    async def get_flows(self) -> list[dict[str, Any]]:
        """Get all flows."""
        try:
            result = await self._fetch("api/flow")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get flows: %s", err)
            return []

    async def set_flow_state(self, uid: str, enabled: bool) -> bool:
        """Set flow state."""
        try:
            state = "true" if enabled else "false"
            await self._fetch(f"api/flow/state/{uid}?enable={state}", method="PUT")
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
        """Get all running workers."""
        try:
            result = await self._fetch("api/worker")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get workers: %s", err)
            return []

    async def abort_worker(self, uid: str) -> bool:
        """Abort a worker."""
        try:
            await self._fetch(f"api/worker/{uid}", method="DELETE")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to abort worker: %s", err)
            return False

    async def abort_worker_by_file(self, file_uid: str) -> bool:
        """Abort worker by file UID."""
        try:
            await self._fetch(f"api/worker/by-file/{file_uid}", method="DELETE")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to abort worker by file: %s", err)
            return False

    # Task Endpoints
    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get all scheduled tasks."""
        try:
            result = await self._fetch("api/task")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get tasks: %s", err)
            return []

    async def run_task(self, uid: str) -> bool:
        """Run a task."""
        try:
            await self._fetch(f"api/task/run/{uid}", method="POST")
            return True
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to run task: %s", err)
            return False

    # Plugin Endpoints
    async def get_plugins(self) -> list[dict[str, Any]]:
        """Get all plugins."""
        try:
            result = await self._fetch("api/plugin")
            return result if isinstance(result, list) else []
        except FileFlowsApiError as err:
            _LOGGER.debug("Could not get plugins: %s", err)
            return []

    # NVIDIA Endpoints
    async def get_nvidia_smi(self) -> dict[str, Any]:
        """Get NVIDIA SMI data."""
        try:
            result = await self._fetch("api/nvidia/smi")
            return result if isinstance(result, dict) else {}
        except FileFlowsApiError:
            return {}

    # =========================================================================
    # Combined Data Fetch for Coordinator
    # =========================================================================
    async def get_all_data(self) -> dict[str, Any]:
        """Get all data needed for sensors."""
        data: dict[str, Any] = {
            "remote_status": {},
            "shrinkage_groups": [],
            "update_available": False,
            "version": "Unknown",
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
        }

        # PUBLIC endpoints (always work)
        try:
            data["remote_status"] = await self.get_remote_status()
        except Exception as err:
            _LOGGER.warning("Could not get remote status: %s", err)

        try:
            data["shrinkage_groups"] = await self.get_remote_shrinkage()
        except Exception as err:
            _LOGGER.debug("Could not get shrinkage: %s", err)

        try:
            data["update_available"] = await self.get_remote_update_available()
        except Exception as err:
            _LOGGER.debug("Could not get update info: %s", err)

        try:
            data["version"] = await self.get_version()
        except Exception as err:
            _LOGGER.debug("Could not get version: %s", err)

        # AUTHENTICATED endpoints
        try:
            data["system_info"] = await self.get_system_info()
        except Exception as err:
            _LOGGER.debug("Could not get system info: %s", err)

        try:
            data["fileflows_status"] = await self.get_fileflows_status()
        except Exception as err:
            _LOGGER.debug("Could not get fileflows status: %s", err)

        try:
            data["nodes"] = await self.get_nodes()
        except Exception as err:
            _LOGGER.debug("Could not get nodes: %s", err)

        try:
            data["libraries"] = await self.get_libraries()
        except Exception as err:
            _LOGGER.debug("Could not get libraries: %s", err)

        try:
            data["flows"] = await self.get_flows()
        except Exception as err:
            _LOGGER.debug("Could not get flows: %s", err)

        try:
            data["workers"] = await self.get_workers()
        except Exception as err:
            _LOGGER.debug("Could not get workers: %s", err)

        try:
            data["tasks"] = await self.get_tasks()
        except Exception as err:
            _LOGGER.debug("Could not get tasks: %s", err)

        try:
            data["plugins"] = await self.get_plugins()
        except Exception as err:
            _LOGGER.debug("Could not get plugins: %s", err)

        try:
            data["library_file_status"] = await self.get_library_file_status()
        except Exception as err:
            _LOGGER.debug("Could not get library file status: %s", err)

        try:
            data["upcoming_files"] = await self.get_upcoming_files()
        except Exception as err:
            _LOGGER.debug("Could not get upcoming files: %s", err)

        try:
            data["recently_finished"] = await self.get_recently_finished()
        except Exception as err:
            _LOGGER.debug("Could not get recently finished: %s", err)

        try:
            data["nvidia"] = await self.get_nvidia_smi()
        except Exception as err:
            _LOGGER.debug("Could not get nvidia info: %s", err)

        return data
