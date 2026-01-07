# FileFlows Home Assistant Integration v2.1.1

## 🐛 Bug Fix Release

This is a quick bug fix release to resolve "Unauthorized" errors in FileFlows server logs and remove non-functional sensors.

---

## 🔧 What's Fixed

### Critical Fix: API Token Errors Resolved

**Problem**: Users with authenticated setups were seeing repeated errors in FileFlows server logs:
```
Unauthorized: Invalid API token 'was not provided'
```

**Root Cause**: The integration was calling `/remote/*` endpoints even when authenticated with username/password. These remote endpoints don't exist on authenticated FileFlows servers, causing the errors.

**Solution**:
- `/remote/info/shrinkage-groups` is now only called when NO authentication is configured
- `/remote/info/update-available` is now only called when NO authentication is configured
- When authenticated, only `/api/*` endpoints are used
- Intelligent fallback logic ensures data is still available

**Impact**: FileFlows server logs will be clean - no more "Unauthorized" errors every 30 seconds!

---

## 🗑️ What's Removed

### Non-Functional Sensors

Removed 4 sensors that relied on the `/api/system/info` endpoint, which doesn't exist on modern FileFlows servers:

- ❌ **CPU Usage** - Always showed 0
- ❌ **Memory Usage** - Always showed 0
- ❌ **Temp Directory Size** - Always showed 0
- ❌ **Log Directory Size** - Always showed 0

**Result**: Cleaner sensor list with only functional sensors.

**New Sensor Count**:
- **24 core sensors** (down from 28)
- **5 NVIDIA sensors** (unchanged - only created if GPU detected)
- **Total working sensors**: 24 + optional 5 NVIDIA = up to 29 sensors

---

## ⚠️ Breaking Changes

### Removed Sensors

If you have automations or dashboards using these sensors, they will need to be updated:

- `sensor.fileflows_*_cpu_usage`
- `sensor.fileflows_*_memory_usage`
- `sensor.fileflows_*_temp_directory_size`
- `sensor.fileflows_*_log_directory_size`

**Recommendation**: Remove these entities from your dashboards and automations after upgrading.

---

## 📊 Remaining Sensors (All Functional)

### Queue & Processing (7 sensors)
- Queue Size
- Unprocessed Files
- Processing Files
- Processed Files
- Failed Files
- Files On Hold
- Files Out of Schedule

### Current Processing (3 sensors)
- Current File
- Active Workers
- Processing Time

### Storage Savings (2 sensors)
- Storage Saved (with per-library breakdown)
- Storage Saved Percentage

### Counts (5 sensors)
- Processing Nodes
- Libraries
- Flows
- Plugins
- Scheduled Tasks

### Version & Updates (1 sensor)
- Version

### Recent Activity (2 sensors)
- Upcoming Files
- Recently Finished

### System Resources (4 sensors - REMOVED)
- ~~CPU Usage~~ ❌
- ~~Memory Usage~~ ❌
- ~~Temp Directory Size~~ ❌
- ~~Log Directory Size~~ ❌

### NVIDIA GPU (5 sensors - optional)
- GPU Usage
- Memory Usage
- Encoder Usage
- Decoder Usage
- Temperature

---

## 🚀 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Find **FileFlows**
4. Click **Update** (or **Redownload** if update doesn't appear)
5. **Restart Home Assistant**
6. (Optional) Reload the FileFlows integration

### Manual Installation

1. Download the [latest release](https://github.com/RiDDiX/fileflows-ha/releases/tag/v2.1.1)
2. Extract and replace `custom_components/fileflows` folder
3. **Restart Home Assistant**
4. (Optional) Reload the FileFlows integration

---

## ⬆️ Upgrading from v2.1.0

### Automatic Upgrade

The upgrade is automatic and requires no configuration changes.

### Steps

1. Update via HACS or manually replace files
2. **Restart Home Assistant** (required)
3. Verify FileFlows server logs are clean (no more "Unauthorized" errors)
4. Remove any dashboards/automations using the 4 removed sensors

### Expected Results

✅ **FileFlows server logs**: No more "Unauthorized: Invalid API token" errors
✅ **All working sensors**: Continue to show correct data
✅ **Storage Saved sensor**: Still shows detailed per-library breakdown (from v2.1.0)
✅ **Cleaner entity list**: Only functional sensors remain

---

## 🔍 Testing

After upgrading, verify:

1. **Check FileFlows server logs** (main fix):
   ```
   # Before v2.1.1:
   [WRN] Unauthorized: Invalid API token 'was not provided'

   # After v2.1.1:
   (No unauthorized errors - clean logs!)
   ```

2. **Check Home Assistant entities**:
   - Go to Settings → Devices & Services → FileFlows
   - Verify 24 core sensors are present (+ 5 NVIDIA if you have GPU)
   - 4 sensors removed: CPU, Memory, Temp, Log

3. **Check sensor values**:
   - Queue Size: Should show correct count
   - Storage Saved: Should show total GB with library breakdown
   - All other sensors: Should show correct values

---

## 📝 Technical Details

### Code Changes

**File: `custom_components/fileflows/api.py`**
- Modified `get_all_data()` to conditionally call endpoints based on authentication
- Remote endpoints only called when `not (self._username and self._password)`
- Lines 760-782: Storage savings logic
- Lines 805-810: Update available logic

**File: `custom_components/fileflows/sensor.py`**
- Removed 4 sensor definitions (lines 205-251)
- NVIDIA sensors unchanged (still created dynamically when GPU detected)

**Statistics**:
- 2 files changed
- +12 insertions
- -60 deletions
- Net code reduction: 48 lines

---

## 🤝 Compatibility

- **Home Assistant**: 2023.1.0 or newer
- **FileFlows**: 24.x or newer (tested with 25.12.9.6135)
- **Python**: 3.11 or newer

---

## 📚 Related Documentation

- [CHANGELOG.md](./CHANGELOG.md) - Complete version history
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - All 17 working FileFlows API endpoints
- [SETUP_COMPLETE.md](./SETUP_COMPLETE.md) - Setup and troubleshooting guide
- [README.md](./README.md) - Main documentation

---

## 🐛 Known Issues

None at this time. This release specifically fixes the main reported issue.

---

## 💬 Feedback

Found a bug or have a feature request? Please open an issue on [GitHub](https://github.com/RiDDiX/fileflows-ha/issues).

---

## 👏 Credits

- **Reported by**: Users experiencing "Unauthorized" errors in FileFlows logs
- **Developed with**: Claude Code
- **Maintainer**: @RiDDiX

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Full Changelog**: https://github.com/RiDDiX/fileflows-ha/compare/v2.1.0...v2.1.1

**Latest Release**: v2.1.1 | **Sensors**: 24 Core + 5 NVIDIA (optional) | **API Endpoints**: 17 Working
