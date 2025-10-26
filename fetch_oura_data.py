import os
import json
from datetime import datetime, timedelta, date
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Load environment variables ---
load_dotenv()

# --- Load Oura Access Token ---
OURA_ACCESS_TOKEN = os.getenv("OURA_ACCESS_TOKEN")
if not OURA_ACCESS_TOKEN:
    print("Error: OURA_ACCESS_TOKEN not found in .env file.")
    exit()

# --- Load Supabase Credentials & Initialize Client ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # or SUPABASE_SERVICE_KEY
supabase = None

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase URL or Key not found in .env file. Will not save to DB.")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✓ Supabase client initialized.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")

# --- Oura API Configuration ---
OURA_API_URL = "https://api.ouraring.com/v2/usercollection"
headers = {
    'Authorization': f'Bearer {OURA_ACCESS_TOKEN}'
}

# --- Function to fetch data WITH PAGINATION ---
def fetch_oura_data_for_period(endpoint, start_date, end_date):
    """Fetches paginated data from Oura endpoint for a date range."""
    all_data = []
    url = f"{OURA_API_URL}/{endpoint}"
    params = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    print(f"\nFetching {endpoint} from {start_date} to {end_date}...")

    page_count = 0
    while url:
        page_count += 1
        print(f"  Fetching page {page_count}...")
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            records = data.get('data', [])
            all_data.extend(records)
            print(f"    > Fetched {len(records)} records on this page.")

            # Get the next page URL from 'next_token'
            next_token = data.get('next_token')
            if next_token:
                url = f"{OURA_API_URL}/{endpoint}?next_token={next_token}"
                params = {}
                print(f"    > Found next_token, preparing for next page...")
            else:
                url = None

        except requests.exceptions.RequestException as e:
            print(f"  ! Error fetching page {page_count} for {endpoint}: {e}")
            if e.response is not None:
                print(f"    Response status: {e.response.status_code}")
                print(f"    Response text: {e.response.text}")
            url = None
        except json.JSONDecodeError as e:
             print(f"  ! Error decoding JSON response for {endpoint}: {e}")
             url = None

    print(f"✓ Fetched a total of {len(all_data)} records for {endpoint} across {page_count} page(s).")
    return all_data

# --- Functions to save data to Supabase ---
def save_sleep_to_supabase(sleep_records):
    """Save sleep records to Supabase"""
    if not supabase or not sleep_records:
        return
    
    print(f"\nSaving {len(sleep_records)} sleep records to Supabase...")
    saved_count = 0
    
    for record in sleep_records:
        try:
            data = {
                'id': record['id'],
                'day': record['day'],
                'bedtime_start': record.get('bedtime_start'),
                'bedtime_end': record.get('bedtime_end'),
                'total_sleep_duration': record.get('total_sleep_duration'),
                'deep_sleep_duration': record.get('deep_sleep_duration'),
                'light_sleep_duration': record.get('light_sleep_duration'),
                'rem_sleep_duration': record.get('rem_sleep_duration'),
                'awake_time': record.get('awake_time'),
                'efficiency': record.get('efficiency'),
                'latency': record.get('latency'),
                'average_hrv': record.get('average_hrv'),
                'average_heart_rate': record.get('average_heart_rate'),
                'lowest_heart_rate': record.get('lowest_heart_rate'),
                'score': record.get('score'),
                'raw_data': record
            }
            
            # Upsert (insert or update if exists)
            result = supabase.table('oura_sleep').upsert(data).execute()
            saved_count += 1
            
        except Exception as e:
            print(f"  ! Error saving sleep record {record.get('id')}: {e}")
    
    print(f"✓ Saved {saved_count} sleep records to Supabase")

