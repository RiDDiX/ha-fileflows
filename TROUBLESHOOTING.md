# FileFlows Integration - Troubleshooting Guide

## Fehler: "cannot_connect"

### Symptom
Bei der Konfiguration der Integration erscheint der Fehler: `cannot_connect`

### Mögliche Ursachen & Lösungen

#### 1. FileFlows Server ist nicht erreichbar

**Prüfen:**
```bash
# Test 1: Ping zum Server
ping YOUR_FILEFLOWS_IP

# Test 2: Port-Check
curl http://YOUR_FILEFLOWS_IP:YOUR_PORT/remote/info/version

# Test 3: Status-Endpoint
curl http://YOUR_FILEFLOWS_IP:YOUR_PORT/remote/info/status
```

**Lösung:**
- Stellen Sie sicher, dass FileFlows läuft
- Prüfen Sie Firewall-Regeln
- Verif icieren Sie IP-Adresse und Port

#### 2. Falscher Port konfiguriert

**Standard-Ports:**
- Häufigster Port: `8585`
- Alternativer Port: `19200`

**Prüfen:**
```bash
# In FileFlows Web UI nachsehen unter Settings → General
# Oder in der FileFlows Konfigurationsdatei
```

**Lösung:**
- Verwenden Sie den korrekten Port in der Home Assistant Konfiguration

#### 3. SSL/HTTPS Fehlkonfiguration

**Symptom:** FileFlows läuft auf HTTP, aber SSL ist auf `true` gesetzt

**Lösung:**
```yaml
# Für HTTP (Standard):
SSL: false
Verify SSL: true  # Kann auf false, hat keine Auswirkung bei HTTP

# Für HTTPS:
SSL: true
Verify SSL: true  # Nur auf false setzen bei selbst-signierten Zertifikaten
```

#### 4. Username/Password sind leer oder enthalten Leerzeichen

**Problem:** Home Assistant trimmt manchmal Leerzeichen nicht korrekt

**Lösung:**
1. Öffnen Sie Home Assistant → Einstellungen → Geräte & Dienste → FileFlows
2. Löschen Sie die Integration komplett
3. Fügen Sie sie neu hinzu
4. Geben Sie Username/Password **ohne** führende/trailing Leerzeichen ein

## Fehler: "invalid_auth"

### Symptom
Verbindung funktioniert, aber Authentifizierung schlägt fehl

### Lösungen

#### 1. Falsche Credentials

**Testen Sie den Login manuell:**
```bash
# Holen Sie einen Bearer Token
TOKEN=$(curl -sS \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}' \
  "http://YOUR_FILEFLOWS_IP:YOUR_PORT/authorize")

echo "Token: $TOKEN"

# Wenn Sie einen Token erhalten (langer String), sind die Credentials korrekt
# Bei Fehler 401: Credentials sind falsch
```

**Lösung:**
- Loggen Sie sich in die FileFlows Web UI ein
- Verwenden Sie **exakt** dieselben Credentials
- Achten Sie auf Groß-/Kleinschreibung

#### 2. FileFlows Security ist deaktiviert

**Symptom:** FileFlows benötigt keine Anmeldung in der Web UI

**Lösung:**
- Lassen Sie Username/Password in Home Assistant **leer**
- Die Integration funktioniert dann nur mit öffentlichen Endpoints
- Für vollständige Funktionalität: Aktivieren Sie Security in FileFlows

## Debug-Modus aktivieren

Um detaillierte Fehler zu sehen, fügen Sie zu `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.fileflows: debug
    custom_components.fileflows.api: debug
    custom_components.fileflows.config_flow: debug
    custom_components.fileflows.coordinator: debug
```

Dann:
1. Home Assistant neu starten
2. Integration erneut hinzufügen
3. Logs prüfen: **Einstellungen** → **System** → **Protokolle**

## Test-Scripts verwenden

### 1. Login-Test

```bash
cd /Users/maximilianhammerschmid/ha-fileflows

# Script bearbeiten
nano test_login.py
# Setzen Sie: API_BASE, USERNAME, PASSWORD

# Ausführen
python3 test_login.py
```

**Was der Test zeigt:**
- ✅ Login erfolgreich → Credentials sind korrekt
- ❌ 401 Error → Falsche Credentials
- ❌ Connection Error → FileFlows nicht erreichbar

### 2. Vollständiger Diagnose-Test

```bash
# Script bearbeiten
nano test_fileflows_diagnostics.py
# Setzen Sie: API_BASE

# Ausführen
python3 test_fileflows_diagnostics.py
```

**Was der Test zeigt:**
- Welche Endpoints funktionieren
- Ob Authentifizierung benötigt wird
- Welche Daten verfügbar sind

## Häufige Konfigurationsfehler

### ❌ Falsch: Port als String
```yaml
Port: "8585"  # FALSCH!
```

### ✅ Richtig: Port als Zahl
```yaml
Port: 8585  # RICHTIG
```

