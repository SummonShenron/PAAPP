import os
import json
import logging

logger = logging.getLogger("SASS Logger")
NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sticky_notes.json")

def _load_notes() -> dict:
    """Helper to safely read notes from the JSON file."""
    if not os.path.exists(NOTES_FILE):
        return {}
    try:
        with open(NOTES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_notes(notes: dict):
    """Helper to write notes back to the JSON file."""
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=4)

def add_sticky_note(key: str, content: str) -> str:
    """Saves or appends a custom sticky note or task."""
    logger.info(f"[TOOL EXECUTION] Writing sticky note: '{key}'")
    notes = _load_notes()
    notes[key.lower().strip()] = {
        "title": key,
        "content": content
    }
    _save_notes(notes)
    return json.dumps({
        "status": "success",
        "message": f"I've pinned that sticky note under '{key}': \"{content}\""
    })

def read_sticky_notes(search_key: str = None) -> str:
    """Reads all sticky notes or searches for a specific note."""
    logger.info(f"[TOOL EXECUTION] Searching sticky notes for key: {search_key}")
    notes = _load_notes()
    
    if not notes:
        return json.dumps({"status": "success", "message": "Your local sticky board is currently empty."})
        
    if search_key:
        match = notes.get(search_key.lower().strip())
        if match:
            return json.dumps({
                "status": "success",
                "message": f"Found your note on '{match['title']}': \"{match['content']}\""
            })
        return json.dumps({
            "status": "error",
            "message": f"I couldn't find any sticky notes matching '{search_key}'."
        })
        
    # Return all notes formatted
    summary = "\n".join([f"- **{note['title']}**: {note['content']}" for note in notes.values()])
    return json.dumps({
        "status": "success",
        "message": f"Here are your active sticky notes:\n{summary}"
    })

def clear_sticky_note(key: str) -> str:
    """Deletes a note/task from your sticky board."""
    logger.info(f"[TOOL EXECUTION] Clearing sticky note: '{key}'")
    notes = _load_notes()
    target_key = key.lower().strip()
    
    if target_key in notes:
        deleted = notes.pop(target_key)
        _save_notes(notes)
        return json.dumps({
            "status": "success",
            "message": f"Successfully removed the sticky note for '{deleted['title']}'."
        })
    return json.dumps({"status": "error", "message": f"No sticky note found matching '{key}' to clear."})

