# Changelog

## [1.1.0] - 2026-05-10
### Added
- **Daily Stats Tracking:** The add-on now fetches `daily_stats` (energy consumption, regenerated energy, etc.) and saves them to a new PostgreSQL table (`vehicle_daily_stats`).
- **PostgreSQL Database Auto-Setup:** The add-on now automatically creates necessary database tables (`vehicle_trips` and `vehicle_daily_stats`) on startup if they don't exist.
- **Local Testing Support:** You can now place a local `options.json` file in the add-on folder to test natively outside of Home Assistant Docker.
- **Cross-Platform Compatibility:** Replaced Unix-specific time methods to allow testing natively on Windows.

### Changed
- **Storage Backend Shift:** Changed the primary data store from a local CSV file to PostgreSQL.
- **Dependencies:** Updated base Docker image to `python:3.12-alpine` for improved performance and security.

### Removed
- **CSV Support:** Removed all local CSV writing components. The `folder` configuration option has been removed from `config.yaml`.
