# FileFlows Home Assistant Integration - API Endpoints Übersicht

## Implementierte Endpoints (2026-01-05)

Diese Dokumentation zeigt alle API-Endpoints, die in der FileFlows Home Assistant Integration implementiert und aktiv genutzt werden.

---

## 🔐 Authentifizierung

### Bearer Token Authentication
- **Endpoint**: `POST /authorize`
- **Verwendung**: Erhält Bearer Token für authentifizierte API-Aufrufe
- **Payload**: `{"username": "...", "password": "..."}`
- **Response**: Token-String (JWT)
- **Caching**: Token wird 23 Stunden gecacht
- **Auto-Refresh**: Bei 401-Fehler wird Token automatisch erneuert

---

## 📊 Status & Monitoring Endpoints

### 1. System Status ✅
- **Endpoint**: `/api/status`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Primäre Quelle für Queue/Processing-Daten
- **Response**:
  ```json
  {
    "queue": 1685,
    "processing": 2,
    "processed": 425,
    "time": "00:15:42",
    "processingFiles": [...]
  }
  ```
- **Fallback**: `/remote/info/status` (wenn keine Auth)
- **Sensors**: `queue_size`, `files_processing`, `files_processed`, `processing_time`

### 2. Library File Status ✅
- **Endpoint**: `/api/library-file/status`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Detaillierte Datei-Status-Übersicht
- **Response**:
  ```json
  {
    "Unprocessed": 1685,
    "Processing": 2,
    "Processed": 425,
    "Failed": 3,
    "OnHold": 0,
    "OutOfSchedule": 0,
    "Disabled": 0
  }
  ```
- **Sensors**: `files_unprocessed`, `files_failed`, `files_on_hold`, `files_out_of_schedule`

### 3. FileFlows Status ✅
- **Endpoint**: `/api/settings/fileflows-status`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: System-Pause-Status
- **Response**: `{"IsPaused": false, ...}`
- **Sensors**: `is_paused` (binary_sensor)

---

## 💾 Storage & Statistics Endpoints

### 4. Storage Saved Statistics ✅ **NEU**
- **Endpoint**: `/api/statistics/storage-saved`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Detaillierte Storage-Einsparungen pro Library
- **Response**:
  ```json
  {
    "series": [
      {"name": "Final Size", "data": [4387058326945, 396159065, 4387454486010]},
      {"name": "Savings", "data": [1439824444369, 3000244, 1439827444613]},
      {"name": "Increase", "data": [0, 0, 0]}
    ],
    "labels": ["Filme", "Bücher", "Total"],
    "items": [1950, 169, 2119]
  }
  ```
- **Sensors**: `storage_saved` (mit by_library attributes)
- **Features**:
  - Total savings in GB: 1.44 TB
  - Per-library breakdown
  - Items count pro Library
  - Savings percentage berechnung

### 5. Shrinkage Groups (Legacy) ✅
- **Endpoint**: `/remote/info/shrinkage-groups`
- **Auth**: Nicht erforderlich (Public)
- **Verwendung**: Fallback für Storage-Daten
- **Response**: Array von Library-Shrinkage-Objekten
- **Status**: Als Fallback beibehalten für Kompatibilität

---

## 🖥️ System Information Endpoints

### 6. System Info ⚠️
- **Endpoint**: `/api/system/info`
- **Auth**: Bearer Token erforderlich
- **Status**: **Endpoint existiert nicht auf User-Server (404)**
- **Verwendung**: CPU/Memory-Daten
- **Sensors**: `cpu_usage`, `memory_usage` (zeigen 0 wenn nicht verfügbar)
- **Hinweis**: Endpoint scheint in neueren FileFlows-Versionen entfernt worden zu sein

### 7. System Version ✅
- **Endpoint**: `/api/system/version`
- **Auth**: Bearer Token erforderlich
- **Fallback**: `/remote/info/version`
- **Verwendung**: FileFlows-Versionsnummer
- **Sensors**: `version`

### 8. Update Available ✅
- **Endpoint**: `/remote/info/update-available`
- **Auth**: Nicht erforderlich
- **Verwendung**: Prüft auf Updates
- **Sensors**: `update_available` (attribute)

---

## 🔧 Processing Nodes Endpoints

