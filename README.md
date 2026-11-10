# FileFlows Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/RiDDiX/ha-fileflows)](https://github.com/RiDDiX/ha-fileflows/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Home Assistant integration for [FileFlows](https://fileflows.com/). Shows queue, processing and storage savings, and lets you pause/resume the server, toggle nodes, libraries and flows, and run rescans and tasks.

## Requirements

- Home Assistant 2025.8 or newer
- FileFlows 26.10 or newer for the API token. Older servers only work with the Fenrus token.

## Installation

### HACS

1. HACS > three-dot menu > **Custom repositories**
2. Add `https://github.com/RiDDiX/ha-fileflows` as type **Integration**
3. Install **FileFlows** and restart Home Assistant
4. **Settings > Devices & Services > Add Integration > FileFlows**

### Manual

Copy `custom_components/fileflows` from the [latest release](https://github.com/RiDDiX/ha-fileflows/releases) into `config/custom_components/`, restart, then add the integration as above.

## Setup

| Field | Default | Notes |
|-------|---------|-------|
| Host | | IP or hostname, no `http://` |
| Port | 8585 | |
| Use SSL | off | Turn on if FileFlows is served over HTTPS |
| Verify SSL Certificate | on | Turn off for self-signed certificates |
| API token | | Full access, see below |
| Fenrus webhook token | | Read-only, see below |

You need at least one of the two tokens. Both can be set at the same time.

**API token** (needs a FileFlows licence): in FileFlows open **Config > API**, enable it and copy the token. Requests are HMAC-signed with it; the token itself is never sent over the network. This gives you every entity, button and service.

**Fenrus webhook token** (free): in FileFlows open **Config > Admin > General > Fenrus Dashboard Endpoint**. It is off by default. This is read-only and gives file counts per status, update available and per-library original/final size (storage saved). With only this token there are no node, library, flow, task or worker entities, no switches, Refresh Data is the only button, and services do not work. Update Available always comes from this endpoint, so set it next to the API token if you want that sensor. The Fenrus token is sent as a plain header, so use HTTPS if the connection leaves your network.

FileFlows 26.10 removed username/password login for the API, so the integration no longer asks for it.

### Options and later changes

- **Configure**: update interval, 10 to 3600 seconds (default 30).
- **Reconfigure**: change host, port, SSL settings or tokens, for example after the server moved. The entry title and device name follow the new host; entity ids stay the same. Moving onto a server that already has an entry is refused.
- **Re-authenticate**: Home Assistant asks for new tokens when FileFlows rejects the stored ones.

## Entities

All entities belong to one device named `FileFlows (<host>)`. Entity ids are built from that device name plus the entity name, so for host `nas` the queue sensor is `sensor.fileflows_nas_queue_size`. With an IP as host the dots become underscores (`sensor.fileflows_192_0_2_10_queue_size`). The examples below and in `examples/` use `nas`; replace it with your own. Entities you already had keep their ids.

Sensors show unavailable, not 0, when the server cannot be reached or does not provide the value.

Token column: **F** works with the Fenrus token alone, **A** needs the API token.

### Sensors

| Entity id | Token | Notes |
|-----------|-------|-------|
| `sensor.fileflows_nas_queue_size` | F | Queue length reported by the server; with only the Fenrus token the unprocessed count |
| `sensor.fileflows_nas_unprocessed_files` | F | |
| `sensor.fileflows_nas_processing_files` | F | Attribute `files` with file, library, step, progress (API token) |
| `sensor.fileflows_nas_processed_files` | F | |
| `sensor.fileflows_nas_failed_files` | F | |
| `sensor.fileflows_nas_files_on_hold` | F | |
| `sensor.fileflows_nas_files_out_of_schedule` | F | |
| `sensor.fileflows_nas_storage_saved` | F | GB, attribute `by_library` |
| `sensor.fileflows_nas_storage_saved_percentage` | F | Saved vs. original size |
| `sensor.fileflows_nas_current_file` | A | `Idle` when nothing runs; attributes `workers_count`, `progress`, `step`, `processing_time`, `details` (file, library, step, progress per running file) |
| `sensor.fileflows_nas_active_workers` | A | Attributes `total_runners`, `workers` (uid, file, agent per running file) |
| `sensor.fileflows_nas_processing_time` | A | |
| `sensor.fileflows_nas_processing_nodes` | A | |
| `sensor.fileflows_nas_libraries` | A | |
| `sensor.fileflows_nas_flows` | A | |
| `sensor.fileflows_nas_plugins` | A | |
| `sensor.fileflows_nas_scheduled_tasks` | A | |
| `sensor.fileflows_nas_version` | A | |
| `sensor.fileflows_nas_upcoming_files` | A | Attribute `files` (next files in queue) |
| `sensor.fileflows_nas_recently_finished` | A | Attribute `files` |

If FileFlows reports an NVIDIA GPU at startup, these are added too (API token): `nvidia_gpu_usage`, `nvidia_memory_usage`, `nvidia_encoder_usage`, `nvidia_decoder_usage`, `nvidia_temperature`.

### Binary sensors

| Entity id | Token | On when |
|-----------|-------|---------|
| `binary_sensor.fileflows_nas_system_paused` | A | Processing is paused |
| `binary_sensor.fileflows_nas_processing_active` | F | A file is being processed |
| `binary_sensor.fileflows_nas_has_failed_files` | F | Failed files > 0 |
| `binary_sensor.fileflows_nas_has_files_on_hold` | F | Files on hold > 0 |
| `binary_sensor.fileflows_nas_queue_not_empty` | F | Queue > 0 |
| `binary_sensor.fileflows_nas_update_available` | F | FileFlows update available (Fenrus token required) |
| `binary_sensor.fileflows_nas_all_nodes_enabled` | A | Every node is enabled |
| `binary_sensor.fileflows_nas_nvidia_available` | A | NVIDIA GPU found |
| `binary_sensor.fileflows_nas_node_<name>_enabled` | A | One per node |
| `binary_sensor.fileflows_nas_library_<name>_enabled` | A | One per library |

### Switches (API token)

| Entity id | Does |
|-----------|------|
| `switch.fileflows_nas_system_active` | On = running, off = paused |
| `switch.fileflows_nas_node_<name>` | Enable/disable a node |
| `switch.fileflows_nas_library_<name>` | Enable/disable a library |
| `switch.fileflows_nas_flow_<name>` | Enable/disable a flow |

### Buttons (API token, except Refresh Data)

| Entity id | Does |
|-----------|------|
| `button.fileflows_nas_pause_system` | Pause until resumed |
| `button.fileflows_nas_resume_system` | Resume |
| `button.fileflows_nas_restart_server` | Restart FileFlows. Disabled by default, listed under Configuration on the device page |
| `button.fileflows_nas_rescan_all_libraries` | Rescan all enabled libraries |
| `button.fileflows_nas_refresh_data` | Poll now |
| `button.fileflows_nas_rescan_<library>` | Rescan one library |
| `button.fileflows_nas_run_task_<task>` | Run one scheduled task |

Node, library, flow and task entities are added when FileFlows reports them, also later at runtime.

## Services

All services need the API token. Every service takes an optional `config_entry_id`; you only need it when more than one FileFlows server is set up. Node, library, flow and task UIDs are in the `uid` attribute of their switch, button or binary sensor. File UIDs are the `uid` of each entry in the `files` attribute of the upcoming and recently finished sensors, or in the `workers` attribute of the active workers sensor. `abort_worker` takes the file UID of a running file from that `workers` attribute as `worker_uid`.

| Service | Fields |
|---------|--------|
| `fileflows.pause_system` | `minutes` (optional, 1 to 525600; leave it out to pause until resumed) |
| `fileflows.resume_system` | |
| `fileflows.restart_system` | |
| `fileflows.enable_node` / `fileflows.disable_node` | `node_uid` |
| `fileflows.enable_library` / `fileflows.disable_library` | `library_uid` |
| `fileflows.rescan_library` | `library_uid` |
| `fileflows.rescan_all_libraries` | |
| `fileflows.enable_flow` / `fileflows.disable_flow` | `flow_uid` |
| `fileflows.reprocess_file` | `file_uid` |
| `fileflows.force_processing` | `file_uid` (one or a list) |
| `fileflows.unhold_files` | `file_uid` (one or a list) |
| `fileflows.abort_worker` | `worker_uid` (file UID from the `workers` attribute) |
| `fileflows.run_task` | `task_uid` |

## Examples

Pause for two hours while Plex is playing, resume when it stops:

```yaml
automation:
  - alias: "Pause FileFlows during Plex"
    trigger:
      - platform: state
        entity_id: media_player.plex
        to: "playing"
    action:
      - service: fileflows.pause_system
        data:
          minutes: 120

  - alias: "Resume FileFlows after Plex"
    trigger:
      - platform: state
        entity_id: media_player.plex
        from: "playing"
        for:
          minutes: 5
    condition:
      - condition: state
        entity_id: binary_sensor.fileflows_nas_system_paused
        state: "on"
    action:
      - service: fileflows.resume_system
```

Simple card:

```yaml
type: entities
title: FileFlows
entities:
  - binary_sensor.fileflows_nas_processing_active
  - sensor.fileflows_nas_queue_size
  - sensor.fileflows_nas_current_file
  - sensor.fileflows_nas_storage_saved
  - switch.fileflows_nas_system_active
```

More in [examples/automations.yaml](examples/automations.yaml) and [examples/lovelace_dashboard.yaml](examples/lovelace_dashboard.yaml).

## Upgrading from 2.x

- After the update the entry asks you to re-authenticate. Username and password are dropped; enter an API token, a Fenrus token or both.
- The API token needs FileFlows 26.10 or newer.
- Entity ids stay the same.
- `binary_sensor.<...>_system_paused` is now **on when the system is paused**. It was inverted before, so check automations that use it.
- Services take an optional `config_entry_id`, and `pause_system` takes optional `minutes`.
- The update interval in the options is now actually used.
- Sensors show unavailable instead of 0 when there is no value.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md). Version history is in [CHANGELOG.md](CHANGELOG.md).

Issues: https://github.com/RiDDiX/ha-fileflows/issues

## License

MIT, see [LICENSE](LICENSE).
