# Kia / Hyundai / Genesis Data Logger

A Home Assistant Add-on that automatically syncs your daily vehicle trip logs and energy stats from the Kia Connect / Hyundai Bluelink / Genesis Connected Services API directly into a PostgreSQL database.

## Features
- **Data Syncing:** Fetches un-synced trips available on your profile for all available vehicles.
- **Energy Stats:** Fetches your daily energy consumption and regenerated energy.
- **Database Integration:** Automatically creates and updates `vehicle_trips` and `vehicle_daily_stats` tables in your PostgreSQL database.
- **Web UI Dashboard:** Features a standalone web interface on port `5002` to manage sync intervals, flush logs, and manually trigger sync operations.
- **Robust:** Graceful error handling with retry loops for Kia server downtime.

## Configuration Options
You must provide your Kia Connect credentials and your PostgreSQL connection details.

- **username**: Your Kia Connect / Bluelink email address.
- **password**: Your password.
- **region**: Your region (e.g. `AUSTRALIA`, `EUROPE`, `USA`).
- **brand**: Your brand (`KIA`, `HYUNDAI`, `GENESIS`).
- **db_host**: Your PostgreSQL server host IP/hostname.
- **db_name**: Name of the database to write to.
- **db_user**: Database username.
- **db_password**: Database password.
- **db_port**: PostgreSQL port (default: `5432`).

## Requirements
- You must have a PostgreSQL database accessible by this add-on. If you don't have one, you can install the official Home Assistant PostgreSQL add-on.
