import os
import time
import json
import logging
import psycopg2
from datetime import datetime, timedelta
from hyundai_kia_connect_api import VehicleManager

logger = logging.getLogger(__name__)

# Define paths
OPTIONS_FILE = "./data/options.json"

REGION_MAP = {"EUROPE": 1, "CANADA": 2, "USA": 3, "CHINA": 4, "AUSTRALIA": 5, "INDIA": 6, "NZ": 7, "BRAZIL": 8}
BRAND_MAP = {"KIA": 1, "CAR": 2, "GENESIS": 3}

def get_options():
    if os.path.exists(OPTIONS_FILE):
        with open(OPTIONS_FILE) as f:
            return json.load(f)
    else:
        logger.info(f"Options file not found at {OPTIONS_FILE}. Please configure via the web UI.")
        return None

def get_db_connection(options):
    return psycopg2.connect(
        host=options.get('db_host'),
        database=options.get('db_name'),
        user=options.get('db_user'),
        password=options.get('db_password'),
        port=options.get('db_port', 5432),
        connect_timeout=5
    )

def setup_database(options):
    conn = None
    try:
        conn = get_db_connection(options)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_trips (
                trip_date DATE,
                start_time TIME,
                distance_km REAL,
                drive_time_mins INT,
                idle_time_mins INT,
                avg_speed_kmh REAL,
                max_speed_kmh INT,
                UNIQUE (trip_date, start_time)
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS vehicle_daily_stats (
                stat_date DATE PRIMARY KEY,
                total_consumed_wh INT,
                engine_consumption_wh INT,
                climate_consumption_wh INT,
                onboard_electronics_wh INT,
                battery_care_wh INT,
                regenerated_energy_wh INT,
                distance REAL
            );
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"Database Setup Error: {e}")
    finally:
        if conn: conn.close()

def get_last_logged_date(options):
    conn = None
    try:
        conn = get_db_connection(options)
        cur = conn.cursor()
        cur.execute("SELECT MAX(trip_date) FROM vehicle_trips;")
        result = cur.fetchone()
        if result and result[0]:
            return result[0]
    except Exception as e:
        logger.warning(f"Warning: Could not fetch last logged date from DB: {e}")
    finally:
        if conn: conn.close()
    return (datetime.now() - timedelta(days=3)).date()

