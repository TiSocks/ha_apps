import os
import time
import json
import csv
import urllib.request
import psycopg2 # Ensure you add 'psycopg2-binary' to your requirements.txt
from datetime import datetime, timedelta
from hyundai_kia_connect_api import VehicleManager

# Define paths
OPTIONS_FILE = "/data/options.json"

REGION_MAP = {"EUROPE": 1, "CANADA": 2, "USA": 3, "CHINA": 4, "AUSTRALIA": 5, "INDIA": 6, "NZ": 7, "BRAZIL": 8}
BRAND_MAP = {"KIA": 1, "HYUNDAI": 2, "GENESIS": 3}

def get_options():
    try:
        with open(OPTIONS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        print("Add-on options not found. Ensure you are running within Home Assistant.")
        return None

def write_to_postgres(options, trip_data):
    """Writes a single trip record to the PostgreSQL database."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=options.get('db_host'),
            database=options.get('db_name'),
            user=options.get('db_user'),
            password=options.get('db_password'),
            port=options.get('db_port', 5432)
        )
        cur = conn.cursor()

       # Insert data
        insert_query = '''
            INSERT INTO vehicle_trips 
            (trip_date, start_time, distance_km, drive_time_mins, idle_time_mins, avg_speed_kmh, max_speed_kmh)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trip_date, start_time) DO NOTHING;
        '''
        cur.execute(insert_query, trip_data)
        
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"PostgreSQL Error: {e}")
    finally:
        if conn is not None:
            conn.close()

def get_last_logged_date(csv_path):
    if not os.path.isfile(csv_path):
        return (datetime.now() - timedelta(days=3)).date()
    try:
        with open(csv_path, 'r') as file:
            lines = file.readlines()
            if len(lines) > 1:
                last_line = lines[-1].strip()
                last_date_str = last_line.split(',')[0]
                return datetime.strptime(last_date_str, "%Y-%m-%d").date()
    except Exception as e:
        print(f"Warning: Could not parse CSV date: {e}")
    return (datetime.now() - timedelta(days=3)).date()

def stop_addon():
    token = os.environ.get("SUPERVISOR_TOKEN")
    if token:
        req = urllib.request.Request(
            "http://supervisor/addons/self/stop",
            headers={"Authorization": f"Bearer {token}"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"API Error: {e}")

def main():
    tz = os.environ.get('TZ', 'UTC')
    os.environ['TZ'] = tz
    time.tzset()

    print("----------")
    print(f"Starting Trip Sync: {datetime.now()}")
    
    options = get_options()
    if not options: return

    output_folder = options.get('folder', '/share/').rstrip('/') + '/'
    csv_path = os.path.join(output_folder, "trips_log.csv")
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_logged_date = get_last_logged_date(csv_path)

    if last_logged_date >= yesterday:
        print(f"Logs up to date ({last_logged_date}).")
        return

    missing_dates = []
    current_date = last_logged_date + timedelta(days=1)
    while current_date <= yesterday:
        missing_dates.append(current_date)
        current_date += timedelta(days=1)

    try:
        vm = VehicleManager(
            region=REGION_MAP.get(options.get('region'), 1),
            brand=BRAND_MAP.get(options.get('brand'), 1),
            username=options['username'],
            password=options['password'],
            pin="" 
        )
        print("Checking Online Account...")
        vm.check_and_refresh_token()
        vm.update_all_vehicles_with_cached_state()

        if not vm.vehicles:
            print("No vehicles found.")

        vehicle = vm.vehicles[list(vm.vehicles.keys())[0]]
        file_exists = os.path.isfile(csv_path)
        months_to_fetch = sorted(list(set(d.strftime("%Y%m") for d in missing_dates)))
        
        with open(csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Date", "Start Time", "Distance (km)", "Drive Time (mins)", "Idle Time (mins)", "Avg Speed (km/h)", "Max Speed (km/h)"])

            for month_str in months_to_fetch:
                vm.update_month_trip_info(vehicle.id, month_str)
                days_in_this_month = [d for d in missing_dates if d.strftime("%Y%m") == month_str]
                
                for day in days_in_this_month:
                    target_day_str = day.strftime("%Y%m%d")
                    vm.update_day_trip_info(vehicle.id, target_day_str)
                    
                    if vehicle.day_trip_info and vehicle.day_trip_info.trip_list:
                        trips = reversed(vehicle.day_trip_info.trip_list)
                        for trip in trips:
                            start_time = f"{trip.hhmmss[:2]}:{trip.hhmmss[2:4]}:{trip.hhmmss[4:]}"
                            date_formatted = day.strftime("%Y-%m-%d")
                            
                            # Prepare data tuple for CSV and Postgres
                            row = [date_formatted, start_time, trip.distance, trip.drive_time, trip.idle_time, trip.avg_speed, trip.max_speed]
                            
                            # Write to CSV
                            writer.writerow(row)
                            
                            # Write to Postgres
                            #write_to_postgres(options, row)
                            
                        print(f"Synced {day.strftime('%Y-%m-%d')} to CSV and DB.")

        print(f"Finished Trip Sync: {datetime.now()}")
        print("==========")
        print(" ")

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    main()
    stop_addon()
