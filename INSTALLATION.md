# FileFlows Home Assistant Integration - Installation Guide

## 📦 Was ist in diesem Ordner?

Dieser Ordner enthält die **fertige FileFlows Home Assistant Integration** mit Bearer-Token-Authentifizierung.

---

## 📂 Dateistruktur

```
FINAL_PLUGIN/
├── custom_components/
│   └── fileflows/           # ← DAS Plugin
│       ├── __init__.py
│       ├── api.py           # API Client mit Bearer-Auth
│       ├── binary_sensor.py
│       ├── button.py
│       ├── config_flow.py   # Setup mit Username/Password
│       ├── const.py
│       ├── coordinator.py
│       ├── manifest.json
│       ├── sensor.py
│       ├── strings.json
│       └── switch.py
├── README.md                # Vollständige Dokumentation
├── LICENSE
├── hacs.json               # HACS Konfiguration
├── INFO
└── BEARER_AUTH_IMPLEMENTATION.md  # Technische Details
```

---

## 🚀 Installation

### Methode 1: Manuell (Empfohlen zum Testen)

1. **Kopiere den `custom_components` Ordner** nach Home Assistant:
   ```bash
   # Auf deinem Home Assistant Server:
   cd /config
   cp -r /pfad/zu/FINAL_PLUGIN/custom_components/fileflows custom_components/
   ```

2. **Starte Home Assistant neu**

3. **Füge die Integration hinzu:**
   - Gehe zu **Settings → Devices & Services**
   - Klicke auf **+ Add Integration**
   - Suche nach **"FileFlows"**
   - Gib deine Daten ein:
     ```
     Host: 192.168.178.8
     Port: 8585
     SSL: false
     Verify SSL: true
     Username: riddix        # Optional aber empfohlen!
     Password: dein_passwort # Optional aber empfohlen!
     ```

### Methode 2: HACS (Für GitHub Release)

1. **Lade das Plugin auf GitHub hoch**

2. **In HACS:**
   - Klicke auf HACS → Integrations
   - Menü (⋮) → Custom repositories
   - Füge deine GitHub URL hinzu
   - Category: Integration
   - Suche nach "FileFlows"
   - Installiere es

---

## ⚙️ Konfiguration

### Mit Authentifizierung (Empfohlen) ✅

Wenn du **Username und Password** angibst, erhältst du:

✅ **Vollständige Daten:**
- CPU Usage
- Memory Usage
- Processing Nodes (1 bei dir)
- Libraries (3 bei dir)
- Flows (36 bei dir!)
- Plugins (12 bei dir!)
- Tasks
- Failed Files
- On Hold Files
- NVIDIA GPU Stats (falls vorhanden)

**Konfiguration:**
```yaml
Host: 192.168.178.8
Port: 8585
Username: riddix
Password: dein_passwort
```

### Ohne Authentifizierung (Fallback) ⚠️

Wenn du **Username/Password LEER lässt**, erhältst du:

✅ **Basis-Monitoring:**
- Queue Size
- Processing Status
- Storage Saved

❌ **Keine erweiterten Daten**

---

## 🔧 Verfügbare Entitäten

Nach der Installation findest du folgende Entitäten:

### Sensoren (mit Auth):
- `sensor.fileflows_queue_size` - Warteschlange
- `sensor.fileflows_processing_files` - Aktiv verarbeitende Dateien
- `sensor.fileflows_current_file` - Aktuell verarbeitete Datei
- `sensor.fileflows_storage_saved` - Gesparte Speicher (GB)
- `sensor.fileflows_cpu_usage` - CPU Auslastung ✨ NEU!
- `sensor.fileflows_memory_usage` - RAM Auslastung ✨ NEU!
- `sensor.fileflows_nodes_count` - Anzahl Nodes ✨ NEU!
- `sensor.fileflows_libraries_count` - Anzahl Libraries ✨ NEU!
- `sensor.fileflows_flows_count` - Anzahl Flows ✨ NEU!
- `sensor.fileflows_plugins_count` - Anzahl Plugins ✨ NEU!
- ... und viele mehr!