### ❌ Falsch: IP mit Protokoll
```yaml
Host: "http://192.168.1.100"  # FALSCH!
```

### ✅ Richtig: Nur IP/Hostname
```yaml
Host: "192.168.1.100"  # RICHTIG
```

### ❌ Falsch: Leerzeichen in Credentials
```yaml
Username: " admin "  # FALSCH! (Leerzeichen)
Password: "  pass  "  # FALSCH! (Leerzeichen)
```

### ✅ Richtig: Keine Leerzeichen
```yaml
Username: "admin"  # RICHTIG
Password: "pass"  # RICHTIG
```

## Netzwerk-Troubleshooting

### FileFlows läuft in Docker

**Problem:** Home Assistant kann FileFlows nicht erreichen

**Lösung:**
```bash
# Prüfen Sie das Docker-Netzwerk
docker network ls
docker inspect <fileflows_container_name>

# Verwenden Sie die interne Docker-IP ODER
# Verbinden Sie beide Container im selben Netzwerk
```

**Für Home Assistant Container:**
```yaml
# docker-compose.yml
services:
  homeassistant:
    networks:
      - fileflows_network

  fileflows:
    networks:
      - fileflows_network

networks:
  fileflows_network:
```

### FileFlows hinter Reverse Proxy

**Problem:** Reverse Proxy blockiert `/api/*` Endpoints

**Lösung - Nginx Beispiel:**
```nginx
location /api/ {
    proxy_pass http://fileflows:8585;
    proxy_set_header Authorization $http_authorization;
    proxy_pass_header Authorization;
}

location /authorize {
    proxy_pass http://fileflows:8585;
    proxy_set_header Content-Type application/json;
}
```

## Sensor-Werte sind alle 0 oder "unknown"

### Symptom
Integration ist verbunden, aber alle Sensoren zeigen keine Daten

### Ursache
Nur öffentliche Endpoints funktionieren, authentifizierte Endpoints schlagen fehl

### Lösung

**Option 1: Credentials konfigurieren**
1. Fügen Sie Username/Password in der Integration hinzu
2. Integration neu laden

**Option 2: Öffentliche Endpoints reichen aus**
Folgende Sensoren funktionieren ohne Auth:
- Version
- Queue Size
- Processing Files
- Processed Files
- Storage Saved

Diese benötigen Authentifizierung:
- CPU/Memory Usage
- Nodes, Libraries, Flows, Plugins
- Detailed File Status
- Tasks

## Logs analysieren

### Wichtige Log-Meldungen

#### ✅ Erfolgreiche Verbindung
```
INFO: Testing basic connection...
DEBUG: Basic connection successful
INFO: Bearer token acquired successfully
INFO: Bearer token authentication successful (token length: 256)
```

#### ❌ Verbindungsfehler
```
ERROR: Connection error: Cannot connect to host
```
→ FileFlows nicht erreichbar, IP/Port prüfen

#### ❌ Authentifizierungsfehler
```
ERROR: Login failed: HTTP 401
ERROR: Bearer authentication failed: Login failed - invalid username or password
```
→ Falsche Credentials, in FileFlows Web UI testen

#### ❌ Token-Problem
```
ERROR: Failed to obtain Bearer token - no token returned
```
→ FileFlows /authorize Endpoint hat keinen Token zurückgegeben

## Support

Wenn Sie weiterhin Probleme haben:

1. **Logs sammeln:**
   - Debug-Modus aktivieren (siehe oben)
   - Integration neu hinzufügen
   - Relevante Log-Zeilen kopieren

2. **Test-Results sammeln:**
   ```bash
   python3 test_login.py > login_test.txt 2>&1
   python3 test_fileflows_diagnostics.py > diagnostics.txt 2>&1
   ```

3. **Issue erstellen:**
   - GitHub: https://github.com/RiDDiX/ha-fileflows/issues
   - Fügen Sie hinzu:
     - Home Assistant Version
     - FileFlows Version
     - Log-Auszüge (ohne Credentials!)
     - Test-Results

## Schnell-Check

Führen Sie diese Befehle aus:

```bash
# 1. Basis-Verbindung (sollte funktionieren)
curl http://YOUR_IP:YOUR_PORT/remote/info/version

# 2. Auth-Test (sollte 401 zurückgeben ohne Credentials)
curl http://YOUR_IP:YOUR_PORT/api/status

# 3. Login-Test
curl -X POST http://YOUR_IP:YOUR_PORT/authorize \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'

# 4. Token-Test (mit Token aus Schritt 3)
curl http://YOUR_IP:YOUR_PORT/api/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Erwartetes Ergebnis:**
1. ✅ Version-String (z.B. "25.12.9.6135")
2. ❌ 401 Unauthorized (wenn Auth aktiviert)
3. ✅ Langer Token-String
4. ✅ JSON mit Status-Daten
