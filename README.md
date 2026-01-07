# FileFlows Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/RiDDiX/fileflows-ha)](https://github.com/RiDDiX/fileflows-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Home Assistant integration for [FileFlows](https://fileflows.com/) - the powerful automated file processing application for media libraries.

## ✨ Features

### 📊 Comprehensive Monitoring
Monitor your FileFlows server with **24 sensors** covering queue status, processing, storage savings, and system resources:

#### Queue & Processing
- **Queue Size** - Total files in queue
- **Unprocessed Files** - Files waiting to be processed
- **Processing Files** - Currently processing files with detailed progress
- **Processed Files** - Total successfully processed
- **Failed Files** - Failed file count
- **Files On Hold** - Files on hold
- **Files Out of Schedule** - Files outside processing schedule
- **Current File** - Active file with progress and step information
- **Active Workers** - Number of active processing workers
- **Processing Time** - Current processing duration

#### Storage Savings ⭐ NEW in v2.1.0
- **Storage Saved** - Total storage saved in GB with per-library breakdown
  - Items count per library
  - Savings per library
  - Final size per library
- **Storage Saved Percentage** - Overall compression ratio

#### System Resources
- **Processing Nodes** - Number and status of processing nodes
- **Libraries** - Library count with detailed attributes
- **Flows** - Flow count with enabled/disabled status
- **Plugins** - Installed plugins count
- **Scheduled Tasks** - Number of configured tasks
- **Version** - FileFlows version with update status
- **Upcoming Files** - Next files queued for processing
- **Recently Finished** - Recently completed files

### 🎮 NVIDIA GPU Monitoring (Optional)
If your FileFlows server has an NVIDIA GPU, additional sensors are automatically created:
- GPU Usage
- Memory Usage
- Encoder Usage
- Decoder Usage
- GPU Temperature

### 🔘 Binary Sensors
Real-time status indicators:
- **System Paused** - System pause state
- **Processing Active** - Files being processed
- **Has Failed Files** - Failed files present
- **Has Files On Hold** - Files on hold present
- **Queue Not Empty** - Queue has pending files
- **Update Available** - FileFlows update available
- **All Nodes Enabled** - All processing nodes active
- **Per-Node Status** - Individual node states
- **Per-Library Status** - Individual library states

### 🎛️ Control Switches
Full control over your FileFlows system:
- **System Active** - Pause/Resume all processing
- **Node Switches** - Enable/Disable individual processing nodes
- **Library Switches** - Enable/Disable individual libraries
- **Flow Switches** - Enable/Disable individual flows

### 🔲 Action Buttons
Quick actions:
- **Pause/Resume System** - Control processing
- **Restart Server** - Restart FileFlows server
- **Rescan Libraries** - Rescan all or individual libraries
- **Refresh Data** - Manual data refresh
- **Run Tasks** - Execute scheduled tasks on demand

### 🛠️ Services
Advanced automation via Home Assistant services:
- `fileflows.pause_system` / `fileflows.resume_system`
- `fileflows.restart_system`
- `fileflows.enable_node` / `fileflows.disable_node`
- `fileflows.enable_library` / `fileflows.disable_library`
- `fileflows.rescan_library` / `fileflows.rescan_all_libraries`
- `fileflows.enable_flow` / `fileflows.disable_flow`
- `fileflows.reprocess_file`
- `fileflows.force_processing`
- `fileflows.unhold_files`
- `fileflows.abort_worker`
- `fileflows.run_task`

## 📥 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the **⋮** menu → **Custom repositories**
4. Add `https://github.com/RiDDiX/fileflows-ha` as an **Integration**
5. Search for **"FileFlows"** and click **Install**
6. **Restart Home Assistant**
7. Go to **Settings** → **Devices & Services** → **Add Integration** → **FileFlows**

### Manual Installation

