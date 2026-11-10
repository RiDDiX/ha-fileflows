# Changelog

All notable changes to the FileFlows Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-11-10

### Changed
Authentication now uses FileFlows API token with HMAC signed requests for FileFlows 26.10 and later. Username and password login is removed by FileFlows. Existing entries ask for re authentication. Entity ids are unchanged.

### Added
Optional Fenrus endpoint token for licence free read only mode. Reauth and reconfigure flows. Update interval option now applies. Services take optional config_entry_id. pause_system takes minutes. Translations in en.json. Tests and CI validation including hassfest, HACS, ruff, and pytest.

### Removed
Remote info endpoints. strings.json. Root diagnostic scripts and duplicate release notes.

### Fixed
Entities show unavailable instead of 0 when the server is unreachable. System Paused binary sensor polarity. Wrong repo URLs in manifest. Routes aligned with api help for library file list all, Uids bodies, and OnHold status.

Minimum Home Assistant 2025.8

## [2.1.1] - 2026-01-06

### Removed
- **CPU Usage sensor** - `/api/system/info` endpoint doesn't exist on modern FileFlows servers
- **Memory Usage sensor** - Same endpoint unavailability
- **Temp Directory Size sensor** - Same endpoint unavailability
- **Log Directory Size sensor** - Same endpoint unavailability
- Reduced from 28 to 24 core sensors (NVIDIA sensors unchanged)

### Fixed
- **"Unauthorized: Invalid API token" errors** in FileFlows server logs
  - Stopped calling `/remote/info/shrinkage-groups` when authenticated
  - Stopped calling `/remote/info/update-available` when authenticated
  - Remote endpoints only used as fallback when no credentials configured
- **Cleaner API call pattern**: Only authenticated endpoints called when credentials available

### Changed
- API client now properly distinguishes between authenticated and unauthenticated modes
- Storage statistics fetching uses new endpoint when authenticated, skips remote endpoints
- Update checking only attempts remote endpoint when no authentication configured

### Technical Details
- Removed 4 sensors from sensor.py (lines 205-251)
- Fixed api.py get_all_data() to conditionally call endpoints based on auth status
- 2 files changed: +12 insertions, -60 deletions

---

## [2.1.0] - 2026-01-06

### Added
- **New Endpoint**: `/api/statistics/storage-saved` for detailed storage statistics
  - Per-library breakdown with items count
  - More accurate total savings calculation
  - Enhanced sensor attributes with library details
- **Comprehensive API Documentation**: Added `API_ENDPOINTS.md` with all 17 working endpoints
- **Setup Guide**: Added `SETUP_COMPLETE.md` with testing and troubleshooting instructions
- **Coordinator Properties**:
  - `storage_saved_stats` - Raw data from new statistics endpoint
  - `storage_saved_by_library` - Detailed per-library breakdown
  - Intelligent fallback logic to legacy endpoints

### Fixed
- **Sensor "unknown" values**: Changed all property checks from `> 0` to `>= 0`
  - Fixes sensors showing "unknown" when actual value is 0
  - Affects: queue_size, files_processed, files_processing, and all count sensors
- **Storage calculations**: Now use precise API data instead of approximations
- **Bearer token validation**: Simplified authentication flow in config_flow

### Changed
- **Storage Saved sensor**: Enhanced attributes with per-library items count
  - Now shows: library name, items count, saved GB, final GB
- **Coordinator logic**: All properties use consistent `if value is not None and value >= 0:` pattern
- **API preference**: Uses `/api/status` over `/remote/info/status` when authenticated
- **Version fetching**: Prefers authenticated `/api/system/version` endpoint

### Improved
- **Error handling**: Better fallback logic for unavailable endpoints
- **Documentation**: Comprehensive endpoint documentation and troubleshooting guide
- **Code quality**: Consistent patterns across all coordinator properties

### Technical Details
- 7 files changed: +866 insertions, -51 deletions
- New documentation: API_ENDPOINTS.md (371 lines), SETUP_COMPLETE.md (293 lines)
- Improved coordinator.py with 137+ lines of new storage logic
- Enhanced api.py with 78 lines of changes for new endpoint

### Known Limitations
- `/api/system/info` endpoint not available on newer FileFlows servers
  - CPU/Memory sensors may show 0 - this is expected
- `/api/worker` endpoint not available on some configurations
  - Falls back to processingFiles from /api/status

### Migration Notes
For users upgrading from 2.0.x:
1. Restart Home Assistant after update
2. Reload the FileFlows integration (or restart HA)
3. Storage Saved sensor will now show more accurate data with library details
4. No configuration changes required - upgrade is automatic

---

## [2.0.1] - Previous Release

### Features
- Bearer Token authentication fully implemented
- 17 API endpoints integrated
- 28 main sensors + 5 NVIDIA sensors
- Comprehensive entity coverage
