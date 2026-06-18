# backend/agent.py
import openai
from tools.calendar_tool import create_google_calendar_event

# 1. Define the tool configuration details so the LLM knows it exists
tools_manifest = [
    {
        "type": "function",
        "function": {
            "name": "quick_add_calendar_event",
            "description": "Create a new event or appointment on the user's Google Calendar. Use this whenever the user asks to schedule, book, set up, or add something to their calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "The title or purpose of the meeting."},
                    "start_time_iso": {"type": "string", "description": "The explicit ISO timestamp for the start of the event (YYYY-MM-DDTHH:MM:SS)."},
                    "duration_minutes": {"type": "integer", "description": "The length of the event in minutes. Defaults to 30 if unstated."}
                },
                "required": ["summary", "start_time_iso"]
            }
        }
    }
]

def run_assistant_agent_loop(user_message: str):
    # Standard system instructions defining its persona
    system_instruction = f"You are a helpful personal executive assistant. The current date and time is {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}."

    # First LLM Call: Pass the message AND the tools manifest
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message}
        ],
        tools=tools_manifest,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Check if the LLM decided it needs to run a calendar tool
    if tool_calls:
        print("Agent analyzed intent: Triggering Google Calendar Action...")
        
        for tool_call in tool_calls:
            if tool_call.function.name == "quick_add_calendar_event":
                # Parse the arguments the LLM extracted from your text
                args = json.loads(tool_call.function.arguments)
                
                # Execute your Python function!
                action_result = create_google_calendar_event(
                    summary=args.get("summary"),
                    start_time_iso=args.get("start_time_iso"),
                    duration_minutes=args.get("duration_minutes", 30)
                )
                
                # Hand the result back to the LLM so it can talk to you conversationally
                final_response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_message},
                        response_message,
                        {"role": "tool", "tool_call_id": tool_call.id, "name": "quick_add_calendar_event", "content": action_result}
                    ]
                )
                return final_response.choices[0].message.content
                
    # If no tool was needed, just return its normal conversational response
    return response_message.content