### 9. Processing Nodes ✅
- **Endpoint**: `/api/node`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Liste aller Processing Nodes
- **Response**: Array von Node-Objekten
  ```json
  [{
    "Uid": "...",
    "Name": "Internal Processing Node",
    "Enabled": true,
    "FlowRunners": 2,
    "Address": "INTERNAL"
  }]
  ```
- **Sensors**: `nodes_count`, `enabled_nodes_count`, `total_runners`

---

## 📚 Library Endpoints

### 10. Libraries ✅
- **Endpoint**: `/api/library`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Liste aller Libraries
- **Response**: Array von Library-Objekten
- **Sensors**: `libraries_count`, `enabled_libraries_count`

### 11. Upcoming Files ✅
- **Endpoint**: `/api/library-file/upcoming`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Nächste zu verarbeitende Dateien
- **Sensors**: `upcoming_count` (mit Details in attributes)

### 12. Recently Finished ✅
- **Endpoint**: `/api/library-file/recently-finished`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Kürzlich abgeschlossene Dateien
- **Sensors**: `recently_finished_count`

---

## 🔄 Flow Endpoints

### 13. Flows ✅
- **Endpoint**: `/api/flow`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Liste aller Flows
- **Response**: Array von Flow-Objekten
- **Sensors**: `flows_count`, `enabled_flows_count`

---

## 👷 Worker Endpoints

### 14. Workers ⚠️
- **Endpoint**: `/api/worker`
- **Auth**: Bearer Token erforderlich
- **Status**: **Endpoint existiert nicht auf User-Server (404)**
- **Verwendung**: Aktive Worker/Executors
- **Fallback**: Verwendet `processingFiles` aus `/api/status`
- **Sensors**: `active_workers`, `current_file`, `current_file_progress`

---

## 🔌 Plugin Endpoints

### 15. Plugins ✅
- **Endpoint**: `/api/plugin`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Liste aller Plugins
- **Response**: Array von Plugin-Objekten
- **Sensors**: `plugins_count`, `enabled_plugins_count`

---

## ⏰ Task Endpoints

### 16. Tasks ✅
- **Endpoint**: `/api/task`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: Liste aller Scheduled Tasks
- **Response**: Array von Task-Objekten
- **Sensors**: `tasks_count`

---

## 🎮 NVIDIA GPU Endpoints

### 17. NVIDIA SMI ✅
- **Endpoint**: `/api/nvidia/smi`
- **Auth**: Bearer Token erforderlich
- **Verwendung**: NVIDIA GPU-Statistiken
- **Response**:
  ```json
  {
    "GpuUsage": 15.2,
    "MemoryUsage": 42.3,
    "EncoderUsage": 0.0,
    "DecoderUsage": 85.1,
    "Temperature": 67.0
  }
  ```
- **Sensors**: `nvidia_gpu_usage`, `nvidia_memory_usage`, `nvidia_encoder_usage`, `nvidia_decoder_usage`, `nvidia_temperature`
- **Hinweis**: Sensors werden nur erstellt wenn NVIDIA GPU vorhanden

---

## 📋 Endpoint-Status Zusammenfassung

### ✅ Funktionierend (17 Endpoints)
- `/authorize` - Bearer Token Authentication
- `/api/status` - System Status
- `/api/statistics/storage-saved` - Storage Statistics **NEU**
- `/api/library-file/status` - File Status Overview
- `/api/settings/fileflows-status` - System Pause Status
- `/api/system/version` - Version Info
- `/remote/info/update-available` - Update Check
- `/remote/info/shrinkage-groups` - Legacy Storage Data
- `/api/node` - Processing Nodes
- `/api/library` - Libraries
- `/api/library-file/upcoming` - Upcoming Files
- `/api/library-file/recently-finished` - Recently Finished
- `/api/flow` - Flows
- `/api/plugin` - Plugins
- `/api/task` - Tasks
- `/api/nvidia/smi` - NVIDIA GPU Stats
- `/remote/info/version` - Version (Fallback)

### ⚠️ Nicht verfügbar auf User-Server
- `/api/system/info` - 404 (CPU/Memory-Daten)
- `/api/worker` - 404 (Worker-Details)
- `/remote/info/status` - 404 (nur /api/status verfügbar)