1. Download the [latest release](https://github.com/RiDDiX/fileflows-ha/releases)
2. Extract the `custom_components/fileflows` folder to your `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration** → **FileFlows**

## ⚙️ Configuration

### Initial Setup

When adding the integration, you'll need:

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| **Host** | Yes | - | IP address or hostname of FileFlows server |
| **Port** | Yes | 8585 | FileFlows server port |
| **SSL** | No | false | Enable for HTTPS connections |
| **Verify SSL** | No | true | Disable for self-signed certificates |
| **Username** | Recommended | - | FileFlows username |
| **Password** | Recommended | - | FileFlows password |

### Authentication

**Bearer Token Authentication** (Automatic):
- Provide username and password during setup
- Integration automatically obtains and manages Bearer tokens
- Tokens cached for 23 hours and auto-renewed
- Full API access with all 17 endpoints

**Without Authentication**:
- Limited to public `/remote/*` endpoints
- Reduced functionality and data availability
- **Recommended to always use credentials**

## 📊 Dashboard Examples

### Basic Card
```yaml
type: entities
title: FileFlows Status
entities:
  - entity: binary_sensor.fileflows_192_168_178_8_processing_active
  - entity: sensor.fileflows_192_168_178_8_queue_size
  - entity: sensor.fileflows_192_168_178_8_current_file
  - entity: sensor.fileflows_192_168_178_8_storage_saved
  - entity: sensor.fileflows_192_168_178_8_storage_saved_percentage
  - entity: switch.fileflows_192_168_178_8_system_active
```

### Storage Savings Card
```yaml
type: custom:bar-card
entity: sensor.fileflows_192_168_178_8_storage_saved
name: Storage Saved
unit_of_measurement: GB
max: 3000
positions:
  icon: inside
  indicator: inside
  name: inside
  value: inside
severity:
  - color: '#4CAF50'
    from: 0
    to: 3000
```

### Processing Queue Card
```yaml
type: glance
title: FileFlows Queue
entities:
  - entity: sensor.fileflows_192_168_178_8_unprocessed_files
    name: Unprocessed
  - entity: sensor.fileflows_192_168_178_8_processing_files
    name: Processing
  - entity: sensor.fileflows_192_168_178_8_processed_files
    name: Processed
  - entity: sensor.fileflows_192_168_178_8_failed_files
    name: Failed
```

## 🤖 Automation Examples

### Pause FileFlows during Plex Streaming
```yaml
automation:
  - alias: "Pause FileFlows during Plex"
    trigger:
      - platform: numeric_state
        entity_id: sensor.plex_watching
        above: 0
    action:
      - service: fileflows.pause_system

  - alias: "Resume FileFlows after Plex"
    trigger:
      - platform: numeric_state
        entity_id: sensor.plex_watching
        below: 1
        for:
          minutes: 5
    action:
      - service: fileflows.resume_system
```

### Notify on Failed Files
```yaml
automation:
  - alias: "Alert on FileFlows failures"
    trigger:
      - platform: state
        entity_id: binary_sensor.fileflows_192_168_178_8_has_failed_files
        to: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "⚠️ FileFlows Alert"
          message: "{{ states('sensor.fileflows_192_168_178_8_failed_files') }} files have failed processing"
```

### Rescan Library on Schedule
```yaml
automation:
  - alias: "Weekly Library Rescan"
    trigger:
      - platform: time
        at: "03:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: fileflows.rescan_all_libraries
```

### Monitor Storage Savings Milestone
```yaml
automation:
  - alias: "Storage Savings Milestone"
    trigger:
      - platform: numeric_state
        entity_id: sensor.fileflows_192_168_178_8_storage_saved
        above: 2500
    action:
      - service: notify.mobile_app_phone
        data:
          title: "🎉 FileFlows Milestone!"
          message: "You've saved {{ states('sensor.fileflows_192_168_178_8_storage_saved') }} GB!"
```

## 🔌 API Coverage

The integration uses **17 working FileFlows API endpoints**:

### Core Endpoints
- `/api/status` - Real-time system status
- `/api/statistics/storage-saved` - Detailed storage statistics ⭐ NEW
- `/api/library-file/status` - File status overview
- `/api/settings/fileflows-status` - System pause state

### Resource Endpoints
- `/api/node` - Processing nodes
- `/api/library` - Libraries configuration
- `/api/flow` - Processing flows
- `/api/plugin` - Installed plugins
- `/api/task` - Scheduled tasks

### Data Endpoints
- `/api/library-file/upcoming` - Queue preview
- `/api/library-file/recently-finished` - Recent completions
- `/api/nvidia/smi` - NVIDIA GPU stats (if available)

### Version & Updates
- `/api/system/version` - Version information

See [API_ENDPOINTS.md](API_ENDPOINTS.md) for complete endpoint documentation.

## 📚 Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [API_ENDPOINTS.md](API_ENDPOINTS.md) - Complete API endpoint reference
- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Detailed setup guide and troubleshooting

## 🐛 Troubleshooting

### Integration won't connect
- Verify FileFlows is running and accessible
- Check host/port are correct
- Ensure credentials are valid
- Test manually: `curl -X POST -H "Content-Type: application/json" -d '{"username":"USER","password":"PASS"}' http://HOST:8585/authorize`

### Sensors show "unknown"
- Ensure username/password are configured
- Check Home Assistant logs for errors
- Reload the integration
- See [SETUP_COMPLETE.md](SETUP_COMPLETE.md) for detailed troubleshooting

### Some sensors missing
- **CPU/Memory sensors**: Removed in v2.1.1 (endpoint doesn't exist on modern FileFlows)
- **NVIDIA sensors**: Only created if GPU detected
- **Failed/On Hold sensors**: May show "unknown" if endpoint unavailable

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💡 Credits

- Created by [@RiDDiX](https://github.com/RiDDiX)
- Built for [FileFlows](https://fileflows.com/)
- Developed with assistance from Claude Code

## 🔗 Links

- [GitHub Repository](https://github.com/RiDDiX/fileflows-ha)
- [Issue Tracker](https://github.com/RiDDiX/fileflows-ha/issues)
- [FileFlows Official Site](https://fileflows.com/)
- [FileFlows Documentation](https://fileflows.com/docs)

---

**Latest Release**: v2.1.1 | **Sensors**: 24 Core + 5 NVIDIA | **API Endpoints**: 17 Working
