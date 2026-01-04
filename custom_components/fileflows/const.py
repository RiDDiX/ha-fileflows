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

# API Endpoints - Remote Info (public/status endpoints)
API_STATUS: Final = "/remote/info/status"
API_SHRINKAGE: Final = "/remote/info/shrinkage-groups"
API_UPDATE_AVAILABLE: Final = "/remote/info/update-available"
API_VERSION: Final = "/remote/info/version"

# API Endpoints - System
API_SYSTEM_INFO: Final = "/api/system/info"
API_SYSTEM_PAUSE: Final = "/api/system/pause"
API_SYSTEM_RESUME: Final = "/api/system/resume"

# API Endpoints - Nodes
API_NODES: Final = "/api/node"
API_NODE_BY_UID: Final = "/api/node/{uid}"
API_NODE_ENABLE: Final = "/api/node/state/{uid}?enable=true"
API_NODE_DISABLE: Final = "/api/node/state/{uid}?enable=false"

# API Endpoints - Libraries
API_LIBRARIES: Final = "/api/library"
API_LIBRARY_BY_UID: Final = "/api/library/{uid}"
API_LIBRARY_RESCAN: Final = "/api/library/rescan/{uid}"

# API Endpoints - Library Files
API_LIBRARY_FILES: Final = "/api/library-file"
API_LIBRARY_FILES_UNPROCESSED: Final = "/api/library-file/unprocessed"
API_LIBRARY_FILES_PROCESSING: Final = "/api/library-file/processing"
API_LIBRARY_FILES_PROCESSED: Final = "/api/library-file/processed"
API_LIBRARY_FILES_FAILED: Final = "/api/library-file/failed"
API_LIBRARY_FILE_REPROCESS: Final = "/api/library-file/reprocess/{uid}"

# API Endpoints - Flows
API_FLOWS: Final = "/api/flow"

# API Endpoints - Statistics/Dashboard
API_STATISTICS: Final = "/api/statistics"
API_STATISTICS_RUNNING: Final = "/api/statistics/running"
API_WORKERS: Final = "/api/worker"
API_SETTINGS: Final = "/api/settings"
API_LOG: Final = "/api/log"
API_DASHBOARD_SUMMARY: Final = "/api/dashboard/summary"

# Auth Header
AUTH_HEADER: Final = "x-token"

# Services
SERVICE_PAUSE_SYSTEM: Final = "pause_system"
SERVICE_RESUME_SYSTEM: Final = "resume_system"
SERVICE_ENABLE_NODE: Final = "enable_node"
SERVICE_DISABLE_NODE: Final = "disable_node"
SERVICE_RESCAN_LIBRARY: Final = "rescan_library"
SERVICE_REPROCESS_FILE: Final = "reprocess_file"

# Attributes
ATTR_NODE_UID: Final = "node_uid"
ATTR_LIBRARY_UID: Final = "library_uid"
ATTR_FILE_UID: Final = "file_uid"

# Sensors
SENSOR_TYPES: Final = {
    "system_status": {
        "name": "System Status",
        "icon": "mdi:server",
        "unit": None,
        "device_class": None,
    },
    "files_unprocessed": {
        "name": "Unprocessed Files",
        "icon": "mdi:file-clock-outline",
        "unit": "files",
        "device_class": None,
    },
    "files_processing": {
        "name": "Processing Files",
        "icon": "mdi:file-sync-outline",
        "unit": "files",
        "device_class": None,
    },
    "files_processed": {
        "name": "Processed Files",
        "icon": "mdi:file-check-outline",
        "unit": "files",
        "device_class": None,
    },
    "files_failed": {
        "name": "Failed Files",
        "icon": "mdi:file-alert-outline",
        "unit": "files",
        "device_class": None,
    },
    "total_files": {
        "name": "Total Files",
        "icon": "mdi:file-multiple-outline",
        "unit": "files",
        "device_class": None,
    },
    "storage_saved": {
        "name": "Storage Saved",
        "icon": "mdi:harddisk",
        "unit": "GB",
        "device_class": None,
    },
    "storage_saved_percent": {
        "name": "Storage Saved Percentage",
        "icon": "mdi:percent",
        "unit": "%",
        "device_class": None,
    },
    "active_runners": {
        "name": "Active Runners",
        "icon": "mdi:run-fast",
        "unit": "runners",
        "device_class": None,
    },
    "total_runners": {
        "name": "Total Runners",
        "icon": "mdi:account-group",
        "unit": "runners",
        "device_class": None,
    },
    "cpu_usage": {
        "name": "CPU Usage",
        "icon": "mdi:chip",
        "unit": "%",
        "device_class": None,
    },
    "memory_usage": {
        "name": "Memory Usage",
        "icon": "mdi:memory",
        "unit": "%",
        "device_class": None,
    },
    "current_file": {
        "name": "Current Processing File",
        "icon": "mdi:file-video-outline",
        "unit": None,
        "device_class": None,
    },
    "processing_time": {
        "name": "Average Processing Time",
        "icon": "mdi:timer-outline",
        "unit": "min",
        "device_class": None,
    },
    "queue_eta": {
        "name": "Queue ETA",
        "icon": "mdi:calendar-clock",
        "unit": None,
        "device_class": None,
    },
}

# Binary Sensors
BINARY_SENSOR_TYPES: Final = {
    "system_paused": {
        "name": "System Paused",
        "icon_on": "mdi:pause-circle",
        "icon_off": "mdi:play-circle",
        "device_class": None,
    },
    "processing_active": {
        "name": "Processing Active",
        "icon_on": "mdi:progress-clock",
        "icon_off": "mdi:progress-check",
        "device_class": "running",
    },
    "system_healthy": {
        "name": "System Healthy",
        "icon_on": "mdi:check-circle",
        "icon_off": "mdi:alert-circle",
        "device_class": "problem",
    },
}
