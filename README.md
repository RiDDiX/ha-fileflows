# FileFlows Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/RiDDiX/ha-fileflows)](https://github.com/RiDDiX/ha-fileflows/releases)
[![License](https://img.shields.io/github/license/RiDDiX/ha-fileflows)](LICENSE)

A Home Assistant integration for [FileFlows](https://fileflows.com/) - a powerful file processing application for media transcoding and automation.

## Features

### Sensors
- **Unprocessed Files** - Number of files waiting to be processed
- **Processing Files** - Number of files currently being processed
- **Processed Files** - Total number of successfully processed files
- **Failed Files** - Number of files that failed processing
- **Storage Saved** - Total storage saved in GB
- **Storage Saved Percentage** - Percentage of storage saved
- **Active Runners** - Number of currently active processing runners
- **Total Runners** - Total number of available runners
- **Current Processing File** - Name of the file currently being processed
- **FileFlows Version** - Current version of FileFlows
- **Processing Nodes** - Number of processing nodes
- **Libraries** - Number of configured libraries
- **Flows** - Number of configured flows

### Binary Sensors
- **System Paused** - Whether the system is paused
- **Processing Active** - Whether any files are currently processing
- **Has Failed Files** - Whether there are any failed files
- **Queue Has Files** - Whether there are files in the queue
- **All Nodes Enabled** - Whether all nodes are enabled
- **Node [Name] Enabled** - Per-node enabled status

### Switches
- **System Active** - Toggle to pause/resume the system
- **Node [Name]** - Per-node enable/disable switches

### Buttons
- **Pause System** - Pause all processing
- **Resume System** - Resume processing
- **Refresh Data** - Manually refresh all data
- **Rescan [Library]** - Per-library rescan buttons

### Services
- `fileflows.pause_system` - Pause the processing system
- `fileflows.resume_system` - Resume the processing system
- `fileflows.enable_node` - Enable a specific node
- `fileflows.disable_node` - Disable a specific node
- `fileflows.rescan_library` - Rescan a specific library
- `fileflows.reprocess_file` - Reprocess a specific file

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/RiDDiX/ha-fileflows` as a custom repository (Category: Integration)
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/RiDDiX/ha-fileflows/releases)
2. Extract the `custom_components/fileflows` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "FileFlows"
4. Enter your FileFlows server details:
   - **Host**: IP address or hostname of your FileFlows server
   - **Port**: Port number (default: 19200)
   - **SSL**: Enable if using HTTPS
   - **Verify SSL**: Verify SSL certificate
   - **Access Token**: Optional, if authentication is enabled

## Example Lovelace Cards

### Status Overview Card

```yaml
type: entities
title: FileFlows Status
entities:
  - entity: binary_sensor.fileflows_processing_active
  - entity: sensor.fileflows_unprocessed_files
  - entity: sensor.fileflows_processing_files
  - entity: sensor.fileflows_current_processing_file
  - entity: sensor.fileflows_storage_saved
  - entity: sensor.fileflows_active_runners
  - entity: switch.fileflows_system_active
```

### Control Card

```yaml
type: horizontal-stack
cards:
  - type: button
    entity: button.fileflows_pause_system
    name: Pause
    icon: mdi:pause
    tap_action:
      action: call-service
      service: button.press
      target:
        entity_id: button.fileflows_pause_system
  - type: button
    entity: button.fileflows_resume_system
    name: Resume
    icon: mdi:play
    tap_action:
      action: call-service
      service: button.press
      target:
        entity_id: button.fileflows_resume_system
  - type: button
    entity: button.fileflows_refresh_data
    name: Refresh
    icon: mdi:refresh
    tap_action:
      action: call-service
      service: button.press
      target:
        entity_id: button.fileflows_refresh_data
```

### Statistics Card

```yaml
type: statistics-graph
title: Storage Saved Over Time
entities:
  - sensor.fileflows_storage_saved
stat_types:
  - max
  - mean
period:
  calendar:
    period: month
```

### Gauge Card

```yaml
type: gauge
entity: sensor.fileflows_storage_saved_percent
name: Storage Savings
min: 0
max: 100
severity:
  green: 50
  yellow: 30
  red: 0
```

## Automation Examples

### Notify When Processing Completes

```yaml
automation:
  - alias: "FileFlows Processing Complete"
    trigger:
      - platform: state
        entity_id: binary_sensor.fileflows_processing_active
        from: "on"
        to: "off"
    condition:
      - condition: state
        entity_id: sensor.fileflows_unprocessed_files
        state: "0"
    action:
      - service: notify.mobile_app
        data:
          title: "FileFlows"
          message: "All files have been processed!"
```

### Pause During Peak Hours

```yaml
automation:
  - alias: "Pause FileFlows During Peak Hours"
    trigger:
      - platform: time
        at: "18:00:00"
    action:
      - service: fileflows.pause_system

  - alias: "Resume FileFlows After Peak Hours"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: fileflows.resume_system
```

### Alert on Failed Files

```yaml
automation:
  - alias: "FileFlows Failed Files Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.fileflows_has_failed_files
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "FileFlows Alert"
          message: "{{ states('sensor.fileflows_files_failed') }} files have failed processing"
```

## Troubleshooting

### Cannot Connect
- Verify the FileFlows server is running
- Check the host and port are correct
- Ensure there's no firewall blocking the connection
- If using SSL, verify the certificate is valid

### Data Not Updating
- Check the FileFlows server logs for errors
- Try pressing the "Refresh Data" button
- Verify the API is accessible at `http://your-server:19200/api/help`

### Authentication Issues
- If FileFlows has authentication enabled, provide the access token
- Check the token is correct and hasn't expired

## Support

- [FileFlows Documentation](https://fileflows.com/docs)
- [FileFlows Discord](https://discord.gg/fileflows)
- [Report Issues](https://github.com/RiDDiX/ha-fileflows/issues)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FileFlows](https://fileflows.com/) by revenz
- [Home Assistant](https://www.home-assistant.io/)