### 🔧 Service Endpoints (definiert aber nicht in get_all_data)
Diese sind für HA Services verfügbar, werden aber nicht beim Polling abgerufen:
- `/api/system/pause` - Pause System
- `/api/system/restart` - Restart System
- `/api/library/rescan` - Rescan Libraries
- `/api/library-file/reprocess` - Reprocess Files
- `/api/library-file/unhold` - Unhold Files

---

## 🔄 Fallback-Logik

Die Integration verwendet eine intelligente Fallback-Strategie:

1. **Status-Daten**:
   - Primär: `/api/status` (wenn Auth verfügbar)
   - Fallback: `/remote/info/status` (Public, aber gibt 404 auf User-Server)

2. **Storage-Daten**:
   - Primär: `/api/statistics/storage-saved` (präzise, mit Items-Count)
   - Fallback: `/remote/info/shrinkage-groups` (Legacy-Kompatibilität)

3. **Version-Daten**:
   - Primär: `/api/system/version` (wenn Auth verfügbar)
   - Fallback: `/remote/info/version` (Public)

4. **Worker-Daten**:
   - Primär: `/api/worker` (gibt 404)
   - Fallback: `processingFiles` aus `/api/status` ✅

5. **System Info**:
   - `/api/system/info` gibt 404 → Sensors zeigen 0
   - Akzeptabel, da nicht kritisch für Kernfunktionalität

---

## 🎯 Integration Quality

### Stärken ✅
- **Bearer Token Auth**: Vollständig implementiert mit Caching und Auto-Refresh
- **Comprehensive Coverage**: Alle wichtigen Daten werden abgerufen
- **Smart Fallbacks**: Robuste Fehlerbehandlung mit alternativen Endpunkten
- **Modern API**: Nutzt `/api/status` und `/api/statistics/storage-saved`
- **Error Resilience**: Fehlende Endpoints führen nicht zu Crashes

### Optimierungen umgesetzt 🔧
- ✅ Verwendung von `/api/status` statt `/remote/info/status`
- ✅ Bearer Token für ALLE API-Aufrufe wenn Credentials vorhanden
- ✅ Storage Statistics mit präzisen Library-Daten
- ✅ Fixes für "unknown" Werte (>= 0 statt > 0)
- ✅ Coordinator Properties mit Fallback-Logik

---

## 📊 Sensor Coverage

Die Integration erstellt **28 Haupt-Sensoren** + **5 NVIDIA-Sensoren** (falls GPU vorhanden):

### Status Sensors (8)
- Queue Size, Unprocessed, Processing, Processed
- Failed, On Hold, Out of Schedule
- Current File

### Resource Sensors (4)
- CPU Usage, Memory Usage
- Temp Directory Size, Log Directory Size

### Storage Sensors (2)
- Storage Saved (GB)
- Storage Saved Percentage

### Count Sensors (7)
- Nodes, Libraries, Flows
- Plugins, Tasks
- Upcoming Files, Recently Finished

### Processing Sensors (3)
- Active Workers
- Processing Time
- Version

### Activity Sensors (4)
- Upcoming Count
- Recently Finished Count
- (Details in attributes)

### NVIDIA Sensors (5) - optional
- GPU Usage, Memory Usage
- Encoder Usage, Decoder Usage
- Temperature

---

## 🚀 Nächste Schritte für Testing

1. **Home Assistant Neustart**: Integration mit neuen Storage-Daten testen
2. **Sensor-Werte prüfen**: Sicherstellen dass keine "unknown" Werte mehr erscheinen
3. **Storage-Attributes**: Überprüfen dass `by_library` mit Items-Count angezeigt wird
4. **Performance**: Polling-Verhalten bei allen Endpoints beobachten

---

## 📝 Changelog

### 2026-01-05
- ✅ `/api/statistics/storage-saved` implementiert
- ✅ Coordinator Properties für Storage Stats hinzugefügt
- ✅ Storage Sensor Attributes mit Items-Count erweitert
- ✅ Fallback-Logik für alle Storage-Berechnungen
- ✅ Fixes für >= 0 Checks in allen Properties
- ✅ Comprehensive API Dokumentation erstellt
