import asyncio
import os
import datetime
import json
import logging
import sys
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Conversational LLM Core
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# Authenticated Calendar Tools
from backend.tools.calendar_tool import (
    create_google_calendar_event,
    update_google_calendar_event,
    list_google_calendar_events
)
from backend.tools.notes_tool import add_sticky_note, read_sticky_notes, clear_sticky_note
from backend.tools.time_tracking import TimeEntry, log_time_internal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DIRECTORY_FILE = os.path.join(BASE_DIR, "directory.json")
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app = FastAPI(title="Headless PAAPP API")
logger = logging.getLogger("SASS Logger")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Conversational Engine (Ollama Llama3)
logger.info("[*] Waking up conversational agent core engine (Ollama Llama3)...")
llm = Ollama(model="llama3")


def save_chat_history():
    """Serializes LangChain message objects to raw JSON dicts and writes to disk."""
    serialized = {}
    for user, messages in chat_sessions.items():
        msg_list = []
        for msg in messages:
            # Map Python classes to clean string labels
            if isinstance(msg, HumanMessage):
                msg_type = "human"
            elif isinstance(msg, AIMessage):
                msg_type = "ai"
            elif isinstance(msg, SystemMessage):
                msg_type = "system"
            else:
                continue
            msg_list.append({"type": msg_type, "content": msg.content})
        serialized[user] = msg_list

    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(serialized, f, indent=4)
        logger.info("[✓] Stateful chat history backed up to local memory.")
    except Exception as e:
        logger.error(f"[-] Failed to write chat history backup: {e}")

