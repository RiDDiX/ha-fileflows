"""FileFlows API client using HMAC request signing."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import quote, unquote
from uuid import uuid4

import aiohttp
from yarl import URL

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)

FENRUS = "/webhook/fenrus"
STATUS = "/api/status"
SYSTEM_VERSION = "/api/system/version"
SYSTEM_PAUSE = "/api/system/pause"
SYSTEM_RESTART = "/api/system/restart"
SETTINGS = "/api/settings"
AGENTS = "/api/agent"
LIBRARIES = "/api/library"
LIBRARY_RESCAN = "/api/library/rescan"
LIBRARY_RESCAN_ENABLED = "/api/library/rescan-enabled"
FILE_STATUS = "/api/library-file/status"
FILE_LIST_ALL = "/api/library-file/list-all"
FILE_ABORT = "/api/library-file/abort"
FILE_REPROCESS = "/api/library-file/reprocess"
FILE_UNHOLD = "/api/library-file/unhold"
FILE_FORCE_PROCESSING = "/api/library-file/force-processing"
FLOWS = "/api/flow"
TASKS = "/api/task"
PLUGINS = "/api/plugin"
NVIDIA_SMI = "/api/nvidia/smi"
STORAGE_SAVED = "/api/statistics/storage-saved"

FILE_STATUS_NAMES = {
    -3: "OnHold",
    -2: "Disabled",
    -1: "OutOfSchedule",
    0: "Unprocessed",
    1: "Processed",
    2: "Processing",
    4: "Failed",
}

# Endpoints fetched as-is for the coordinator; failures only blank their key
OPTIONAL_ENDPOINTS: tuple[tuple[str, str, type], ...] = (
    ("settings", SETTINGS, dict),
    ("nodes", AGENTS, list),
    ("libraries", LIBRARIES, list),
    ("flows", FLOWS, list),
    ("tasks", TASKS, list),
    ("plugins", PLUGINS, list),
    ("nvidia", NVIDIA_SMI, dict),
    ("storage_saved", STORAGE_SAVED, dict),
)

# Optional first pages of /api/library-file/list-all, keyed by FileStatus
FILE_LISTS: tuple[tuple[str, int], ...] = (
    ("workers", 2),
    ("upcoming_files", 0),
    ("recently_finished", 1),
)

# duration=0 resumes, so an open-ended pause is sent as one year
PAUSE_INDEFINITELY = 525600


class FileFlowsApiError(Exception):
    """Exception for FileFlows API errors."""


class FileFlowsConnectionError(FileFlowsApiError):
    """Exception for connection errors."""


class FileFlowsAuthError(FileFlowsApiError):
    """Exception for authentication errors."""


class FileFlowsNotFoundError(FileFlowsApiError):
    """Exception for endpoints that answer 404."""


class FileFlowsApiDisabledError(FileFlowsApiError):
    """Exception for a REST API or webhook that is disabled or unlicensed."""


class FileFlowsApi:
    """FileFlows API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        ssl: bool,
        api_token: str | None,
        fenrus_token: str | None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._base_url = str(
            URL.build(scheme="https" if ssl else "http", host=host, port=port)
        )
        self._api_token = api_token
        self._fenrus_token = fenrus_token

    @property
    def base_url(self) -> str:
        """Return the server base URL."""
        return self._base_url

    @property
    def has_api(self) -> bool:
        """Return whether the licensed REST API can be used."""
        return bool(self._api_token)

    def _headers(self, method: str, path: str, payload: bytes | None) -> dict[str, str]:
        if not path.startswith("/api"):
            return {"X-Webhook-Token": self._fenrus_token or ""}
        if not self.has_api:
            raise FileFlowsAuthError("API token required")
        timestamp = str(int(time.time()))
        nonce = uuid4().hex
        body_hash = hashlib.sha256(payload).hexdigest() if payload is not None else ""
        message = f"{method}:{unquote(path)}:{timestamp}:{nonce}:{body_hash}"
        signature = hmac.new(
            self._api_token.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        headers = {"X-Timestamp": timestamp, "X-Nonce": nonce, "X-Signature": signature}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: Any = None,
        plain: bool = False,
    ) -> Any:
        """Send a request and return the decoded JSON body."""
        payload = None if body is None else json.dumps(body).encode()
        headers = self._headers(method, path, payload)
        try:
            async with self._session.request(
                method,
                URL(f"{self._base_url}{path}", encoded=True),
                params=params,
                data=payload,
                headers=headers,
                timeout=TIMEOUT,
            ) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                text = await response.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise FileFlowsConnectionError(f"{method} {path}: {err!r}") from err

        if status == 401:
            reason = text.strip() or "Unauthorized"
            if "timestamp" in reason.lower() or "nonce" in reason.lower():
                raise FileFlowsApiError(f"{method} {path}: {reason}")
            raise FileFlowsAuthError(f"{method} {path}: {reason}")
        if status == 404:
            raise FileFlowsNotFoundError(f"{method} {path}: not found")
        if status >= 400:
            raise FileFlowsApiError(f"{method} {path}: HTTP {status}")
        if not text.strip():
            return None
        if "text/html" in content_type:
            raise FileFlowsApiError(f"{method} {path}: HTML instead of JSON")
        # a plain "26.10" must stay a string, not become the float 26.1
        if plain and content_type.startswith("text/plain"):
            return text.strip()
        try:
            return json.loads(text)
        except ValueError as err:
            raise FileFlowsApiError(f"{method} {path}: invalid JSON") from err

    async def _get(
        self, path: str, kind: type, params: dict[str, str] | None = None
    ) -> Any:
        result = await self._request("GET", path, params=params)
        if not isinstance(result, kind):
            raise FileFlowsApiError(f"GET {path}: unexpected {type(result).__name__}")
        if kind is list:
            return [item for item in result if isinstance(item, dict)]
        return result

    async def _set_state(self, base: str, uid: str, enabled: bool) -> None:
        await self._request(
            "PUT",
            f"{base}/state/{quote(uid, safe='')}",
            params={"enable": str(enabled).lower()},
        )

    async def async_validate(self) -> None:
        """Check that every configured token reaches a working endpoint."""
        try:
            if self.has_api:
                await self.get_status()
            if self._fenrus_token:
                await self.get_fenrus()
        except FileFlowsNotFoundError as err:
            raise FileFlowsApiDisabledError(str(err)) from err

    async def get_fenrus(self) -> dict[str, Any]:
        """Get the licence-free Fenrus summary."""
        return await self._get(FENRUS, dict)

    async def get_status(self) -> dict[str, Any]:
        """Get the processing status."""
        return await self._get(STATUS, dict)

    async def get_version(self) -> str:
        """Get the server version."""
        result = await self._request("GET", SYSTEM_VERSION, plain=True)
        if not isinstance(result, str):
            raise FileFlowsApiError(f"GET {SYSTEM_VERSION}: unexpected response")
        return result

    async def get_library_file_status(self) -> dict[str, int]:
        """Get file counts keyed by status name."""
        counts = dict.fromkeys(FILE_STATUS_NAMES.values(), 0)
        for item in await self._get(FILE_STATUS, list):
            if (name := FILE_STATUS_NAMES.get(item.get("Status"))) is not None:
                counts[name] = item.get("StatusCount") or 0
        return counts

    async def pause_system(self, minutes: int | None = None) -> None:
        """Pause processing, indefinitely when no minutes are given."""
        await self._request(
            "POST",
            SYSTEM_PAUSE,
            params={
                "duration": str(PAUSE_INDEFINITELY if minutes is None else minutes),
                "abort": "false",
            },
        )

    async def resume_system(self) -> None:
        """Resume processing."""
        await self._request(
            "POST", SYSTEM_PAUSE, params={"duration": "0", "abort": "false"}
        )

    async def restart_system(self) -> None:
        """Restart the server."""
        await self._request("POST", SYSTEM_RESTART)

    async def set_node_state(self, uid: str, enabled: bool) -> None:
        """Enable or disable a processing agent."""
        await self._set_state(AGENTS, uid, enabled)

    async def set_library_state(self, uid: str, enabled: bool) -> None:
        """Enable or disable a library."""
        await self._set_state(LIBRARIES, uid, enabled)

    async def set_flow_state(self, uid: str, enabled: bool) -> None:
        """Enable or disable a flow."""
        await self._set_state(FLOWS, uid, enabled)

    async def rescan_libraries(self, uids: list[str] | None = None) -> None:
        """Rescan the given libraries, or all enabled ones."""
        if uids:
            await self._request("PUT", LIBRARY_RESCAN, body={"Uids": uids})
        else:
            await self._request("POST", LIBRARY_RESCAN_ENABLED)

    async def reprocess_files(self, uids: list[str]) -> None:
        """Reprocess library files."""
        await self._request("POST", FILE_REPROCESS, body={"Uids": uids})

    async def unhold_files(self, uids: list[str]) -> None:
        """Release library files that are on hold."""
        await self._request("POST", FILE_UNHOLD, body={"Uids": uids})

    async def force_processing(self, uids: list[str]) -> None:
        """Force processing of library files."""
        await self._request("POST", FILE_FORCE_PROCESSING, body={"Uids": uids})

    async def abort_worker(self, uid: str) -> None:
        """Abort processing of a running library file."""
        await self._request("DELETE", FILE_ABORT, body={"Uids": [uid]})

    async def run_task(self, uid: str) -> None:
        """Run a scheduled task now."""
        await self._request("POST", f"{TASKS}/run/{quote(uid, safe='')}")

    async def get_all_data(self) -> dict[str, Any]:
        """Fetch everything the entities need."""
        if not self.has_api:
            return {"fenrus": await self.get_fenrus()}
        data: dict[str, Any] = {"status": await self.get_status()}
        calls = {key: self._get(path, kind) for key, path, kind in OPTIONAL_ENDPOINTS}
        for key, status in FILE_LISTS:
            calls[key] = self._get(
                FILE_LIST_ALL, list, {"status": str(status), "page": "0"}
            )
        calls["version"] = self.get_version()
        calls["library_file_status"] = self.get_library_file_status()
        if self._fenrus_token:
            calls["fenrus"] = self.get_fenrus()
        # await every call so none is left pending when one of them aborts the refresh
        results = await asyncio.gather(*calls.values(), return_exceptions=True)
        for key, result in zip(calls, results, strict=True):
            if isinstance(result, (FileFlowsConnectionError, FileFlowsAuthError)):
                raise result
            if isinstance(result, FileFlowsApiError):
                # unknown routes answer 200 + HTML, so any API error means "absent"
                _LOGGER.debug("Optional endpoint %s unavailable: %s", key, result)
                result = None
            elif isinstance(result, BaseException):
                raise result
            data[key] = result
        return data
