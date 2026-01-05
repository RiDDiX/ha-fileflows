# FileFlows Home Assistant Integration v2.1.0

## 🎉 Release Highlights

### New Storage Statistics Endpoint
This release adds support for the `/api/statistics/storage-saved` endpoint, providing more accurate and detailed storage savings data with per-library breakdown and items count.

### Bug Fixes for "Unknown" Sensor Values
Fixed a critical issue where sensors would show "unknown" when actual values were 0, affecting queue size, file counts, and other metrics.

---

## ✨ What's New

### 🆕 Features

#### Storage Statistics Enhancement
- **New API Endpoint Integration**: `/api/statistics/storage-saved`
  - More accurate total savings calculation
  - Per-library breakdown with items count
  - Enhanced sensor attributes showing:
    - Library name
    - Number of items processed
    - Storage saved in GB
    - Final file size in GB

Example sensor attribute output:
```json
{
  "by_library": [
    {
      "library": "Filme",
      "items": 1950,
      "saved_gb": 1340.56,
      "final_gb": 4086.45
    },
    {
      "library": "Bücher",
      "items": 169,
      "saved_gb": 2.78,
      "final_gb": 368.79
    }
  ]
}
```

#### Documentation
- **API_ENDPOINTS.md**: Complete documentation of all 17 working API endpoints
- **SETUP_COMPLETE.md**: Comprehensive setup, testing, and troubleshooting guide
- **CHANGELOG.md**: Structured changelog following Keep a Changelog format

### 🐛 Bug Fixes

#### Sensor "Unknown" Values Fixed
**Problem**: Sensors showed "unknown" when actual values were 0
**Solution**: Changed all property checks from `> 0` to `>= 0`

**Affected sensors**:
- Queue Size
- Files Unprocessed
- Files Processing
- Files Processed
- All count sensors (nodes, libraries, flows, etc.)

**Impact**: Sensors now correctly show `0` instead of `unknown` when there are no items.

#### Storage Calculation Improvements
- Uses precise API data instead of approximations
- Intelligent fallback to legacy endpoints
- Better handling of missing or unavailable data

### 🔧 Improvements

#### Coordinator Enhancements
- All properties use consistent `if value is not None and value >= 0:` pattern
- Better error handling for unavailable endpoints
- New properties:
  - `storage_saved_stats` - Raw statistics data
  - `storage_saved_by_library` - Detailed library breakdown

#### API Client Updates
- Prefers `/api/status` over `/remote/info/status` when authenticated
- Uses `/api/system/version` instead of remote version endpoint
- Improved Bearer token validation in config flow

---

## 📊 Statistics

- **Files Changed**: 7
- **Lines Added**: +866
- **Lines Removed**: -51
- **New Documentation**: 664 lines across 2 files
- **Test Coverage**: All 17 working endpoints verified

---

## 📚 Documentation

### New Documentation Files
1. **API_ENDPOINTS.md** (371 lines)
   - Complete list of all 17 functional endpoints
   - Status indicators for each endpoint
   - Example responses and usage notes
   - Known limitations documented

2. **SETUP_COMPLETE.md** (293 lines)
   - Step-by-step setup instructions
   - Testing procedures
   - Troubleshooting guide
   - Expected sensor values

3. **CHANGELOG.md**
   - Structured release history
   - Migration notes
   - Technical details

---

## ⚙️ Installation

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to Integrations
3. Search for "FileFlows"
4. Click Install
5. Restart Home Assistant

### Manual Installation
1. Download the latest release
2. Copy `custom_components/fileflows` to your Home Assistant `custom_components` directory
3. Restart Home Assistant
4. Add FileFlows integration via UI

---

## 🚀 Upgrading from 2.0.x

### Automatic Upgrade
The upgrade is automatic and requires no configuration changes.

### Steps
1. Update via HACS or manually replace files
2. Restart Home Assistant
3. Reload FileFlows integration (or restart HA again)
4. Verify sensors show correct values

### What to Expect
- Storage Saved sensor will show more accurate data
- No more "unknown" values for 0 counts
- Enhanced attributes on storage sensor
- All existing sensors continue to work

### Breaking Changes
**None** - This release is fully backward compatible.

---

## 🔍 Known Issues & Limitations

### Endpoint Availability
Some endpoints are not available on all FileFlows server versions:

1. **`/api/system/info`** - Not available on newer servers
   - CPU/Memory sensors may show 0
   - This is expected and does not affect core functionality

2. **`/api/worker`** - Not available on some configurations
   - Falls back to `processingFiles` from `/api/status`
   - No user impact

### Compatibility
- **Home Assistant**: 2023.1.0 or newer
- **FileFlows**: 24.x or newer (tested with 25.12.9.6135)
- **Python**: 3.11 or newer

---

## 📝 Full Changelog

See [CHANGELOG.md](./CHANGELOG.md) for complete details.

---

## 🤝 Contributing

Found a bug or have a feature request? Please open an issue on [GitHub](https://github.com/RiDDiX/fileflows-ha/issues).

---

## 👏 Credits

This release was developed with assistance from Claude Code.

**Maintainer**: @RiDDiX

---

## 📄 License

This project follows the same license as Home Assistant.

---

**Full Changelog**: https://github.com/RiDDiX/fileflows-ha/compare/v2.0.1...v2.1.0
