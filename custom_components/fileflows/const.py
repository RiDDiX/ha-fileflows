"""Constants for the FileFlows integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "fileflows"

# Configuration
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_SSL: Final = "ssl"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_ACCESS_TOKEN: Final = "access_token"

# Defaults
DEFAULT_PORT: Final = 19200
DEFAULT_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)

# Auth Header
AUTH_HEADER: Final = "x-token"

# =============================================================================
# Remote/Public Endpoints (no auth required)
# =============================================================================
API_REMOTE_STATUS: Final = "/remote/info/status"
API_REMOTE_SHRINKAGE: Final = "/remote/info/shrinkage-groups"
API_REMOTE_UPDATE_AVAILABLE: Final = "/remote/info/update-available"
API_REMOTE_VERSION: Final = "/remote/info/version"

# =============================================================================
# API Endpoints - Status (authenticated)
# =============================================================================
API_STATUS: Final = "/api/status"
API_STATUS_UPDATE_AVAILABLE: Final = "/api/status/update-available"

# =============================================================================
# API Endpoints - System
# =============================================================================
API_SYSTEM_VERSION: Final = "/api/system/version"
API_SYSTEM_INFO: Final = "/api/system/info"
API_SYSTEM_PAUSE: Final = "/api/system/pause"
API_SYSTEM_RESTART: Final = "/api/system/restart"
API_SYSTEM_NODE_UPDATE_VERSION: Final = "/api/system/node-update-version"
API_SYSTEM_NODE_UPDATER_AVAILABLE: Final = "/api/system/node-updater-available"
API_SYSTEM_HISTORY_CPU: Final = "/api/system/history-data/cpu"
API_SYSTEM_HISTORY_MEMORY: Final = "/api/system/history-data/memory"
API_SYSTEM_HISTORY_DB_CONNECTIONS: Final = "/api/system/history-data/database-connections"
API_SYSTEM_HISTORY_TEMP_STORAGE: Final = "/api/system/history-data/temp-storage"
API_SYSTEM_HISTORY_LOG_STORAGE: Final = "/api/system/history-data/log-storage"
API_SYSTEM_HISTORY_PROCESSING_TIME: Final = "/api/system/history-data/library-processing-time"
API_SYSTEM_HISTORY_HEATMAP: Final = "/api/system/history-data/processing-heatmap"

# =============================================================================
# API Endpoints - Settings
# =============================================================================
API_SETTINGS: Final = "/api/settings"
API_SETTINGS_FILEFLOWS_STATUS: Final = "/api/settings/fileflows-status"
API_SETTINGS_CHECK_UPDATE: Final = "/api/settings/check-update-available"
API_SETTINGS_UI: Final = "/api/settings/ui-settings"
API_SETTINGS_CONFIG_REVISION: Final = "/api/settings/current-config/revision"
API_SETTINGS_CURRENT_CONFIG: Final = "/api/settings/current-config"

# =============================================================================
# API Endpoints - Dashboard
# =============================================================================
API_DASHBOARD: Final = "/api/dashboard"
API_DASHBOARD_LIST: Final = "/api/dashboard/list"
API_DASHBOARD_WIDGETS: Final = "/api/dashboard/{uid}/Widgets"

# =============================================================================
# API Endpoints - Node (Processing Nodes)
# =============================================================================
API_NODES: Final = "/api/node"
API_NODE_BY_UID: Final = "/api/node/{uid}"
API_NODE_STATE: Final = "/api/node/state/{uid}"
API_NODE_BY_ADDRESS: Final = "/api/node/by-address/{address}"
API_NODE_REGISTER: Final = "/api/node/register"

# =============================================================================
# API Endpoints - Library
# =============================================================================
API_LIBRARIES: Final = "/api/library"
API_LIBRARY_BY_UID: Final = "/api/library/{uid}"
API_LIBRARY_STATE: Final = "/api/library/state/{uid}"
API_LIBRARY_RESCAN: Final = "/api/library/rescan"
API_LIBRARY_RESCAN_ENABLED: Final = "/api/library/rescan-enabled"
API_LIBRARY_TEMPLATES: Final = "/api/library/templates"

# =============================================================================
# API Endpoints - Library Files
# =============================================================================
API_LIBRARY_FILES: Final = "/api/library-file"
API_LIBRARY_FILE_LIST_ALL: Final = "/api/library-file/list-all"
API_LIBRARY_FILE_BY_UID: Final = "/api/library-file/{uid}"
API_LIBRARY_FILE_UPCOMING: Final = "/api/library-file/upcoming"
API_LIBRARY_FILE_RECENTLY_FINISHED: Final = "/api/library-file/recently-finished"
API_LIBRARY_FILE_STATUS: Final = "/api/library-file/status"
API_LIBRARY_FILE_SHRINKAGE_GROUPS: Final = "/api/library-file/shrinkage-groups"
API_LIBRARY_FILE_SHRINKAGE_CHART: Final = "/api/library-file/shrinkage-bar-chart"
API_LIBRARY_FILE_REPROCESS: Final = "/api/library-file/reprocess"
API_LIBRARY_FILE_UNHOLD: Final = "/api/library-file/unhold"
API_LIBRARY_FILE_FORCE: Final = "/api/library-file/force-processing"
API_LIBRARY_FILE_TOGGLE_FORCE: Final = "/api/library-file/toggle-force"
API_LIBRARY_FILE_SET_STATUS: Final = "/api/library-file/set-status/{status}"
API_LIBRARY_FILE_MOVE_TO_TOP: Final = "/api/library-file/move-to-top"
API_LIBRARY_FILE_SEARCH: Final = "/api/library-file/search"
API_LIBRARY_FILE_DELETE: Final = "/api/library-file/delete-files"
API_LIBRARY_FILE_LOG: Final = "/api/library-file/{uid}/log"
API_LIBRARY_FILE_PROCESS: Final = "/api/library-file/process-file"

# =============================================================================
# API Endpoints - Flow
# =============================================================================
API_FLOWS: Final = "/api/flow"
API_FLOW_BY_UID: Final = "/api/flow/{uid}"
API_FLOW_LIST_ALL: Final = "/api/flow/list-all"
API_FLOW_STATE: Final = "/api/flow/state/{uid}"
API_FLOW_SET_DEFAULT: Final = "/api/flow/set-default/{uid}"
API_FLOW_ELEMENTS: Final = "/api/flow/elements"
API_FLOW_EXPORT: Final = "/api/flow/export"
API_FLOW_IMPORT: Final = "/api/flow/import"
API_FLOW_DUPLICATE: Final = "/api/flow/duplicate/{uid}"
API_FLOW_RENAME: Final = "/api/flow/{uid}/rename"
API_FLOW_FAILURE_BY_LIBRARY: Final = "/api/flow/failure-flow/by-library/{libraryUid}"

# =============================================================================
# API Endpoints - Worker (Running Executors)
# =============================================================================
API_WORKERS: Final = "/api/worker"
API_WORKER_LOG: Final = "/api/worker/{uid}/log"
API_WORKER_ABORT: Final = "/api/worker/{uid}"
API_WORKER_ABORT_BY_FILE: Final = "/api/worker/by-file/{uid}"
API_WORKER_CLEAR: Final = "/api/worker/clear/{nodeUid}"
API_WORKER_START: Final = "/api/worker/work/start"
API_WORKER_FINISH: Final = "/api/worker/work/finish"
API_WORKER_UPDATE: Final = "/api/worker/work/update"

# =============================================================================
# API Endpoints - Statistics
# =============================================================================
API_STATISTICS_RECORD: Final = "/api/statistics/record"
API_STATISTICS_BY_NAME: Final = "/api/statistics/by-name/{name}"
API_STATISTICS_CLEAR: Final = "/api/statistics/clear"

# =============================================================================
# API Endpoints - Log
# =============================================================================
API_LOG: Final = "/api/fileflows-log"
API_LOG_SOURCES: Final = "/api/fileflows-log/log-sources"
API_LOG_SEARCH: Final = "/api/fileflows-log/search"
API_LOG_DOWNLOAD: Final = "/api/fileflows-log/download"
API_LOG_MESSAGE: Final = "/api/fileflows-log/message"

# =============================================================================
# API Endpoints - Plugin
# =============================================================================
API_PLUGINS: Final = "/api/plugin"
API_PLUGIN_BY_UID: Final = "/api/plugin/{uid}"
API_PLUGIN_BY_NAME: Final = "/api/plugin/by-package-name/{name}"
API_PLUGIN_PACKAGES: Final = "/api/plugin/plugin-packages"
API_PLUGIN_UPDATE: Final = "/api/plugin/update"
API_PLUGIN_DOWNLOAD: Final = "/api/plugin/download"
API_PLUGIN_STATE: Final = "/api/plugin/state/{uid}"
API_PLUGIN_SETTINGS: Final = "/api/plugin/{packageName}/settings"

# =============================================================================
# API Endpoints - Task (Scheduled Tasks)
# =============================================================================
API_TASKS: Final = "/api/task"
API_TASK_BY_UID: Final = "/api/task/{uid}"
API_TASK_BY_NAME: Final = "/api/task/name/{name}"
API_TASK_RUN: Final = "/api/task/run/{uid}"

# =============================================================================
# API Endpoints - Variable
# =============================================================================
API_VARIABLES: Final = "/api/variable"
API_VARIABLE_BY_UID: Final = "/api/variable/{uid}"
API_VARIABLE_BY_NAME: Final = "/api/variable/name/{name}"

# =============================================================================
# API Endpoints - Script
# =============================================================================
API_SCRIPTS: Final = "/api/script"
API_SCRIPT_BY_NAME: Final = "/api/script/{name}"
API_SCRIPT_CODE: Final = "/api/script/{name}/code"
API_SCRIPT_TEMPLATES: Final = "/api/script/templates"
API_SCRIPT_BY_TYPE: Final = "/api/script/all-by-type/{type}"
API_SCRIPT_LIST: Final = "/api/script/list/{type}"
API_SCRIPT_VALIDATE: Final = "/api/script/validate"
API_SCRIPT_EXPORT: Final = "/api/script/export/{name}"
API_SCRIPT_IMPORT: Final = "/api/script/import"
API_SCRIPT_DUPLICATE: Final = "/api/script/duplicate/{name}"

# =============================================================================
# API Endpoints - Repository
# =============================================================================
API_REPOSITORY_SCRIPTS: Final = "/api/repository/scripts"
API_REPOSITORY_CONTENT: Final = "/api/repository/content"
API_REPOSITORY_DOWNLOAD: Final = "/api/repository/download"
API_REPOSITORY_UPDATE: Final = "/api/repository/update-scripts"

# =============================================================================
# API Endpoints - Revision
# =============================================================================
API_REVISIONS: Final = "/api/revision/{uid}"
API_REVISION_LIST: Final = "/api/revision/list"
API_REVISION_SPECIFIC: Final = "/api/revision/{uid}/revision/{revisionUid}"
API_REVISION_RESTORE: Final = "/api/revision/{uid}/restore/{revisionUid}"

# =============================================================================
# API Endpoints - NVIDIA
# =============================================================================
API_NVIDIA_SMI: Final = "/api/nvidia/smi"

# =============================================================================
# API Endpoints - Webhook
# =============================================================================
API_WEBHOOKS: Final = "/api/webhook"
API_WEBHOOK_BY_NAME: Final = "/api/webhook/{name}"

# =============================================================================
# File Status Constants
# =============================================================================
FILE_STATUS_UNPROCESSED: Final = 0
FILE_STATUS_PROCESSED: Final = 1
FILE_STATUS_PROCESSING: Final = 2
FILE_STATUS_FLOW_NOT_FOUND: Final = 3
FILE_STATUS_FAILED: Final = 4
FILE_STATUS_DUPLICATE: Final = 5
FILE_STATUS_MAPPING_ISSUE: Final = 6
FILE_STATUS_ON_HOLD: Final = 7
FILE_STATUS_DISABLED: Final = 8
FILE_STATUS_OUT_OF_SCHEDULE: Final = 9

FILE_STATUS_NAMES: Final = {
    0: "Unprocessed",
    1: "Processed",
    2: "Processing",
    3: "Flow Not Found",
    4: "Failed",
    5: "Duplicate",
    6: "Mapping Issue",
    7: "On Hold",
    8: "Disabled",
    9: "Out of Schedule",
}

# =============================================================================
# Services
# =============================================================================
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
SERVICE_CANCEL_FILE: Final = "cancel_file"
SERVICE_FORCE_PROCESSING: Final = "force_processing"
SERVICE_UNHOLD_FILES: Final = "unhold_files"

# =============================================================================
# Attributes
# =============================================================================
ATTR_NODE_UID: Final = "node_uid"
ATTR_LIBRARY_UID: Final = "library_uid"
ATTR_FLOW_UID: Final = "flow_uid"
ATTR_FILE_UID: Final = "file_uid"
ATTR_WORKER_UID: Final = "worker_uid"
ATTR_TASK_UID: Final = "task_uid"
ATTR_ENABLED: Final = "enabled"
