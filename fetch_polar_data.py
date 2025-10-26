import os
import json
import requests
import base64
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from supabase import create_client, Client
from urllib.parse import urlparse

# --- Load environment variables ---
load_dotenv()

# Load token
try:
    with open("polar_token.json", "r") as f:
        token = json.load(f)
except FileNotFoundError:
    print("Error: polar_token.json not found. Please run the authentication script first.")
    exit()
except json.JSONDecodeError:
    print("Error: polar_token.json is corrupted or empty.")
    exit()

ACCESS_TOKEN = token.get('access_token')
USER_ID = token.get('x_user_id')
BASE_URL = "https://www.polaraccesslink.com/v3"

if not ACCESS_TOKEN or not USER_ID:
    print("Error: 'access_token' or 'x_user_id' missing from polar_token.json.")
    exit()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = None
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: Supabase URL or Key not found in .env file. Will not save to DB.")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✓ Supabase client initialized.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

def check_user_info():
    """Get user information"""
    url = f"{BASE_URL}/users/{USER_ID}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        print(f"\n--- User Info ---")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user info: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None

def create_exercise_transaction():
    """Create a transaction to access exercise data"""
    url = f"{BASE_URL}/users/{USER_ID}/exercise-transactions"
    try:
        response = requests.post(url, headers=headers)
        print(f"\n--- Create Exercise Transaction ---")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201: # Created
            data = response.json()
            transaction_id = data.get('transaction-id')
            exercise_links = data.get('exercises', [])
            print(f"Transaction ID: {transaction_id}")
            print(f"Exercises available immediately: {len(exercise_links)}")
            return transaction_id, exercise_links
        elif response.status_code == 204: # No new data
            print("No new exercises available")
            return None, []
        else:
            response.raise_for_status() # Raise error for other statuses
            return None, []
    except requests.exceptions.RequestException as e:
        print(f"Error creating exercise transaction: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None, []

def list_exercises_in_transaction(transaction_id):
    """List exercises available within a specific transaction"""
    url = f"{BASE_URL}/users/{USER_ID}/exercise-transactions/{transaction_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"\n--- List Exercises in Transaction {transaction_id} ---")
        print(f"Status: {response.status_code}")
        exercise_links = response.json().get('exercises', [])
        print(f"Exercises found: {len(exercise_links)}")
        return exercise_links
    except requests.exceptions.RequestException as e:
        print(f"Error listing exercises in transaction: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return []

def get_exercise_summary(exercise_url):
    """Get specific exercise summary using its direct URL"""
    print(f"Fetching exercise summary from: {exercise_url}")
    try:
        response = requests.get(exercise_url, headers=headers)
        response.raise_for_status()
        print(f"Status: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch exercise: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None

def get_exercise_gpx(exercise_id):
    """Get exercise GPX data"""
    url = f"{BASE_URL}/exercises/{exercise_id}/gpx"
    gpx_headers = headers.copy()
    gpx_headers['Accept'] = 'application/vnd.polar.exercise.gpx+xml'
    try:
        response = requests.get(url, headers=gpx_headers)
        response.raise_for_status()
        print(f"Fetching GPX for {exercise_id} - Status: {response.status_code}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch GPX: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None

def commit_exercise_transaction(transaction_id):
    """Commit (mark as handled) an exercise transaction"""
    url = f"{BASE_URL}/users/{USER_ID}/exercise-transactions/{transaction_id}"
    try:
        response = requests.put(url, headers=headers)
        print(f"\n--- Committing Exercise Transaction {transaction_id} ---")
        print(f"Status: {response.status_code}")
        if response.status_code == 204:
            print("Transaction committed successfully.")
            return True
        else:
            response.raise_for_status()
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to commit transaction: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return False

def create_activity_transaction():
    """Create a transaction to access daily activity summaries"""
    url = f"{BASE_URL}/users/{USER_ID}/activity-transactions"
    try:
        response = requests.post(url, headers=headers)
        print(f"\n--- Create Activity Transaction ---")
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            transaction_id = data.get('transaction-id')
            activity_links = data.get('activity-log', [])
            print(f"Transaction ID: {transaction_id}")
            print(f"Activity summaries available immediately: {len(activity_links)}")
            return transaction_id, activity_links
        elif response.status_code == 204:
            print("No new activities available")
            return None, []
        else:
            response.raise_for_status()
            return None, []
    except requests.exceptions.RequestException as e:
        print(f"Error creating activity transaction: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None, []

def list_activities_in_transaction(transaction_id):
    """List activities available within a specific transaction"""
    url = f"{BASE_URL}/users/{USER_ID}/activity-transactions/{transaction_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"\n--- List Activities in Transaction {transaction_id} ---")
        print(f"Status: {response.status_code}")
        activity_links = response.json().get('activity-log', [])
        print(f"Activity links found: {len(activity_links)}")
        return activity_links
    except requests.exceptions.RequestException as e:
        print(f"Error listing activities in transaction: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return []

def get_activity_summary(activity_url):
    """Get specific daily activity summary using its direct URL"""
    print(f"Fetching activity summary from: {activity_url}")
    try:
        response = requests.get(activity_url, headers=headers)
        response.raise_for_status()
        print(f"Status: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch activity summary: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None

def commit_activity_transaction(transaction_id):
    """Commit (mark as handled) an activity transaction"""
    url = f"{BASE_URL}/users/{USER_ID}/activity-transactions/{transaction_id}"
    try:
        response = requests.put(url, headers=headers)
        print(f"\n--- Committing Activity Transaction {transaction_id} ---")
        print(f"Status: {response.status_code}")
        if response.status_code == 204:
            print("Activity transaction committed successfully.")
            return True
        else:
            response.raise_for_status()
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to commit activity transaction: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return False


# ==============================================================================
# --- MAIN EXECUTION BLOCK (CORRECTED) ---
# ==============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("POLAR DATA FETCH & SAVE TO SUPABASE")
    print("=" * 50)

    user = check_user_info()
    if not user:
        print("Could not fetch user info, exiting.")
        exit()
    
    # --- Process Exercises ---
    print("\n" + "=" * 50)
    print("PROCESSING EXERCISES")
    print("=" * 50)
    
    ex_transaction_id, ex_links = create_exercise_transaction()
    exercises_to_save_to_db = []

    if ex_transaction_id:
        # If links weren't returned immediately, list them from the transaction
        if not ex_links:
            print("Transaction created, listing exercises from transaction...")
            ex_links = list_exercises_in_transaction(ex_transaction_id)
            
        exercises_to_save_to_db = [] # <<< Initialize list here

        if ex_links:
            print(f"\nFetching details for {len(ex_links)} exercises...")
            for link in ex_links:
                summary = get_exercise_summary(link)
                
                if summary:
                    # --- Format data for Supabase ---
                    
                    # 1. Safely retrieve and convert the Polar Exercise ID (THE FIX)
                    polar_ex_id_raw = summary.get('id')
                    try:
                        # Convert to integer directly using str() for robustness
                        polar_ex_id = int(str(polar_ex_id_raw)) 
                    except (ValueError, TypeError):
                        print(f"  ! Warning: Could not parse exercise ID: {polar_ex_id_raw}. Skipping record.")
                        continue # Skip to the next link if ID is invalid
                        
                    # 2. Safely retrieve Polar User ID
                    polar_user_url = summary.get('polar-user', '')
                    # Extract the ID from the URL link, convert to int, or use POLAR_USER_ID fallback
                    polar_user_id_int = int(polar_user_url.split('/')[-1]) if polar_user_url else POLAR_USER_ID 

                    # 3. Create the formatted dictionary
                    formatted_ex = {
                        'polar_user_id': polar_user_id_int,
                        'polar_exercise_id': polar_ex_id,
                        'start_time': summary.get('start-time'),
                        'duration': summary.get('duration'),
                        'sport': summary.get('detailed-sport-info'),
                        'distance': summary.get('distance'),
                        'calories': summary.get('calories'),
                        'average_hr': summary.get('heart-rate', {}).get('average'),
                        'max_hr': summary.get('heart-rate', {}).get('maximum'),
                    }
                    
                    # 4. Append to the saving list
                    if formatted_ex['polar_exercise_id'] and formatted_ex['start_time']:
                        exercises_to_save_to_db.append(formatted_ex)
                    else:
                        print(f"  ! Warning: Skipping exercise {polar_ex_id} due to missing essential data.")
            

        # --- Upsert exercises to Supabase ---
        if exercises_to_save_to_db and supabase:
            print(f"\nAttempting to upsert {len(exercises_to_save_to_db)} exercise records to Supabase...")
            try:
                response = supabase.table('polar_exercises').upsert(
                    exercises_to_save_to_db,
                    on_conflict='polar_exercise_id' # Assumes 'polar_exercise_id' is a UNIQUE constraint
                ).execute()
                
                # The V2 client returns data differently. Check for error attribute.
                if hasattr(response, 'error') and response.error:
                     print(f"! Supabase error during exercise upsert: {response.error}")
                elif hasattr(response, 'data'):
                     print(f"✓ Supabase response: Upserted {len(response.data)} exercise records.")
                else:
                    print(f"✓ Supabase exercise upsert request sent (check DB for results).")
            except Exception as e:
                print(f"! Error inserting Polar exercise data into Supabase: {e}")
        elif not supabase:
            print("\nSupabase client not initialized. Skipping DB insertion for exercises.")
        elif not exercises_to_save_to_db:
            print("\nNo valid exercise data formatted for DB insertion.")

        # --- Commit transaction ---
        if commit_exercise_transaction(ex_transaction_id):
            print("✓ Exercise transaction committed.")
        else:
            print("! Failed to commit exercise transaction.")

    else:
        # This 'else' catches the 204 No Content case
        print("No new exercise transaction created (no new data).")


    # --- Process Activities ---
    print("\n" + "=" * 50)
    print("PROCESSING ACTIVITIES")
    print("=" * 50)
    act_transaction_id, act_links = create_activity_transaction()
    activities_to_save_to_db = []

    if act_transaction_id:
        # If links weren't returned immediately, list them
        if not act_links:
            print("Activity transaction created, listing activities from transaction...")
            act_links = list_activities_in_transaction(act_transaction_id)

        if act_links:
            print(f"\nFetching details for {len(act_links)} activity summaries...")
            for link in act_links:
                summary = get_activity_summary(link)
                if summary:
                    # --- Format data for Supabase ---
                    polar_user_url = summary.get('polar-user', '')
                    polar_user_id_from_summary = polar_user_url.split('/')[-1] if polar_user_url else USER_ID

                    formatted_act = {
                        'polar_user_id': polar_user_id_from_summary,
                        'polar_transaction_id': act_transaction_id,
                        'date': summary.get('date'),
                        'calories': summary.get('calories'),
                        'active_calories': summary.get('active-calories'),
                        'duration': summary.get('active-duration'),
                        'active_steps': summary.get('active-steps'),
                    }
                    if formatted_act['date']:
                        activities_to_save_to_db.append(formatted_act)
                else:
                    print(f"Warning: Failed to get summary for link {link}")
        else:
            print("Transaction created, but no new activity summaries found.")
            
        # --- Upsert activities to Supabase ---
        if activities_to_save_to_db and supabase:
            print(f"\nAttempting to upsert {len(activities_to_save_to_db)} activity records to Supabase...")
            try:
                response = supabase.table('polar_daily_activity').upsert(
                    activities_to_save_to_db,
                    on_conflict='date' # Assumes 'date' is a UNIQUE constraint
                ).execute()

                if hasattr(response, 'error') and response.error:
                     print(f"! Supabase error during activity upsert: {response.error}")
                elif hasattr(response, 'data'):
                     print(f"✓ Supabase response: Upserted {len(response.data)} activity records.")
                else:
                    print(f"✓ Supabase activity upsert request sent (check DB for results).")
            except Exception as e:
                print(f"! Error inserting Polar activity data into Supabase: {e}")
        elif not supabase:
            print("\nSupabase client not initialized. Skipping DB insertion for activities.")
        elif not activities_to_save_to_db:
            print("\nNo valid activity data formatted for DB insertion.")

        # --- Commit transaction ---
        if commit_activity_transaction(act_transaction_id):
            print("✓ Activity transaction committed.")
        else:
            print("! Failed to commit activity transaction.")

    else:
        # This 'else' catches the 204 No Content case
        print("No new activity transaction created (no new data).")


    # --- Final Summary ---
    print("\n" + "=" * 50)
    print(f"✓ Exercises processed/saved: {len(exercises_to_save_to_db)}")
    print(f"✓ Activities processed/saved: {len(activities_to_save_to_db)}")
    print("--- Polar data fetch and save complete. ---")