def save_activity_to_supabase(activity_records):
    """Save activity records to Supabase"""
    if not supabase or not activity_records:
        return
    
    print(f"\nSaving {len(activity_records)} activity records to Supabase...")
    saved_count = 0
    
    for record in activity_records:
        try:
            data = {
                'id': record['id'],
                'day': record['day'],
                'score': record.get('score'),
                'active_calories': record.get('active_calories'),
                'total_calories': record.get('total_calories'),
                'steps': record.get('steps'),
                'equivalent_walking_distance': record.get('equivalent_walking_distance'),
                'high_activity_time': record.get('high_activity_time'),
                'medium_activity_time': record.get('medium_activity_time'),
                'low_activity_time': record.get('low_activity_time'),
                'sedentary_time': record.get('sedentary_time'),
                'average_met': record.get('average_met'),
                'raw_data': record
            }
            
            result = supabase.table('oura_activity').upsert(data).execute()
            saved_count += 1
            
        except Exception as e:
            print(f"  ! Error saving activity record {record.get('id')}: {e}")
    
    print(f"✓ Saved {saved_count} activity records to Supabase")

def save_readiness_to_supabase(readiness_records):
    """Save readiness records to Supabase"""
    if not supabase or not readiness_records:
        return
    
    print(f"\nSaving {len(readiness_records)} readiness records to Supabase...")
    saved_count = 0
    
    for record in readiness_records:
        try:
            data = {
                'id': record['id'],
                'day': record['day'],
                'score': record.get('score'),
                'temperature_deviation': record.get('temperature_deviation'),
                'temperature_trend_deviation': record.get('temperature_trend_deviation'),
                'raw_data': record
            }
            
            result = supabase.table('oura_readiness').upsert(data).execute()
            saved_count += 1
            
        except Exception as e:
            print(f"  ! Error saving readiness record {record.get('id')}: {e}")
    
    print(f"✓ Saved {saved_count} readiness records to Supabase")

def save_heart_rate_to_supabase(heart_rate_records):
    """Save heart rate records to Supabase"""
    if not supabase or not heart_rate_records:
        return
    
    print(f"\nSaving {len(heart_rate_records)} heart rate records to Supabase...")
    saved_count = 0
    
    for record in heart_rate_records:
        try:
            data = {
                'timestamp': record['timestamp'],
                'bpm': record.get('bpm'),
                'source': record.get('source')
            }
            
            result = supabase.table('oura_heart_rate').upsert(data).execute()
            saved_count += 1
            
        except Exception as e:
            # Skip duplicate timestamps silently
            if 'duplicate key' not in str(e).lower():
                print(f"  ! Error saving heart rate record: {e}")
    
    print(f"✓ Saved {saved_count} heart rate records to Supabase")

# --- Main Execution ---
if __name__ == "__main__":
    # --- Date Range ---
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # Fetch last 30 days

    print(f"--- Starting Oura Data Fetch for {start_date} to {end_date} ---")

    # --- Fetch Data from Oura API ---
    sleep_records = fetch_oura_data_for_period("daily_sleep", start_date, end_date)
    activity_records = fetch_oura_data_for_period("daily_activity", start_date, end_date)
    readiness_records = fetch_oura_data_for_period("daily_readiness", start_date, end_date)
    heart_rate_records = fetch_oura_data_for_period("heartrate", start_date, end_date)
    
    # --- Save to Supabase ---
    if supabase:
        save_sleep_to_supabase(sleep_records)
        save_activity_to_supabase(activity_records)
        save_readiness_to_supabase(readiness_records)
        save_heart_rate_to_supabase(heart_rate_records)
        print("\n✓ All data synced to Supabase!")
    else:
        print("\n! Supabase not configured, data not saved to database")
    
    # --- Save to local JSON as backup ---
    backup_data = {
        'sleep': sleep_records,
        'activity': activity_records,
        'readiness': readiness_records,
        'heart_rate': heart_rate_records,
        'fetched_at': datetime.now().isoformat()
    }
    
    with open('oura_data_backup.json', 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    print("\n✓ Backup saved to oura_data_backup.json")
    print(f"\n--- Summary ---")
    print(f"Sleep: {len(sleep_records)} records")
    print(f"Activity: {len(activity_records)} records")
    print(f"Readiness: {len(readiness_records)} records")
    print(f"Heart Rate: {len(heart_rate_records)} records")
