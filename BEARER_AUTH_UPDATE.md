# FileFlows Integration - Bearer Token Authentication Update

## Änderungen

Die FileFlows Integration wurde komplett überarbeitet, um die **Bearer Token Authentifizierung** zu unterstützen.

### Was wurde geändert?

1. **Neue Authentifizierung**: Die Integration verwendet jetzt Username/Password statt statischem Access Token
2. **Automatisches Token-Management**: Bearer Tokens werden automatisch über `/authorize` geholt und gecached
3. **Intelligentes Fallback**: Öffentliche `/remote/*` Endpoints funktionieren ohne Authentifizierung
4. **Token-Refresh**: Abgelaufene Tokens werden automatisch erneuert

### Vorher vs. Nachher

#### Vorher (Alt - funktioniert NICHT mehr):
```yaml
# Alte Konfiguration mit statischem x-token Header
Host: YOUR_FILEFLOWS_IP
Port: YOUR_PORT
SSL: false
Access Token: "YOUR_TOKEN"  # ❌ Funktioniert nicht für /api/* Endpoints
```

#### Nachher (Neu - funktioniert korrekt):
```yaml
# Neue Konfiguration mit Username/Password
Host: YOUR_FILEFLOWS_IP
Port: YOUR_PORT
SSL: false
Username: your_username  # ✅ Wird für Bearer Token verwendet
Password: your_password  # ✅ Wird für Bearer Token verwendet
```

## So aktualisieren Sie Ihre Integration

### Schritt 1: Integration in Home Assistant neu konfigurieren

1. Öffnen Sie Home Assistant
2. Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
3. Suchen Sie **FileFlows** Integration
4. Klicken Sie auf **KONFIGURIEREN** oder löschen Sie die alte Integration und fügen Sie sie neu hinzu
5. Geben Sie ein:
   - **Host**: Ihre FileFlows IP-Adresse (z.B. 192.168.1.100)
   - **Port**: Ihr Port (Standard: 8585)
   - **SSL**: false (oder true wenn Sie HTTPS verwenden)
   - **Verify SSL**: true
   - **Username**: Ihr FileFlows Benutzername
   - **Password**: Ihr FileFlows Passwort

### Schritt 2: Integration neu starten

1. Starten Sie Home Assistant neu ODER
2. Laden Sie die Integration neu

### Schritt 3: Überprüfen Sie die Sensoren

Nach dem Neustart sollten alle Sensoren korrekte Werte anzeigen:

- ✅ **Queue Size**: Anzahl der Dateien in der Warteschlange
- ✅ **Processing Files**: Anzahl der verarbeiteten Dateien
- ✅ **Active Workers**: Anzahl aktiver Worker
- ✅ **CPU Usage**: CPU-Auslastung
- ✅ **Memory Usage**: Speicherauslastung
- ✅ **Storage Saved**: Eingesparter Speicherplatz
- ✅ **Libraries**: Anzahl Bibliotheken
- ✅ **Flows**: Anzahl Flows
- ✅ **Nodes**: Anzahl Processing Nodes
- ✅ **Plugins**: Anzahl Plugins

## Technische Details

### Authentifizierung Flow

1. **Beim Start**: Integration holt Bearer Token über POST `/authorize` mit Username/Password
2. **Token Caching**: Token wird 23 Stunden gecached (läuft nach 24h ab)
3. **API Calls**: Alle `/api/*` Requests verwenden `Authorization: Bearer <token>` Header
4. **Token Refresh**: Bei 401 Fehler wird Token automatisch erneuert
5. **Öffentliche Endpoints**: `/remote/info/*` Endpoints funktionieren ohne Token

### Welche Daten werden abgerufen?

#### Ohne Authentifizierung (nur `/remote/*`):
- Version
- Queue Status (Warteschlange, Verarbeitung, Verarbeitet)
- Storage Savings (Eingesparter Speicher)
- Update Status