def load_chat_history() -> dict:
    """Reads local JSON history and reconstructs live LangChain message class objects."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            raw_data = json.load(f)
        
        sessions = {}
        for user, msg_list in raw_data.items():
            messages = []
            for msg in msg_list:
                m_type = msg.get("type")
                content = msg.get("content", "")
                
                # Reconstruct classes on backend load
                if m_type == "human":
                    messages.append(HumanMessage(content=content))
                elif m_type == "ai":
                    messages.append(AIMessage(content=content))
                elif m_type == "system":
                    messages.append(SystemMessage(content=content))
            sessions[user] = messages
        
        logger.info(f"[✓] Restored stateful sessions for {len(sessions)} profiles from disk.")
        return sessions
    except Exception as e:
        logger.error(f"[-] Failed to restore session history: {e}")
        return {}
# In-Memory Session Storage for Chat History
chat_sessions = load_chat_history()
if not os.path.exists(USER_DIRECTORY_FILE):
    raise RuntimeError(f"Could not find required security directory profile file: {USER_DIRECTORY_FILE}")
with open(USER_DIRECTORY_FILE, "r") as f:
    user_directory = json.load(f)

class LoginRequest(BaseModel):
    username: str

@app.post("/api/login")
async def verify_identity_profile(payload: LoginRequest):
    username = payload.username.strip()
    if username not in user_directory:
        raise HTTPException(status_code=401, detail="Unauthorized profile claims.")
    return {"status": "authenticated", "principal": username}

class ChatRequest(BaseModel):
    username: str
    question: str

def clean_and_parse_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx + 1]
    return json.loads(text)

async def simulate_token_stream(full_text: str, delay: float = 0.01):
    """
    Slices a static string into individual characters and streams them 
    dynamically to the frontend to maintain progressive token-streaming behaviors.
    """
    for char in full_text:
        yield char
        await asyncio.sleep(delay)

# --- MAIN STREAMING CHAT COCKPIT ENDPOINT ---
@app.post("/api/headless-chat")
async def secure_chat(request: ChatRequest, x_saapp: str | None = Header(default=None)):    
    username = request.username.strip()
    question = request.question.strip()
    is_saapp = (x_saapp == "true")
    if username not in chat_sessions:
        chat_sessions[username] = []  
    if len(chat_sessions[username]) > 10:
        chat_sessions[username] = chat_sessions[username][-10:]
    today_dt = datetime.datetime.now()
    days_until_sunday = (6 - today_dt.weekday()) % 7
    this_sunday_dt = today_dt + datetime.timedelta(days=days_until_sunday)
    tomorrow_dt = today_dt + datetime.timedelta(days=1)

    router_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a strict backend intent routing component for Jack's personal cockpit. 

TIMELINE CHEAT SHEET:
- CURRENT TIMESTAMP: {today_dt.strftime('%A, %B %d, %Y at %I:%M %p')}
- TODAY'S DATE: {today_dt.strftime('%Y-%m-%d')}
- TOMORROW'S DATE: {tomorrow_dt.strftime('%Y-%m-%d')}
- THIS SUNDAY'S DATE: {this_sunday_dt.strftime('%Y-%m-%d')}

CRITICAL: Choose exactly ONE of the four JSON options below. Do not include any introductory remarks, explanations, or conversational preamble. Output strictly RAW JSON.

OPTION 1: Add or schedule a brand new event.
Format:
{{"action": "call_tool", "tool": "create_google_calendar_event", "summary": "Title", "start_time_iso": "YYYY-MM-DDTHH:MM:SS", "duration_minutes": 30}}

OPTION 2: Reschedule, move, or modify an existing event.
Format:
{{"action": "call_tool", "tool": "update_google_calendar_event", "search_summary": "Old Title Key", "event_date_iso": "YYYY-MM-DD", "updates": {{"start_time_iso": "YYYY-MM-DDTHH:MM:SS", "duration_minutes": 60}}}}

OPTION 3: Check, view, list, see, or read events on their calendar for a specific date.
Format:
{{"action": "call_tool", "tool": "list_google_calendar_events", "event_date_iso": "YYYY-MM-DD"}}

OPTION 4: General conversational greeting, chat follow-up, or standard non-calendar question.
Format:
{{"action": "run_chat"}}
<|eot_id|><|start_header_id|>user<|end_header_id|>
User Query: "{question}"
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

OPTION 5: Save or remember a sticky note, code, password, task, or fact.
Format:
{{"action": "call_tool", "tool": "add_sticky_note", "key": "Note Title", "content": "Note detail or task here"}}

OPTION 6: Read, view, list, or find sticky notes, todo list, or facts.
Format:
{{"action": "call_tool", "tool": "read_sticky_notes", "search_key": "Optional Note Title Key or empty string to list all"}}

OPTION 7: Delete, clear, or remove a sticky note or task.
Format:
{{"action": "call_tool", "tool": "clear_sticky_note", "key": "Note Title to remove"}}

OPTION 8: Log or track time spent on an activity.
Format:
{{"action": "call_tool", "tool": "log_time", "activity": "...", "minutes": 60, "date_iso": "...", "notes": "Description goes here"}}

CRITICAL ROUTING OVERRIDE:
If the user message begins with "log", "track", or "record", ALWAYS choose OPTION 8 (log_time).
This rule overrides all calendar heuristics, even if the message contains words like "call", "phone", "meeting", "with", or "today".

MANDATORY FIELD RULES FOR OPTION 8:
When choosing OPTION 8, ALWAYS include:
- "activity": extracted from the user message
- "minutes": extracted from the user message
- "date_iso": TODAY'S DATE unless the user explicitly specifies another date

NEVER omit "date_iso". It is required.

Examples:
- "log 1 hour of talking on the phone for today"
- "track 30 minutes of debugging"
- "record 2 hours of cleaning"
"""

    try:
        router_response = llm.invoke(router_prompt)
        intent = clean_and_parse_json(router_response)
        logger.info(f"[+] Evaluated routing classification: {intent}")
    except Exception as e:
        logger.warning(f"[-] Router bypass triggered: {e}. Defaulting to standard chat.")
        intent = {"action": "run_chat"}

    action_type = intent.get("action")
    tool_name = intent.get("tool")

    # --- PATTERN A: STREAM TOOL - CREATE EVENT ---
    if action_type == "call_tool" and tool_name == "create_google_calendar_event":
        tool_result = create_google_calendar_event(
            username=username,
            summary=intent.get("summary", "Appointment"),
            start_time_iso=intent.get("start_time_iso"),
            duration_minutes=intent.get("duration_minutes", 30)
        )
        parsed_res = json.loads(tool_result)
        formatted_msg = f"**Calendar Scheduled**\n\n{parsed_res['message']}"
        
        chat_sessions[username].append(HumanMessage(content=question))
        chat_sessions[username].append(AIMessage(content=formatted_msg))
        save_chat_history()
        if is_saapp:
            return {"message": formatted_msg}
        return StreamingResponse(simulate_token_stream(formatted_msg), media_type="text/plain")

    # --- PATTERN B: STREAM TOOL - UPDATE EVENT ---
    elif action_type == "call_tool" and tool_name == "update_google_calendar_event":
        tool_result = update_google_calendar_event(
            search_summary=intent.get("search_summary"),
            event_date_iso=intent.get("event_date_iso"),
            updates=intent.get("updates", {})
        )
        parsed_res = json.loads(tool_result)
        formatted_msg = f"**Calendar Updated**\n\n{parsed_res['message']}"
        
        chat_sessions[username].append(HumanMessage(content=question))
        chat_sessions[username].append(AIMessage(content=formatted_msg))
        save_chat_history()
        if is_saapp:
            return {"message": formatted_msg}
        return StreamingResponse(simulate_token_stream(formatted_msg), media_type="text/plain")

    # --- PATTERN C: STREAM TOOL - LIST AGENDA ---
    elif action_type == "call_tool" and tool_name == "list_google_calendar_events":
        tool_result = list_google_calendar_events(
            date_iso=intent.get("event_date_iso", today_dt.strftime('%Y-%m-%d'))
        )
        parsed_res = json.loads(tool_result)
        formatted_msg = f"**Calendar Agenda**\n\n{parsed_res['message']}"
        
        chat_sessions[username].append(HumanMessage(content=question))
        chat_sessions[username].append(AIMessage(content=formatted_msg))
        save_chat_history()
        if is_saapp:
            return {"message": formatted_msg}
        return StreamingResponse(simulate_token_stream(formatted_msg), media_type="text/plain")

    # --- PATTERN D: STREAM TOOL - LOG TIME ---
    elif action_type == "call_tool" and tool_name == "log_time":
        activity = intent.get("activity")
        minutes = intent.get("minutes")
        date_iso = intent.get("date_iso")
        notes = intent.get("notes")

        formatted_msg = (
            f"**Time Logged**\n\n"
            f"- Activity: {activity}\n"
            f"- Duration: {minutes} minutes\n"
            f"- Date: {date_iso}"
        )

        chat_sessions[username].append(HumanMessage(content=question))
        chat_sessions[username].append(AIMessage(content=formatted_msg))
        save_chat_history()

        return {
            "message": formatted_msg,
            "intent": intent
        }

        # return StreamingResponse(simulate_token_stream(formatted_msg), media_type="text/plain")
    
    # --- PATTERN E: NATIVE CONVERSATIONAL TOKEN STREAMER ---
    elif action_type == "run_chat":
        chat_template = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Jack's dedicated personal assistant companion. You are helpful, adaptive, concise, and professional.\n"
                "CRITICAL: Do NOT invent fake calendar events, meetings, or company names under any circumstances. "
                "If asked about what's on the schedule, rely strictly on previous tool entries found in the conversation logs. "
                "Otherwise, answer normally and ask how you can help."
            )),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}")
        ])
        
        chat_chain = chat_template | llm | StrOutputParser()
    
        # SAAPP MODE — synchronous, return JSON
        if is_saapp:
            full_response = chat_chain.invoke({
                "history": chat_sessions[username],
                "question": question
            })

            chat_sessions[username].append(HumanMessage(content=question))
            chat_sessions[username].append(AIMessage(content=full_response))
            save_chat_history()

            return {"message": full_response}

        # FRONTEND MODE — streaming
        async def token_streamer():
            full_response = ""
            try:
                async for chunk in chat_chain.astream({
                    "history": chat_sessions[username],
                    "question": question
                }):
                    full_response += chunk
                    yield chunk

                chat_sessions[username].append(HumanMessage(content=question))
                chat_sessions[username].append(AIMessage(content=full_response))
                save_chat_history()

            except Exception as e:
                logger.error(f"[-] Conversational stream disruption: {str(e)}")
                yield f"\n[Agent Stream Error: {str(e)}]"

        return StreamingResponse(token_streamer(), media_type="text/plain")


    # --- PATTERN F: STREAM TOOL - READ STICKY NOTES ---
    elif action_type == "call_tool" and tool_name == "read_sticky_notes":
        tool_result = read_sticky_notes(
            search_key=intent.get("search_key")
        )
        parsed_res = json.loads(tool_result)
        formatted_msg = f"**Sticky Board**\n\n{parsed_res['message']}"
        
        chat_sessions[username].append(HumanMessage(content=question))
        chat_sessions[username].append(AIMessage(content=formatted_msg))
        save_chat_history()
        if is_saapp:
            return {"message": formatted_msg}
        return StreamingResponse(simulate_token_stream(formatted_msg), media_type="text/plain")

    # --- PATTERN G: STREAM TOOL - CLEAR STICKY NOTE ---
    elif action_type == "call_tool" and tool_name == "clear_sticky_note":
        tool_result = clear_sticky_note(
            key=intent.get("key", "")
        )
        parsed_res = json.loads(tool_result)
        formatted_msg = f"**Sticky Removed**\n\n{parsed_res['message']}"
        
        chat_sessions[username].append(HumanMessage(content=question))
        chat_sessions[username].append(AIMessage(content=formatted_msg))
        save_chat_history()
        if is_saapp:
            return {"message": formatted_msg}
        return StreamingResponse(simulate_token_stream(formatted_msg), media_type="text/plain")
    
class SAAPPEvent(BaseModel):
    username: str
    activity: str
    start_time: str
    date: str
    notes: str | None = ""
    type: str


@app.post("/api/saapp/event")
async def saapp_create_event(payload: SAAPPEvent):
    start_iso = f"{payload.date}T{payload.start_time}:00"

    result = create_google_calendar_event(
        username=payload.username,
        summary=payload.activity,
        start_time_iso=start_iso,
        duration_minutes=30
    )

    return json.loads(result)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}