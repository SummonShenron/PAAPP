🔮 Imperium Cockpit: Local Personal Assistant Core

A high-performance, private, localized AI assistant dashboard designed to manage your schedule, organize sticky tasks, and act as an offline brain. Powered by Ollama (Llama 3) and FastAPI, with real-time Google Calendar integration, client-side persistence, and custom styling inspired by the Arcosian Light and Imperium Dark aesthetics.

🚀 Key Features

Real-Time Google Calendar Synchronization:

Create Events: Schedule appointments via natural language (e.g., "Schedule coding block Sunday at 3 PM").

Update Events: Modify titles, descriptions, and times dynamically.

List Agenda: View your authentic daily timeline with absolute zero hallucinations.

Local Sticky Note Manager: A lightweight database (sticky_notes.json) allowing you to pin critical facts, tasks, passwords, or codes that the assistant can reference instantly.

Persistent Session Recovery:

Backend Serialization: Raw LangChain message classes (HumanMessage, AIMessage, SystemMessage) are dynamically translated and saved on disk (chat_history.json), surviving server restarts.

Client Persistence: Frontend chat histories are securely bound to individual logged-in operators in localStorage, surviving refreshes and session restarts.

Robust Intent Classification: Custom backend JSON-stripping regex handler ensures LLM-driven actions run flawlessly even if Llama 3 wraps its payloads in markdown backticks or introductory text.

Interactive Sandbox Bypass: Automatically falls back to offline sandbox mode on the frontend if the local backend server is temporarily shut down, keeping the UI fully interactive.

🛠️ Project Architecture

local_agent/                  # Root Project Directory
├── app.py                    # Main Server, Intent Router & Streaming Engine
├── directory.json            # Identity Security Profile Registry
├── chat_history.json         # Saved Local Conversations (Auto-Generated)
├── backend/                  # Local Action Tool Modules
│   └── tools/                
│       ├── calendar_tool.py  # Google Calendar API Client
│       ├── notes_tool.py     # Local Task/Sticky Note Database
│       └── sticky_notes.json # Active Sticky Notes (Auto-Generated)
└── local/                    # React Frontend Application (Pure JS/TS Environment)
    ├── public/               # Static Web Assets
    └── src/                  # React Source Code
        ├── assets/           # UI Images and Gifs
        ├── components/       # Interface Elements
        ├── pages/            # View Templates
        │   ├── Chat.tsx      # Persistent Chat Interface with Frieza Style
        │   └── LandingPage.tsx # Identity Gateway & Sandbox Auto-Bypass
        ├── api.ts            # Frontend API Connection Layer
        └── index.css         # Theme Styles & CSS Variables



💻 Prerequisites & Setup

1. Local LLM (Ollama)

Ensure you have Ollama installed and running locally on your workstation, then pull the required model:

ollama pull llama3


2. Google Calendar API Integration

To connect your assistant to your real-world calendar:

Go to the Google Cloud Console.

Create a new project, enable the Google Calendar API, and generate an OAuth 2.0 Client ID.

Download the client credentials JSON, rename it to credentials.json, and place it in your backend/ folder.

On your first calendar tool interaction, the Python backend will prompt you in the terminal to authorize the app through your browser, generating a persistent local token file.

3. Backend Setup

Set up your isolated Python virtual environment and launch your API gateway:

# Navigate to the backend folder
cd backend

# Create & activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate

# Install dependencies (Uvicorn, FastAPI, Langchain, Google API Client)
pip install fastapi uvicorn pydantic langchain langchain-community google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Run the live, hot-reloading development server
uvicorn app:app --host 12000 --port 8000 --reload


4. Frontend Setup

Launch the React interface:

# Navigate to the React frontend directory
cd local

# Install packages
npm install

# Boot up the development server
npm run dev


📋 Conversation Logs & Commands

Your Llama 3 model is instructed to parse these structures contextually. You can try typing these exact prompts into the Cockpit chat:

Sticky Notes

Save Information: "Remember that my entry gate code is 9981"

Retrieve Facts: "What was my gate code again?"

List Sticky Board: "Show me all of my sticky notes"

Clear Elements: "Delete the sticky note about my gate code"

Google Calendar

Create Appointment: "Add a Coding Session for today at 3:00 PM"

Change Appointment: "Move my coding session to tomorrow at 5:00 PM"

Check Schedule: "What do I have on my schedule today?"

🎨 Theme Configuration

To swap between the Arcosian Light theme and the Imperium Dark theme, simply click the "Hero / Dark" selector button in the top navigation bar. Theme configurations are automatically saved to your browser session's local storage properties, preventing style resets on refresh!