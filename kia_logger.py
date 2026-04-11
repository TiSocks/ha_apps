import os
import json
import csv
import urllib.request
from datetime import datetime, timedelta
from hyundai_kia_connect_api import VehicleManager

# Define paths (Using /share assumes you are running this as the Add-on)
CSV_FILE = "/share/kia_trips_log.csv"
OPTIONS_FILE = "/data/options.json"

def get_options():
    try:
        with open(OPTIONS_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback for testing outside the add-on environment
        print("Add-on options not found. Ensure you are running within Home Assistant.")
        return None

def get_last_logged_date():
    """Reads the CSV to find the last successfully logged date."""
    if not os.path.isfile(CSV_FILE):
        # If no file exists, default to catching up on the last 3 days
        print("No CSV found. Initializing a new one and fetching the last 3 days.")
        return (datetime.now() - timedelta(days=3)).date()

    try:
        with open(CSV_FILE, 'r') as file:
            lines = file.readlines()
            if len(lines) > 1: # Ensure there is data beyond the header
                last_line = lines[-1].strip()
                last_date_str = last_line.split(',')[0]
                return datetime.strptime(last_date_str, "%Y-%m-%d").date()
    except Exception as e:
        print(f"Warning: Could not parse last date from CSV. Defaulting to 3 days ago. Error: {e}")
        
    return (datetime.now() - timedelta(days=3)).date()

def stop_addon():
    """Tells the Home Assistant Supervisor to cleanly shut down this add-on in the UI."""
    print("Task complete. Telling Home Assistant to stop the Add-on...")
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
    print(f"\n--- Starting Kia Trip Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    options = get_options()
    if not options:
        return

    # 1. Determine the Date Gap
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_logged_date = get_last_logged_date()

    if last_logged_date >= yesterday:
        print(f"Logs are already up to date (Last record: {last_logged_date}). Exiting.")
        return

    # Generate a list of all dates that are missing
    missing_dates = []
    current_date = last_logged_date + timedelta(days=1)
    while current_date <= yesterday:
        missing_dates.append(current_date)
        current_date += timedelta(days=1)
        
    print(f"Identified {len(missing_dates)} missing day(s) to fetch: "
          f"From {missing_dates[0]} to {missing_dates[-1]}")

    # 2. Authenticate with Kia
    print("Authenticating with Kia Connect...")
    try:
        vm = VehicleManager(
            region=options['region'],
            brand=options['brand'],
            username=options['username'],
            password=options['password'],
            pin="" 
        )

        vm.check_and_refresh_token()
        vm.update_all_vehicles_with_cached_state()

        # --- NEW SAFETY CHECK ---
        if not vm.vehicles:
            print("Login successful, but no vehicles are paired to this account yet.")
            print("Waiting for delivery day! Exiting gracefully.")
            return
        # ------------------------

        vehicle_id = list(vm.vehicles.keys())[0]
        vehicle = vm.vehicles[vehicle_id]
        print(f"Successfully connected to vehicle: {vehicle.name}")

        file_exists = os.path.isfile(CSV_FILE)
        
        # 3. Group missing dates by month (YYYYMM) to minimize API calls
        months_to_fetch = sorted(list(set(d.strftime("%Y%m") for d in missing_dates)))
        
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)

            # Write header if file is brand new
            if not file_exists:
                writer.writerow(["Date", "Start Time", "Distance (km)", "Drive Time (mins)", "Idle Time (mins)"])

            # 4. Fetch and Write Data
            for month_str in months_to_fetch:
                print(f"Fetching summary data for month: {month_str}")
                vm.update_month_trip_info(vehicle.id, month_str)
                
                # Find all missing days that fall within this specific month
                days_in_this_month = [d for d in missing_dates if d.strftime("%Y%m") == month_str]
                
                for day in days_in_this_month:
                    target_day_str = day.strftime("%Y%m%d")
                    print(f"  -> Pulling specific trips for {target_day_str}...")
                    
                    vm.update_day_trip_info(vehicle.id, target_day_str)
                    
                    if vehicle.day_trip_info is not None and vehicle.day_trip_info.trip_list:
                        # Reverse list so morning trips are written before evening trips
                        trips = reversed(vehicle.day_trip_info.trip_list)
                        trip_count = 0
                        
                        for trip in trips:
                            start_time = f"{trip.hhmmss[:2]}:{trip.hhmmss[2:4]}:{trip.hhmmss[4:]}"
                            date_formatted = day.strftime("%Y-%m-%d")
                            
                            writer.writerow([date_formatted, start_time, trip.distance, trip.drive_time, trip.idle_time])
                            trip_count += 1
                            
                        print(f"     Appended {trip_count} trips.")
                    else:
                        print("     No drives recorded on this day.")

        print("Sync complete. Closing application.")

    except Exception as e:
        print(f"Critical error during sync: {e}")

if __name__ == "__main__":
    main()
    stop_addon()