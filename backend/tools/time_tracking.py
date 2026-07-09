import re
import datetime
import uuid
from pydantic import BaseModel


class TimeEntry(BaseModel):
    id: str
    activity: str
    duration_minutes: int
    date: str          # "YYYY-MM-DD"
    created_at: str    # ISO timestamp
    notes: str | None = None

def log_time(activity: str, minutes: int, date_iso: str, notes: str = ""):
    message = (
        f"I've logged {minutes} minutes of {activity} for {date_iso}."
        if minutes < 60 else
        f"I've logged {minutes // 60} hour(s) of {activity} for {date_iso}."
    )

    if notes:
        message += f" Notes: {notes}"

    return {"message": message}


def extract_time_fields(msg: str):
    msg = msg.lower()

    # Minutes
    h = re.search(r"(\d+)\s*hour", msg)
    m = re.search(r"(\d+)\s*minute", msg)

    if h:
        minutes = int(h.group(1)) * 60
    elif m:
        minutes = int(m.group(1))
    else:
        minutes = None

    # Activity
    activity_match = re.search(
        r"(?:\d+\s*(?:hour|hours|minute|minutes))(?:\s*(?:of|for))?\s+(.+)", msg
    )
    activity = activity_match.group(1).strip() if activity_match else msg

    # Date
    date_iso = datetime.datetime.utcnow().date().isoformat()

    return activity, minutes, date_iso
TIME_ENTRIES: list[TimeEntry] = []

def log_time_internal(activity: str, minutes: int, date_iso: str, notes: str | None = None):
    entry = TimeEntry(
        id=str(uuid.uuid4()),
        activity=activity,
        duration_minutes=minutes,
        date=date_iso,
        created_at=datetime.datetime.utcnow().isoformat(),
        notes=notes
    )
    TIME_ENTRIES.append(entry)
    return entry