def main():
    try:
        tz = os.environ.get('TZ')
        if tz:
            os.environ['TZ'] = tz
            if hasattr(time, 'tzset'):
                time.tzset()
    except Exception as e:
        logger.warning(f"TZ setting skipped: {e}")

    options = get_options()
    if not options: return

    # Validate required DB options
    if not all([options.get('db_host'), options.get('db_name'), options.get('db_user')]):
        logger.error("Database configuration is incomplete. Please update via the web interface.")
        return

    # Validate required Kia options
    if not all([options.get('username'), options.get('password')]):
        logger.error("Kia/Car account configuration is incomplete. Please update via the web interface.")
        return

    setup_database(options)

    today = datetime.now().date()
    last_logged_date = get_last_logged_date(options)

    # We will fetch from last_logged_date + 1 up to today. 
    # If up to date, we can still fetch today's partial data.
    missing_dates = []
    current_date = min(last_logged_date + timedelta(days=1), today)
    while current_date <= today:
        missing_dates.append(current_date)
        current_date += timedelta(days=1)

    try:
        logger.info("Checking Online Account...")
        
        vm = None
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Checking Online Account (Attempt {attempt}/{max_retries})...")
                vm = VehicleManager(
                    region=REGION_MAP.get(options.get('region'), 5),
                    brand=BRAND_MAP.get(options.get('brand'), 1),
                    username=options['username'],
                    password=options['password'],
                    pin="" 
                )
                vm.check_and_refresh_token()
                vm.update_all_vehicles_with_cached_state()
                
                if vm.vehicles:
                    logger.info("Authentication successful.")
                    break
                else:
                    logger.info("No vehicles found in account yet.")
                    return
            except Exception as e:
                logger.error(f"Connection attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(10) # Reduced sleep for better responsiveness in web UI
                else:
                    logger.error("Max retries reached. Kia servers are likely down.")
                    return

        if not vm.vehicles:
            logger.warning("No vehicles found.")
            return

        logger.info("Starting vehicle sync...")
        vehicle = vm.vehicles[list(vm.vehicles.keys())[0]]
        
        conn = get_db_connection(options)
        cur = conn.cursor()

        # Sync daily stats
        if hasattr(vehicle, 'daily_stats') and vehicle.daily_stats:
            logger.info(f"Found {len(vehicle.daily_stats)} daily stats records. Syncing to DB...")
            for stat in vehicle.daily_stats:
                stat_date = stat.date.date() if isinstance(stat.date, datetime) else stat.date
                cur.execute('''
                    INSERT INTO vehicle_daily_stats 
                    (stat_date, total_consumed_wh, engine_consumption_wh, climate_consumption_wh, onboard_electronics_wh, battery_care_wh, regenerated_energy_wh, distance)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (stat_date) DO UPDATE SET
                    total_consumed_wh = EXCLUDED.total_consumed_wh,
                    engine_consumption_wh = EXCLUDED.engine_consumption_wh,
                    climate_consumption_wh = EXCLUDED.climate_consumption_wh,
                    onboard_electronics_wh = EXCLUDED.onboard_electronics_wh,
                    battery_care_wh = EXCLUDED.battery_care_wh,
                    regenerated_energy_wh = EXCLUDED.regenerated_energy_wh,
                    distance = EXCLUDED.distance;
                ''', (
                    stat_date, stat.total_consumed, stat.engine_consumption, stat.climate_consumption,
                    stat.onboard_electronics_consumption, stat.battery_care_consumption, stat.regenerated_energy, stat.distance
                ))

        months_to_fetch = sorted(list(set(d.strftime("%Y%m") for d in missing_dates)))
        if months_to_fetch:
            logger.info(f"Months to fetch for trips: {months_to_fetch}")

        for month_str in months_to_fetch:
            vm.update_month_trip_info(vehicle.id, month_str)
            days_in_this_month = [d for d in missing_dates if d.strftime("%Y%m") == month_str]
            
            for day in days_in_this_month:
                target_day_str = day.strftime("%Y%m%d")
                vm.update_day_trip_info(vehicle.id, target_day_str)
                
                if vehicle.day_trip_info and vehicle.day_trip_info.trip_list:
                    trips = reversed(vehicle.day_trip_info.trip_list)
                    inserted = 0
                    for trip in trips:
                        start_time = f"{trip.hhmmss[:2]}:{trip.hhmmss[2:4]}:{trip.hhmmss[4:]}"
                        date_formatted = day.strftime("%Y-%m-%d")
                        trip_data = (date_formatted, start_time, trip.distance, trip.drive_time, trip.idle_time, trip.avg_speed, trip.max_speed)
                        
                        cur.execute('''
                            INSERT INTO vehicle_trips 
                            (trip_date, start_time, distance_km, drive_time_mins, idle_time_mins, avg_speed_kmh, max_speed_kmh)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (trip_date, start_time) DO NOTHING;
                        ''', trip_data)
                        inserted += 1
                            
                    logger.info(f"Synced {inserted} trips for {day.strftime('%Y-%m-%d')} to DB.")
        
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        if 'conn' in locals() and conn:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
        logger.error(f"Critical error: {e}")

if __name__ == "__main__":
    # If run directly for testing, just log to console
    logging.basicConfig(level=logging.INFO)
    logger.info("----------")
    logger.info(f"Starting Data Sync (CLI mode): {datetime.now()}")
    main()
    logger.info(f"Finished Data Sync: {datetime.now()}")
    logger.info("==========")