#### Mit Authentifizierung (zusätzlich `/api/*`):
- **System Info**: CPU, Memory, Temp/Log Directory Größe
- **Nodes**: Alle Processing Nodes mit Status
- **Libraries**: Alle Bibliotheken mit Status
- **Flows**: Alle Flows mit Status
- **Workers**: Aktive Worker mit Details
- **Library Files**: Detaillierter Datei-Status
- **Plugins**: Installierte Plugins
- **Tasks**: Geplante Tasks
- **NVIDIA**: GPU Informationen (falls vorhanden)

## Fehlersuche

### Problem: Alle Sensoren zeigen 0 oder "unknown"

**Ursache**: Keine Authentifizierung konfiguriert oder ungültige Credentials

**Lösung**:
1. Überprüfen Sie, ob Username/Password korrekt eingegeben wurden
2. Testen Sie den Login in der FileFlows Web UI
3. Prüfen Sie die Home Assistant Logs: **Einstellungen** → **System** → **Protokolle**

### Problem: "Authentication failed - check credentials"

**Ursache**: Falsche Username/Password Kombination

**Lösung**:
1. Überprüfen Sie Ihre FileFlows Credentials
2. Loggen Sie sich in die FileFlows Web UI ein: `http://YOUR_FILEFLOWS_IP:YOUR_PORT`
3. Wenn Login funktioniert, konfigurieren Sie die Integration mit denselben Credentials neu

### Problem: "Cannot connect to FileFlows"

**Ursache**: FileFlows Server ist nicht erreichbar

**Lösung**:
1. Überprüfen Sie, ob FileFlows läuft
2. Prüfen Sie die IP-Adresse und Port
3. Testen Sie mit: `curl http://YOUR_FILEFLOWS_IP:YOUR_PORT/remote/info/version`

### Debug Logs aktivieren

Fügen Sie zu Ihrer `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.fileflows: debug
    custom_components.fileflows.api: debug
    custom_components.fileflows.coordinator: debug
```

Danach Home Assistant neu starten und Logs prüfen.

## Test Script

Ein Diagnose-Script wurde erstellt: `test_fileflows_diagnostics.py`

```bash
# Script bearbeiten und API_BASE setzen
nano test_fileflows_diagnostics.py

# Script ausführen
python3 test_fileflows_diagnostics.py
```

Das Script testet:
- ✅ Öffentliche Endpoints (ohne Auth)
- ✅ Authentifizierte Endpoints (mit/ohne Token)
- ✅ Bearer Token Login
- ✅ Zeigt welche Daten verfügbar sind

## Beispiel Bearer Token Request

So funktioniert die Authentifizierung unter der Haube:

```bash
# 1. Bearer Token holen
TOKEN=$(curl -sS \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}' \
  "http://YOUR_FILEFLOWS_IP:YOUR_PORT/authorize")

echo "Token: $TOKEN"

# 2. Token verwenden für API Calls
curl -v \
  -H "Authorization: Bearer $TOKEN" \
  "http://YOUR_FILEFLOWS_IP:YOUR_PORT/api/status"

curl -v \
  -H "Authorization: Bearer $TOKEN" \
  "http://YOUR_FILEFLOWS_IP:YOUR_PORT/api/library"

curl -v \
  -H "Authorization: Bearer $TOKEN" \
  "http://YOUR_FILEFLOWS_IP:YOUR_PORT/api/node"
```

## Unterstützung

Bei Problemen:
1. Prüfen Sie die Home Assistant Logs
2. Führen Sie das Diagnose-Script aus
3. Erstellen Sie ein Issue auf GitHub mit den Log-Auszügen

## Wichtiger Hinweis

**Passwort-Sicherheit**: Ihr FileFlows Passwort wird in der Home Assistant Konfiguration gespeichert.
Home Assistant verschlüsselt die Konfiguration, aber Sie sollten trotzdem sichere Passwörter verwenden!

**Token Caching**: Der Bearer Token wird im RAM gecached und nicht auf der Festplatte gespeichert.
Bei Home Assistant Neustart wird ein neuer Token geholt.
