import os
import datetime
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import json
import uuid
import datetime
import requests  # <-- add this at the top of the file

# --- Dynamic Path Resolution ---
# 1. Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Go up two levels to reach the local-rag/ root directory
PROJECT_ROOT = os.path.abspath(os.path.join(current_dir, "..", ".."))

# 3. Define the shared data path
SAAPP_DATA_DIR = os.path.join(PROJECT_ROOT, "saapp_data", "time")

logger = logging.getLogger("SASS Logger")

# The permissions scope required to write events to your calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    # 1. Load credentials from the environment (The 'Client ID' setup)
    creds_json = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    
    # 2. Load the token from the environment (The 'Permission' key)
    token_json = json.loads(os.getenv("GOOGLE_TOKEN_JSON"))
    
    # 3. Combine them to build the service
    creds = Credentials.from_authorized_user_info(token_json, SCOPES)
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        
    return build('calendar', 'v3', credentials=creds)


def create_google_calendar_event(username: str, summary: str, start_time_iso: str, duration_minutes: int = 30) -> str:
    """
    Executes a live API network action call to insert an event and 
    mirrors it into the local SAAPP data store.
    """
    logger.info(f"[TOOL EXECUTION] Connecting to Google API for '{summary}' on {start_time_iso}")
    
    try:
        # 1. Initialize the authenticated Google client connection
        service = get_calendar_service()
        
        # 2. Parse out the start time parameters
        start_dt = datetime.datetime.fromisoformat(start_time_iso)
        end_dt = start_dt + datetime.timedelta(minutes=int(duration_minutes))
        
        # 3. Build the payload
        event_payload = {
            'summary': summary,
            'description': 'Automated cockpit entry created via local Personal Assistant.',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Chicago',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Chicago',
            },
            'reminders': {'useDefault': True},
        }
        
        # 4. Push to Google
        created_event = service.events().insert(calendarId='primary', body=event_payload).execute()
        
        # --- SAAPP LOCAL MIRROR (Dynamic Path) ---
        try:
            # Ensure the directory exists
            if not os.path.exists(SAAPP_DATA_DIR):
                os.makedirs(SAAPP_DATA_DIR, exist_ok=True)
                
            file_path = os.path.join(SAAPP_DATA_DIR, f"{username}_events.json")
            
            # Read existing entries
            entries = []
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    try:
                        entries = json.load(f)
                    except json.JSONDecodeError:
                        pass # File is empty or malformed
            
            # Create the entry
            new_entry = {
                "id": str(uuid.uuid4()),
                "username": username,
                "activity": created_event.get("summary", "Untitled Event"),
                "duration_hours": float(duration_minutes // 60),
                "duration_minutes": int(duration_minutes % 60),
                "date": created_event["start"]["dateTime"].split("T")[0],
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "notes": created_event.get("description", ""),
                "type": "event"
            }
            
            # Append and write back
            entries.append(new_entry)
            with open(file_path, "w") as f:
                json.dump(entries, f, indent=2)
                
            logger.info("[✓] Mirrored event to SAAPP JSON file!")
            
        except Exception as mirror_error:
            logger.error(f"[!] Failed to mirror event: {mirror_error}")

        return json.dumps({
            "status": "success",
            "message": f"Added '{summary}' to your Google Calendar."
        })
        
    except Exception as api_error:
        logger.error(f"[-] Google API Failure: {str(api_error)}")
        return json.dumps({
            "status": "error",
            "message": f"Google Calendar write failed: {str(api_error)}"
        })
    
def update_google_calendar_event(search_summary: str, event_date_iso: str, updates: dict) -> str:
    """
    Finds an existing calendar event by title/date and updates its properties.
    :param search_summary: Keyword to look for (e.g., 'Unemployment')
    :param event_date_iso: The day the event is on (YYYY-MM-DD)
    :param updates: A dict containing fields to change, e.g., {'start_time_iso': '2026-06-21T14:00:00', 'duration_minutes': 60}
    """
    logger.info(f"[TOOL EXECUTION] Attempting to update event matching '{search_summary}' on {event_date_iso}")
    
    try:
        service = get_calendar_service()
        
        # 1. Define time boundaries for the search day (00:00:00 to 23:59:59)
        time_min = f"{event_date_iso}T00:00:00Z"
        time_max = f"{event_date_iso}T23:59:59Z"
        
        # 2. Query Google Calendar for events on that specific day
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            q=search_summary,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return json.dumps({"status": "error", "message": f"Could not find any events matching '{search_summary}' on {event_date_iso}."})
            
        # Target the first matching event found
        target_event = events[0]
        event_id = target_event['id']
        
        # 3. Apply updates to the existing event payload structure
        if 'new_summary' in updates:
            target_event['summary'] = updates['new_summary']
            
        if 'start_time_iso' in updates:
            start_dt = datetime.datetime.fromisoformat(updates['start_time_iso'])
            duration = int(updates.get('duration_minutes', 30))
            end_dt = start_dt + datetime.timedelta(minutes=duration)
            
            target_event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Chicago'}
            target_event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Chicago'}
            
        # 4. Push the modified resource bundle back to Google's servers
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=target_event
        ).execute()
        
        logger.info(f"[✓] Event update successfully synced! Link: {updated_event.get('htmlLink')}")
        return json.dumps({
            "status": "success",
            "message": f"Successfully updated '{target_event['summary']}' on your calendar."
        })
        
    except Exception as api_error:
        logger.error(f"[-] Update execution failure: {str(api_error)}")
        return json.dumps({"status": "error", "message": f"Failed to update calendar: {str(api_error)}"})

def list_google_calendar_events(date_iso: str) -> str:
    """
    Fetches all calendar entries for a specific date (YYYY-MM-DD).
    """
    logger.info(f"[TOOL EXECUTION] Reading daily agenda for date: {date_iso}")
    
    try:
        service = get_calendar_service()
        
        # Define boundaries for the targeted day (Local Central Time bounds converted to ISO)
        time_min = f"{date_iso}T00:00:00-05:00"  # Adjust offset if your local time changes
        time_max = f"{date_iso}T23:59:59-05:00"
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return json.dumps({
                "status": "success",
                "message": f"Your calendar is completely empty for {date_iso}. You have no events scheduled."
            })
            
        agenda_items = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            # Format time for clean reading if it contains a timestamp
            if 'T' in start_time:
                time_part = start_time.split('T')[1][:5] # Grabs HH:MM
                display_time = f"{time_part}"
            else:
                display_time = "All Day"
                
            agenda_items.append(f"- {display_time}: {event.get('summary')}")
            
        agenda_summary = "\n".join(agenda_items)
        return json.dumps({
            "status": "success",
            "message": f"Here is your agenda for {date_iso}:\n{agenda_summary}"
        })
        
    except Exception as api_error:
        logger.error(f"[-] Fetch execution failure: {str(api_error)}")
        return json.dumps({
            "status": "error",
            "message": f"I couldn't read your calendar. Error details: {str(api_error)}"
        })        