# FileFlows Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/RiDDiX/fileflows-ha)](https://github.com/RiDDiX/fileflows-ha/releases)

A comprehensive Home Assistant integration for [FileFlows](https://fileflows.com/) - the automated file processing application.

## Features

### Sensors
- **Queue Size** - Total files in queue (unprocessed + processing)
- **Unprocessed Files** - Files waiting to be processed
- **Processing Files** - Files currently being processed
- **Processed Files** - Successfully processed files count
- **Failed Files** - Failed file count
- **Files On Hold** - Files on hold count
- **Files Out of Schedule** - Files outside processing schedule
- **Current File** - Currently processing file name
- **Active Workers** - Number of active processing workers
- **Storage Saved** - Total storage saved (GB)
- **Storage Saved Percentage** - Percentage of storage saved
- **CPU Usage** - FileFlows server CPU usage
- **Memory Usage** - FileFlows server memory usage
- **Temp Directory Size** - Size of temp directory
- **Log Directory Size** - Size of log directory
- **Processing Nodes** - Number of processing nodes
- **Libraries** - Number of libraries
- **Flows** - Number of flows
- **Plugins** - Number of plugins
- **Scheduled Tasks** - Number of scheduled tasks
- **Version** - FileFlows version
- **Upcoming Files** - Next files to process
- **Recently Finished** - Recently completed files

### NVIDIA Sensors (if available)
- GPU Usage
- Memory Usage
- Encoder Usage
- Decoder Usage
- Temperature

### Binary Sensors
- **System Paused** - Whether the system is paused
- **Processing Active** - Whether files are being processed
- **Has Failed Files** - Whether there are failed files
- **Has Files On Hold** - Whether there are files on hold
- **Queue Not Empty** - Whether the queue has files
- **Update Available** - Whether a FileFlows update is available
- **All Nodes Enabled** - Whether all nodes are enabled
- **NVIDIA Available** - Whether NVIDIA GPU is available
- **Per-Node Status** - Individual node enabled status
- **Per-Library Status** - Individual library enabled status

### Switches
- **System Active** - Pause/Resume FileFlows processing
- **Per-Node Switches** - Enable/Disable individual nodes
- **Per-Library Switches** - Enable/Disable individual libraries
- **Per-Flow Switches** - Enable/Disable individual flows

### Buttons
- **Pause System** - Pause FileFlows
- **Resume System** - Resume FileFlows
- **Restart Server** - Restart FileFlows server
- **Rescan All Libraries** - Rescan all enabled libraries
- **Refresh Data** - Manually refresh data
- **Per-Library Rescan** - Rescan individual libraries
- **Per-Task Run** - Run scheduled tasks

### Services
- `fileflows.pause_system` - Pause processing
- `fileflows.resume_system` - Resume processing
- `fileflows.restart_system` - Restart server
- `fileflows.enable_node` / `fileflows.disable_node` - Node control
- `fileflows.enable_library` / `fileflows.disable_library` - Library control
- `fileflows.rescan_library` / `fileflows.rescan_all_libraries` - Library rescan
- `fileflows.enable_flow` / `fileflows.disable_flow` - Flow control
- `fileflows.reprocess_file` - Reprocess a file
- `fileflows.force_processing` - Force process out-of-schedule files
- `fileflows.unhold_files` - Unhold files
- `fileflows.abort_worker` - Abort a running worker
- `fileflows.run_task` - Run a scheduled task

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add `https://github.com/RiDDiX/fileflows-ha` as an Integration
5. Search for "FileFlows" and install
6. Restart Home Assistant
7. Go to Settings → Devices & Services → Add Integration → FileFlows

### Manual Installation

1. Download the latest release from GitHub
2. Extract the `custom_components/fileflows` folder to your `config/custom_components/` directory
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Add Integration → FileFlows

## Configuration

During setup, you'll need:
- **Host**: IP address or hostname of your FileFlows server
- **Port**: Port number (default: 8585)
- **SSL**: Enable if using HTTPS
- **Verify SSL**: Disable for self-signed certificates
- **Username**: FileFlows username (optional - required for full API access)
- **Password**: FileFlows password (optional - required for full API access)

### Authentication

The integration uses Bearer token authentication:
- If credentials are provided, the integration will automatically login and obtain a Bearer token
- Bearer tokens are cached for 23 hours and automatically renewed when needed
- Without credentials, only public `/remote/*` endpoints are accessible (limited data)

## Example Dashboard Card

```yaml
type: entities
title: FileFlows
entities:
  - entity: binary_sensor.fileflows_processing_active
  - entity: sensor.fileflows_queue_size
  - entity: sensor.fileflows_current_file
  - entity: sensor.fileflows_storage_saved
  - entity: sensor.fileflows_cpu_usage
  - entity: sensor.fileflows_memory_usage
  - entity: switch.fileflows_system_active
```

## Automation Examples

### Pause FileFlows during Plex streaming

```yaml
automation:
  - alias: "Pause FileFlows during Plex"
    trigger:
      - platform: state
        entity_id: sensor.plex_watching
        to: "1"
    action:
      - service: fileflows.pause_system

  - alias: "Resume FileFlows after Plex"
    trigger:
      - platform: state
        entity_id: sensor.plex_watching
        to: "0"
        for:
          minutes: 5
    action:
      - service: fileflows.resume_system
```

### Notify on failed files

```yaml
automation:
  - alias: "Notify FileFlows failures"
    trigger:
      - platform: state
        entity_id: binary_sensor.fileflows_has_failed_files
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "FileFlows Alert"
          message: "{{ state_attr('sensor.fileflows_files_failed', 'failed_count') }} files have failed processing"
```

## API Coverage

This integration uses the following FileFlows API endpoints:
- `/api/status` - System status
- `/api/system/info` - System information (CPU, memory)
- `/api/system/version` - Version info
- `/api/system/pause` - Pause/Resume
- `/api/system/restart` - Server restart
- `/api/settings/fileflows-status` - FileFlows status
- `/api/node` - Processing nodes
- `/api/library` - Libraries
- `/api/library-file/status` - File status counts
- `/api/library-file/upcoming` - Upcoming files
- `/api/library-file/recently-finished` - Recent files
- `/api/library-file/shrinkage-groups` - Storage savings
- `/api/flow` - Flows
- `/api/worker` - Running workers
- `/api/task` - Scheduled tasks
- `/api/plugin` - Plugins
- `/api/nvidia/smi` - NVIDIA GPU info

## Support

- [GitHub Issues](https://github.com/RiDDiX/fileflows-ha/issues)
- [FileFlows Documentation](https://fileflows.com/docs)

## License

MIT License