### Binary Sensoren:
- `binary_sensor.fileflows_processing_active` - Verarbeitung aktiv?
- `binary_sensor.fileflows_queue_not_empty` - Warteschlange nicht leer?
- `binary_sensor.fileflows_system_paused` - System pausiert?
- `binary_sensor.fileflows_update_available` - Update verfügbar?

### Buttons:
- `button.fileflows_pause_system` - System pausieren
- `button.fileflows_resume_system` - System fortsetzen
- `button.fileflows_restart_server` - Server neustarten
- `button.fileflows_rescan_all_libraries` - Libraries neu scannen

### Switch:
- `switch.fileflows_system_active` - System An/Aus

---

## 🧪 Testing

Nach der Installation:

1. **Prüfe die Logs:**
   ```
   Settings → System → Logs
   Suche nach "fileflows"
   ```

2. **Erwartete Log-Einträge:**
   ```
   INFO FileFlows API initialized: http://192.168.178.8:8585 (mode: authenticated)
   INFO Bearer token acquired successfully
   INFO Connection test successful (authenticated)
   ```

3. **Prüfe die Sensoren:**
   - Gehe zu Developer Tools → States
   - Suche nach "fileflows"
   - Prüfe ob Werte angezeigt werden

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to FileFlows"

**Lösung:**
1. Prüfe ob FileFlows erreichbar ist: `curl http://192.168.178.8:8585`
2. Prüfe IP und Port in der Konfiguration
3. Prüfe Firewall-Einstellungen

### Problem: "Authentication failed (401)"

**Lösung:**
1. Prüfe Username und Password
2. Teste Login manuell:
   ```bash
   curl -X POST http://192.168.178.8:8585/authorize \
     -H "Content-Type: application/json" \
     -d '{"username":"riddix","password":"dein_passwort"}'
   ```
3. Sollte einen Token zurückgeben

### Problem: "Sensoren zeigen 0"

**Mögliche Ursachen:**
- Keine Authentifizierung konfiguriert → Nur Basis-Daten verfügbar
- Token abgelaufen → Automatischer Refresh sollte funktionieren
- FileFlows API nicht erreichbar

**Lösung:**
1. Füge Username/Password hinzu für vollständige Daten
2. Prüfe Logs für Auth-Errors
3. Starte Integration neu

---

## 📊 Features

### ✅ Implementiert:
- Bearer-Token-Authentifizierung
- Automatischer Token-Refresh
- Intelligente Fallback-Logik
- 40+ Sensoren
- 5 Binary Sensoren
- 4 Buttons
- 1 Switch
- Vollständige HACS-Integration
- Unterstützung für mehrere FileFlows-Instanzen

### 🎯 Geplant:
- Services für erweiterte Kontrolle
- Node Management
- Library Management
- Flow Management

---

## 📝 Für Entwickler

### API-Client (`api.py`)
- Bearer-Token Login via `/authorize`
- Automatisches Token-Caching (24h)
- Smart Fallback zwischen `/api/*` und `/remote/info/*`

### Coordinator (`coordinator.py`)
- Zentrale Datenverwaltung
- 30s Update-Intervall (konfigurierbar)
- Fehlertolerante Datenabfrage

### Config Flow (`config_flow.py`)
- Benutzerfreundliches Setup
- Optionale Authentifizierung
- Verbindungstest beim Setup

---

## 🤝 Support

Bei Problemen oder Fragen:
1. Prüfe die Logs
2. Schaue in `BEARER_AUTH_IMPLEMENTATION.md` für technische Details
3. Öffne ein Issue auf GitHub

---

## 📄 Lizenz

Siehe `LICENSE` Datei

---

**Viel Erfolg mit der FileFlows Integration!** 🚀
