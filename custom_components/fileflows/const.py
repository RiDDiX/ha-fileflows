"""Constants for the FileFlows integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "fileflows"

CONF_SSL: Final = "ssl"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_API_TOKEN: Final = "api_token"
CONF_FENRUS_TOKEN: Final = "fenrus_token"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_PORT: Final = 8585
DEFAULT_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = 30

SERVICE_PAUSE_SYSTEM: Final = "pause_system"
SERVICE_RESUME_SYSTEM: Final = "resume_system"
SERVICE_RESTART_SYSTEM: Final = "restart_system"
SERVICE_ENABLE_NODE: Final = "enable_node"
SERVICE_DISABLE_NODE: Final = "disable_node"
SERVICE_ENABLE_LIBRARY: Final = "enable_library"
SERVICE_DISABLE_LIBRARY: Final = "disable_library"
SERVICE_RESCAN_LIBRARY: Final = "rescan_library"
SERVICE_RESCAN_ALL_LIBRARIES: Final = "rescan_all_libraries"
SERVICE_ENABLE_FLOW: Final = "enable_flow"
SERVICE_DISABLE_FLOW: Final = "disable_flow"
SERVICE_REPROCESS_FILE: Final = "reprocess_file"
SERVICE_ABORT_WORKER: Final = "abort_worker"
SERVICE_RUN_TASK: Final = "run_task"
SERVICE_FORCE_PROCESSING: Final = "force_processing"
SERVICE_UNHOLD_FILES: Final = "unhold_files"

ATTR_NODE_UID: Final = "node_uid"
ATTR_LIBRARY_UID: Final = "library_uid"
ATTR_FLOW_UID: Final = "flow_uid"
ATTR_FILE_UID: Final = "file_uid"
ATTR_WORKER_UID: Final = "worker_uid"
ATTR_TASK_UID: Final = "task_uid"
ATTR_MINUTES: Final = "minutes"
