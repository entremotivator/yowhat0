import streamlit as st
import pandas as pd
import requests
import json
import uuid
import speech_recognition as sr
from gtts import gTTS
import os
import base64
import tempfile
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pickle
from pathlib import Path
# Removed google_auth_oauthlib.flow as it seems service account is preferred
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Multi-Agent Business Dashboard", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants & Configuration ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar"
]

# Placeholder for spreadsheet IDs - Should be configured via UI or secrets
REAL_SPREADSHEETS = {
    "Grant": {
        "id": "1t80HNEgDIBFElZqodlvfaEuRj-bPlS4-R8T9kdLBtFk",
        "name": "Grant Information",
        "description": "Grant application and funding data",
        "icon": "📊"
    },
    "Real Estate": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y",
        "name": "Real Estate Properties",
        "description": "Property listings and details",
        "icon": "🏠"
    },
    "Agent": {
        "id": "1Om-RVVChe1GItsY4YaN_K95iM44vTpoxpSXzwTnOdAo",
        "name": "Agent Information",
        "description": "Agent profiles and performance metrics",
        "icon": "👤"
    }
}

# Load Agent Configuration from JSON file if exists, otherwise use default
AGENT_CONFIG_FILE = "agents_config.json"
DEFAULT_AGENTS_CONFIG = {
    "Agent_CEO": {
        "id": "agent_ceo_default_id", # Use unique IDs
        "name": "Agent CEO",
        "description": "Executive leadership and strategic decision making",
        "icon": "👔",
        "webhook_url_key": "WEBHOOK_URL", # Reference secret key
        "bearer_token_key": "BEARER_TOKEN", # Reference secret key
        "ai_phone": "+15551000001",
        "ai_assistant_id": "bf161516-6d88-490c-972e-274098a6b51a",
        "category": "Leadership",
        "specialization": "Strategic Planning, Executive Decisions, Leadership",
        "spreadsheet_key": "Agent" # Reference REAL_SPREADSHEETS key
    },
    # Add other default agents here...
    "STREAMLIT_Agent": {
        "id": "streamlit_agent_default_id",
        "name": "STREAMLIT Agent",
        "description": "Streamlit app development and Python coding",
        "icon": "🐍",
        "webhook_url_key": "WEBHOOK_URL",
        "bearer_token_key": "BEARER_TOKEN",
        "ai_phone": "+15551000011",
        "ai_assistant_id": "538258da-0dda-473d-8ef8-5427251f3ad5",
        "category": "Development",
        "specialization": "Streamlit, Python, Web Apps",
        "spreadsheet_key": "Agent"
    },
}

def load_config(file_path, default_config):
    """Load configuration from a JSON file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading config file {file_path}: {e}")
            return default_config
    return default_config

AGENTS_CONFIG = load_config(AGENT_CONFIG_FILE, DEFAULT_AGENTS_CONFIG)

# --- Secrets Management ---
def get_secret(key, default=None):
    """Safely retrieve secrets."""
    return st.secrets.get(key, default)

# --- Session State Initialization ---
def initialize_session_state():
    """Initialize Streamlit session state variables."""
    defaults = {
        "authenticated": False,
        "credentials": None,
        "user_info": None,
        "current_page": list(AGENTS_CONFIG.keys())[0] if AGENTS_CONFIG else None, # Default to first agent
        "current_tab": "chatbot",
        "sheets_data": {},
        "chat_sessions": {},
        "recognizer": None, # Initialize later if needed
        "use_tts": True,
        "show_timestamps": False,
        "recording_status": False,
        "vapi_settings": {
            "api_key": get_secret("VAPI_API_KEY"),
            "endpoint": get_secret("VAPI_ENDPOINT", "https://api.vapi.ai/v1"),
            "enabled": bool(get_secret("VAPI_API_KEY")) # Enable if key exists
        },
        "agent_configs": AGENTS_CONFIG,
        "prompt_library": {},
        "google_auth_error": None,
        "google_creds_uploaded": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
            
    # Initialize recognizer if not already done
    if st.session_state.recognizer is None:
        try:
            st.session_state.recognizer = sr.Recognizer()
        except Exception as e:
            st.warning(f"Could not initialize Speech Recognition: {e}")

initialize_session_state()

# --- Authentication Functions ---
def authenticate_google_with_json(creds_info):
    """Authenticate Google services using service account JSON info."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=SCOPES
        )
        # Optionally, check if credentials are valid (e.g., by making a simple API call)
        gc = gspread.authorize(credentials)
        gc.list_spreadsheet_files() # Test call
        
        st.session_state.credentials = credentials
        st.session_state.authenticated = True
        st.session_state.user_info = {"name": creds_info.get("client_email", "Service Account"), "email": creds_info.get("client_email")}
        st.session_state.google_auth_error = None
        st.session_state.google_creds_uploaded = True
        st.success("Google Authentication Successful!")
        return True
    except Exception as e:
        st.session_state.authenticated = False
        st.session_state.credentials = None
        st.session_state.google_auth_error = f"Google Auth Error: {e}"
        st.error(st.session_state.google_auth_error)
        return False

# --- Helper Functions ---
def get_agent_config(agent_key):
    """Get agent configuration safely."""
    return st.session_state.agent_configs.get(agent_key)

def format_timestamp(timestamp):
    """Format timestamp for chat messages."""
    if not st.session_state.get("show_timestamps", False):
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return f"[{dt.strftime("%H:%M:%S")] "
    except:
        return ""

def text_to_speech(text):
    """Convert text to speech using gTTS."""
    if not st.session_state.get("use_tts", False) or not text:
        return None
    
    try:
        tts = gTTS(text=text, lang="en", slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"TTS Error: {e}")
        return None

def autoplay_audio(file_path):
    """Autoplay audio file in Streamlit."""
    if file_path is None or not os.path.exists(file_path):
        return
    
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_tag = f'<audio autoplay="true" src="data:audio/mp3;base64,{audio_base64}"></audio>'
        st.markdown(audio_tag, unsafe_allow_html=True)
        
        # Optional: Clean up the file immediately or schedule cleanup
        # Using a small delay before removing might help ensure playback starts
        time.sleep(0.5) 
        os.remove(file_path)
    except Exception as e:
        # Don't necessarily show error to user, could be transient
        print(f"Audio playback/cleanup error: {e}") 
        # If file still exists, try removing again
        if os.path.exists(file_path):
             try: os.remove(file_path)
             except: pass

def speech_to_text():
    """Convert speech to text using speech_recognition."""
    recognizer = st.session_state.get("recognizer")
    if not recognizer or not st.session_state.get("recording_status", False):
        return None
        
    try:
        with sr.Microphone() as source:
            st.info("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        st.info("Processing...")
        text = recognizer.recognize_google(audio)
        st.success("Speech recognized!")
        return text
    except sr.WaitTimeoutError:
        st.warning("No speech detected within timeout.")
    except sr.UnknownValueError:
        st.warning("Could not understand audio.")
    except sr.RequestError as e:
        st.error(f"Could not request results from Google Speech Recognition service; {e}")
    except Exception as e:
        st.error(f"STT Error: {e}")
    finally:
        st.session_state.recording_status = False # Ensure status is reset
    return None

def send_message_to_agent(agent_config, message):
    """Send message to the configured agent webhook."""
    if not message or not agent_config:
        return None

    webhook_url = get_secret(agent_config.get("webhook_url_key"))
    bearer_token = get_secret(agent_config.get("bearer_token_key"))

    if not webhook_url or not bearer_token:
        st.error(f"Webhook URL or Bearer Token not configured in secrets for agent {agent_config.get("name")}.")
        return None

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}"
        }
        
        payload = {
            "message": message,
            "agent_id": agent_config.get("id"),
            "user_id": st.session_state.user_info.get("email") if st.session_state.user_info else "anonymous",
            # Add any other relevant context if needed by the webhook
        }
        
        with st.spinner(f"Sending message to {agent_config.get("name")}..."):
            response = requests.post(
                webhook_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=60 # Add a timeout
            )
        
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        return response.json()

    except requests.exceptions.Timeout:
        st.error(f"API request timed out after 60 seconds.")
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        
    return None

# --- VAPI Functions (Placeholder - Requires VAPI SDK/Library or direct API calls) ---
def process_vapi_call(agent_config, message):
    """Initiate a VAPI call (Placeholder)."""
    vapi_settings = st.session_state.get("vapi_settings", {})
    if not vapi_settings.get("enabled") or not message or not agent_config:
        return None
        
    api_key = vapi_settings.get("api_key")
    endpoint = vapi_settings.get("endpoint")
    assistant_id = agent_config.get("ai_assistant_id")
    phone_number = agent_config.get("ai_phone")

    if not api_key or not endpoint or not assistant_id or not phone_number:
        st.warning("VAPI settings or agent VAPI config missing.")
        return None

    st.info(f"Initiating VAPI call to {phone_number} for assistant {assistant_id} (Implementation Pending)")
    # Replace with actual VAPI API call logic using requests or VAPI library
    # Example using requests:
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = { 
            "assistantId": assistant_id, 
            "phoneNumberId": phone_number, # Adjust payload based on VAPI docs
            # Add other necessary parameters like first message, etc.
        }
        # response = requests.post(f"{endpoint}/call/phone", headers=headers, json=payload, timeout=30)
        # response.raise_for_status()
        # call_data = response.json()
        # call_id = call_data.get("id")
        # st.session_state.vapi_calls[call_id] = { ... } # Store call info
        # return call_id
        st.warning("VAPI call initiation logic not fully implemented.")
        return None # Placeholder return
    except Exception as e:
        st.error(f"VAPI Call Error: {e}")
        return None

def get_vapi_call_status(call_id):
    """Get VAPI call status (Placeholder)."""
    # Implementation needed to query VAPI for call status
    st.info(f"Checking VAPI call status for {call_id} (Implementation Pending)")
    return None

# --- Chat Functions ---
def get_chat_history(agent_id):
    """Retrieve chat history for a specific agent."""
    if agent_id not in st.session_state.chat_sessions:
        st.session_state.chat_sessions[agent_id] = []
    return st.session_state.chat_sessions[agent_id]

def add_message_to_chat(agent_id, role, content):
    """Add a message to the agent's chat history."""
    if agent_id not in st.session_state.chat_sessions:
        st.session_state.chat_sessions[agent_id] = []
    
    message = {
        "role": role, # "user" or "assistant"
        "content": content,
        "timestamp": datetime.now().timestamp()
    }
    
    st.session_state.chat_sessions[agent_id].append(message)
    # Limit history size if needed
    # MAX_HISTORY = 50
    # st.session_state.chat_sessions[agent_id] = st.session_state.chat_sessions[agent_id][-MAX_HISTORY:]
    return message

def clear_chat_history(agent_id):
    """Clear chat history for a specific agent."""
    if agent_id in st.session_state.chat_sessions:
        st.session_state.chat_sessions[agent_id] = []
        st.success("Chat history cleared.")

# --- Google Sheets Functions ---
def get_sheets_data(spreadsheet_id, worksheet_name=None):
    """Get data from a specific Google Sheet and optionally a worksheet."""
    credentials = st.session_state.get("credentials")
    if not credentials:
        st.warning("Google Sheets: Not authenticated.")
        return None

    # Use cached data if available and worksheet specified
    if worksheet_name and spreadsheet_id in st.session_state.sheets_data and worksheet_name in st.session_state.sheets_data[spreadsheet_id]:
         return st.session_state.sheets_data[spreadsheet_id]

    try:
        with st.spinner(f"Loading data from Google Sheet {spreadsheet_id}..."):
            gc = gspread.authorize(credentials)
            spreadsheet = gc.open_by_key(spreadsheet_id)
            
            sheets_data = {}
            worksheets_to_load = [worksheet_name] if worksheet_name else [ws.title for ws in spreadsheet.worksheets()]
            
            for ws_name in worksheets_to_load:
                try:
                    worksheet = spreadsheet.worksheet(ws_name)
                    # Consider using get_all_records for dictionary format or get_all_values
                    df = get_as_dataframe(worksheet, evaluate_formulas=True, skiprows=0, header=1)
                    df = df.dropna(how="all").dropna(axis=1, how="all") # Clean
                    if not df.empty:
                        sheets_data[ws_name] = df
                except gspread.exceptions.WorksheetNotFound:
                    st.warning(f"Worksheet ", {ws_name}, " not found in spreadsheet ", {spreadsheet_id})
                except Exception as e:
                    st.error(f"Error loading worksheet {ws_name}: {e}")
        
        # Update cache
        if spreadsheet_id not in st.session_state.sheets_data:
             st.session_state.sheets_data[spreadsheet_id] = {}
        st.session_state.sheets_data[spreadsheet_id].update(sheets_data)
        
        return st.session_state.sheets_data[spreadsheet_id]

    except gspread.exceptions.APIError as e:
         st.error(f"Google Sheets API Error: {e}. Check permissions and Sheet ID.")
    except Exception as e:
        st.error(f"Error loading spreadsheet {spreadsheet_id}: {e}")
    return None

def update_sheets_data(spreadsheet_id, worksheet_name, df):
    """Update data in a specific Google Sheet worksheet."""
    credentials = st.session_state.get("credentials")
    if not credentials:
        st.error("Google Sheets: Not authenticated.")
        return False
    
    if df is None or not isinstance(df, pd.DataFrame):
        st.error("Invalid data provided for update.")
        return False

    try:
        with st.spinner(f"Updating worksheet {worksheet_name}..."):
            gc = gspread.authorize(credentials)
            spreadsheet = gc.open_by_key(spreadsheet_id)
            
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                # Option to create worksheet if it doesn't exist
                st.info(f"Worksheet {worksheet_name} not found. Creating new worksheet.")
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=df.shape[0] + 10, cols=df.shape[1] + 5)
            
            # Clear existing content before writing? Optional, depends on desired behavior.
            # worksheet.clear()
            set_with_dataframe(worksheet, df, include_index=False, include_column_header=True, resize=True)
        
        # Update cache
        if spreadsheet_id in st.session_state.sheets_data:
            st.session_state.sheets_data[spreadsheet_id][worksheet_name] = df.copy() # Update cache with a copy
        
        st.success(f"Worksheet {worksheet_name} updated successfully!")
        return True
        
    except gspread.exceptions.APIError as e:
         st.error(f"Google Sheets API Error during update: {e}. Check permissions.")
    except Exception as e:
        st.error(f"Error updating spreadsheet {spreadsheet_id}: {e}")
    return False

# --- Data Processing & Analytics ---
def process_data(df):
    """Perform basic analysis on a DataFrame."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {"summary": {}, "trends": {}, "insights": ["No data to process."]}
    
    summary = {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "column_names": df.columns.tolist()
    }
    
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    trends = {}
    insights = []

    if not numeric_cols:
        insights.append("No numeric columns found for trend analysis.")
    else:
        insights.append(f"Found {len(numeric_cols)} numeric columns: {', '.join(numeric_cols)}")
        for col in numeric_cols:
            try:
                trends[col] = {
                    "mean": df[col].mean(),
                    "median": df[col].median(),
                    "min": df[col].min(),
                    "max": df[col].max(),
                    "std_dev": df[col].std()
                }
            except Exception as e:
                insights.append(f"Could not calculate trends for column '{col}': {e}")

    # Add more sophisticated insights based on data types, correlations, etc.
    # Example: Check for date/time columns
    datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    if datetime_cols:
        insights.append(f"Found {len(datetime_cols)} date/time columns: {', '.join(datetime_cols)}")

    return {"summary": summary, "trends": trends, "insights": insights}

# --- UI Rendering Functions ---
def render_sidebar():
    """Render the sidebar with authentication, agent selection, and settings."""
    with st.sidebar:
        st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=200) # Example logo
        st.title("Agent Dashboard")
        st.markdown("--- ")

        # --- Google Authentication Section ---
        st.subheader("🔒 Google Authentication")
        if not st.session_state.authenticated:
            uploaded_file = st.file_uploader(
                "Upload Google Service Account JSON", 
                type=["json"],
                key="google_creds_file",
                help="Upload the JSON key file for your Google Service Account to access Sheets/Drive."
            )
            if uploaded_file is not None:
                try:
                    creds_info = json.load(uploaded_file)
                    authenticate_google_with_json(creds_info)
                    # Rerun to update UI after successful auth
                    if st.session_state.authenticated:
                        st.rerun()
                except json.JSONDecodeError:
                    st.error("Invalid JSON file. Please upload a valid Google Service Account key file.")
                except Exception as e:
                    st.error(f"Error processing credentials file: {e}")
            
            if st.session_state.google_auth_error:
                st.error(st.session_state.google_auth_error)
        else:
            st.success(f"Authenticated as: {st.session_state.user_info["email"]}")
            if st.button("Logout Google", key="google_logout"):
                st.session_state.authenticated = False
                st.session_state.credentials = None
                st.session_state.user_info = None
                st.session_state.sheets_data = {} # Clear cached data on logout
                st.session_state.google_creds_uploaded = False
                st.rerun()
        
        st.markdown("--- ")

        # --- Agent Selection Section ---
        if st.session_state.authenticated:
            st.subheader("🤖 Select Agent")
            agent_configs = st.session_state.get("agent_configs", {})
            if not agent_configs:
                st.warning("No agents configured.")
                return

            # Group agents by category for better organization
            categories = {}
            for agent_key, config in agent_configs.items():
                category = config.get("category", "General")
                if category not in categories:
                    categories[category] = []
                categories[category].append((agent_key, config))

            # Display agents using expanders for categories
            for category, agents_in_category in sorted(categories.items()):
                with st.expander(f"{category} ({len(agents_in_category)})", expanded=True):
                    for agent_key, config in agents_in_category:
                        button_label = f"{config.get('icon', '')} {config.get('name', agent_key)}"
                        if st.button(button_label, key=f"agent_btn_{agent_key}", use_container_width=True):
                            st.session_state.current_page = agent_key
                            # Optionally reset current tab when switching agents
                            # st.session_state.current_tab = "chatbot" 
                            st.rerun()
            st.markdown("--- ")
        else:
            st.info("Please authenticate with Google to select an agent.")

        # --- General Settings Section ---
        st.subheader("⚙️ Settings")
        with st.expander("General Settings", expanded=False):
            st.checkbox("Enable Text-to-Speech", value=st.session_state.get("use_tts", True), key="use_tts")
            st.checkbox("Show Chat Timestamps", value=st.session_state.get("show_timestamps", False), key="show_timestamps")

        # --- VAPI Settings Section ---
        with st.expander("VAPI Settings", expanded=False):
            vapi_enabled = st.checkbox("Enable VAPI Calls", value=st.session_state.vapi_settings.get("enabled", False), key="vapi_enabled_chk")
            vapi_api_key = st.text_input("VAPI API Key", value=st.session_state.vapi_settings.get("api_key", ""), type="password", key="vapi_api_key_input", help="Get your API key from VAPI dashboard.")
            vapi_endpoint = st.text_input("VAPI Endpoint", value=st.session_state.vapi_settings.get("endpoint", "https://api.vapi.ai/v1"), key="vapi_endpoint_input")
            
            # Update VAPI settings in session state if changed
            if (vapi_enabled != st.session_state.vapi_settings.get("enabled") or
                vapi_api_key != st.session_state.vapi_settings.get("api_key") or
                vapi_endpoint != st.session_state.vapi_settings.get("endpoint")):
                
                st.session_state.vapi_settings = {
                    "enabled": vapi_enabled,
                    "api_key": vapi_api_key,
                    "endpoint": vapi_endpoint
                }
                # Optionally save to secrets or persistent storage if needed beyond session
                st.info("VAPI settings updated.")
                # No rerun needed unless UI depends immediately on this change

def render_agent_page(agent_key):
    """Render the main page content for the selected agent."""
    agent_config = get_agent_config(agent_key)
    
    if not agent_config:
        st.error(f"Agent configuration for '{agent_key}' not found.")
        # Maybe redirect to a default page or show a selection prompt
        st.session_state.current_page = list(AGENTS_CONFIG.keys())[0] if AGENTS_CONFIG else None
        st.rerun()
        return

    # Agent Header
    st.title(f"{agent_config.get('icon', '🤖')} {agent_config.get('name', 'Agent')}")
    st.caption(agent_config.get('description', ''))
    st.markdown("--- ")

    # Tabs for different functionalities
    tab_keys = ["Chatbot", "Data", "Analytics", "Agent Settings"]
    tabs = st.tabs(tab_keys)
    
    # Store current tab selection if needed for state persistence
    # selected_tab = st.radio("Select Tab", tab_keys, horizontal=True, label_visibility="collapsed")
    # st.session_state.current_tab = selected_tab

    with tabs[0]: # Chatbot Tab
        render_chatbot_tab(agent_config)
    
    with tabs[1]: # Data Tab
        render_data_tab(agent_config)
    
    with tabs[2]: # Analytics Tab
        render_analytics_tab(agent_config)
    
    with tabs[3]: # Settings Tab
        render_agent_settings_tab(agent_config)

def render_chatbot_tab(agent_config):
    """Render the chatbot interface for the agent."""
    st.header("💬 Chat")
    agent_id = agent_config.get("id")
    
    # Chat history display area
    chat_container = st.container()
    with chat_container:
        chat_history = get_chat_history(agent_id)
        if not chat_history:
            st.info(f"Start your conversation with {agent_config.get('name', 'the agent')}.")
        else:
            for msg in reversed(chat_history): # Display newest first
                timestamp_str = format_timestamp(msg["timestamp"])
                with st.chat_message(msg["role"]):
                    st.markdown(f"{timestamp_str}{msg['content']}")

    st.markdown("--- ")
    # Input area using st.chat_input for better UI
    prompt = st.chat_input(f"Message {agent_config.get('name', 'Agent')}...", key=f"chat_input_{agent_id}")

    # --- Input Handling --- 
    # TODO: Add voice input button next to chat input if possible/desired
    # Maybe use columns for text input and voice button side-by-side above chat_input
    # col1, col2 = st.columns([5,1])
    # with col1: user_input_text = st.text_input(...) 
    # with col2: if st.button("🎤"): ...
    
    if prompt:
        # 1. Add user message to chat history and display
        add_message_to_chat(agent_id, "user", prompt)
        
        # 2. Send message to agent (webhook)
        # Display thinking indicator
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response_data = send_message_to_agent(agent_config, prompt)
        
        # 3. Process response
        if response_data and isinstance(response_data, dict):
            agent_message = response_data.get("message", "Agent did not provide a message.")
            # Add agent response to chat history
            add_message_to_chat(agent_id, "assistant", agent_message)
            
            # Text-to-speech for agent response
            audio_file = text_to_speech(agent_message)
            if audio_file:
                autoplay_audio(audio_file)
        elif response_data:
             # Handle non-dict responses if applicable
             add_message_to_chat(agent_id, "assistant", str(response_data))
        else:
            # Keep the spinner message or replace it with an error
            # The error is likely already shown by send_message_to_agent
            # We might add a generic failure message here if needed.
            # add_message_to_chat(agent_id, "assistant", "Sorry, I encountered an error.")
            pass # Error already displayed
            
        # Rerun to update the chat display immediately after processing
        st.rerun()

    # Add Clear Chat button (optional, could be in settings)
    if st.button("Clear Chat History", key=f"clear_chat_{agent_id}"):
        clear_chat_history(agent_id)
        st.rerun()
        
    # VAPI Call Button (optional)
    vapi_settings = st.session_state.get("vapi_settings", {})
    if vapi_settings.get("enabled"):
        if st.button(f"📞 Call {agent_config.get('name')}", key=f"vapi_call_{agent_id}"):
            # Maybe use the last user message or a specific prompt for the call?
            last_user_message = next((msg["content"] for msg in reversed(chat_history) if msg["role"] == "user"), None)
            if last_user_message:
                call_id = process_vapi_call(agent_config, last_user_message)
                if call_id:
                    st.success(f"VAPI call initiated (ID: {call_id}). Status check pending implementation.")
                    add_message_to_chat(agent_id, "system", f"[VAPI Call Initiated based on last message: '{last_user_message[:50]}...']")
                    st.rerun()
                # Error handled within process_vapi_call
            else:
                st.warning("No previous user message to initiate VAPI call with.")

def render_data_tab(agent_config):
    """Render the data viewing/editing tab."""
    st.header("📊 Data Viewer")
    
    if not st.session_state.authenticated:
        st.warning("Please authenticate with Google in the sidebar to view data.")
        return

    spreadsheet_key = agent_config.get("spreadsheet_key")
    spreadsheet_info = REAL_SPREADSHEETS.get(spreadsheet_key)
    
    if not spreadsheet_info:
        st.warning(f"Spreadsheet key '{spreadsheet_key}' not found in configuration.")
        return
        
    spreadsheet_id = spreadsheet_info.get("id")
    if not spreadsheet_id:
         st.error(f"Spreadsheet ID missing for key '{spreadsheet_key}'.")
         return

    # Load all worksheets initially or let user select
    sheets_data_dict = get_sheets_data(spreadsheet_id) # Load all worksheets for this sheet
    
    if not sheets_data_dict:
        st.info("No data loaded. Check Google Sheet ID, permissions, and authentication.")
        # Optionally add a refresh button
        if st.button("Retry Loading Data"): st.rerun()
        return

    worksheet_names = list(sheets_data_dict.keys())
    if not worksheet_names:
        st.info("Spreadsheet contains no worksheets or no data could be loaded.")
        return

    # Worksheet selection
    selected_worksheet = st.selectbox(
        "Select Worksheet", 
        worksheet_names, 
        key=f"worksheet_select_{agent_config.get('id')}",
        index=0 # Default to first worksheet
    )
    
    if selected_worksheet and selected_worksheet in sheets_data_dict:
        df = sheets_data_dict[selected_worksheet]
        st.markdown(f"**Displaying:** `{selected_worksheet}`")
        
        # Display data using st.dataframe for better interaction
        st.dataframe(df, use_container_width=True)
        
        # Data editing section
        st.markdown("--- ")
        with st.expander("✏️ Edit Data", expanded=False):
            st.caption("Changes made here can be saved back to the Google Sheet.")
            # Use a unique key for the editor based on agent and worksheet
            editor_key = f"editor_{agent_config.get('id')}_{selected_worksheet}"
            edited_df = st.data_editor(df, key=editor_key, use_container_width=True, num_rows="dynamic")
            
            if st.button("Save Changes to Google Sheet", key=f"save_data_{agent_config.get('id')}_{selected_worksheet}"):
                # Check if data has changed before saving (optional optimization)
                if not df.equals(edited_df):
                    if update_sheets_data(spreadsheet_id, selected_worksheet, edited_df):
                        # Refresh data view after saving
                        st.rerun()
                    # Error handled within update_sheets_data
                else:
                    st.info("No changes detected to save.")
    else:
        st.warning(f"Selected worksheet '{selected_worksheet}' not found or empty.")

def render_analytics_tab(agent_config):
    """Render the data analytics tab."""
    st.header("📈 Analytics")

    if not st.session_state.authenticated:
        st.warning("Please authenticate with Google in the sidebar to view analytics.")
        return

    spreadsheet_key = agent_config.get("spreadsheet_key")
    spreadsheet_info = REAL_SPREADSHEETS.get(spreadsheet_key)
    
    if not spreadsheet_info or not spreadsheet_info.get("id"):
        st.warning(f"Spreadsheet configuration missing or invalid for agent.")
        return
        
    spreadsheet_id = spreadsheet_info["id"]
    sheets_data_dict = get_sheets_data(spreadsheet_id)
    
    if not sheets_data_dict:
        st.info("No data available for analysis.")
        return

    worksheet_names = list(sheets_data_dict.keys())
    if not worksheet_names:
        st.info("No worksheets available for analysis.")
        return

    selected_worksheet = st.selectbox(
        "Select Worksheet for Analysis", 
        worksheet_names, 
        key=f"analytics_ws_select_{agent_config.get('id')}"
    )
    
    if selected_worksheet and selected_worksheet in sheets_data_dict:
        df = sheets_data_dict[selected_worksheet]
        st.markdown(f"**Analyzing:** `{selected_worksheet}`")
        
        if df.empty:
            st.info("Selected worksheet is empty.")
            return
            
        # Process data for insights
        processed_data = process_data(df)
        
        # Display Summary
        st.subheader("Data Overview")
        summary = processed_data.get("summary", {})
        st.metric("Total Rows", summary.get("rows", 0))
        st.metric("Total Columns", summary.get("columns", 0))
        with st.expander("Column Names"):
            st.write(summary.get("column_names", []))
            
        # Display Insights
        st.subheader("Automated Insights")
        insights = processed_data.get("insights", [])
        if insights:
            for insight in insights:
                st.info(insight)
        else:
            st.info("No specific insights generated.")

        # Display Trends & Visualizations
        st.subheader("Trend Analysis (Numeric Columns)")
        trends = processed_data.get("trends", {})
        numeric_cols = list(trends.keys())

        if not numeric_cols:
            st.info("No numeric columns suitable for trend analysis found.")
            return

        # Allow selecting column for visualization
        col_to_visualize = st.selectbox("Select Numeric Column to Visualize", numeric_cols, key=f"viz_select_{agent_config.get('id')}_{selected_worksheet}")
        
        if col_to_visualize:
            st.markdown(f"#### Distribution of `{col_to_visualize}`")
            try:
                fig = px.histogram(df, x=col_to_visualize, title=f"Histogram for {col_to_visualize}")
                st.plotly_chart(fig, use_container_width=True)
                
                # Display key stats for the selected column
                stats = trends.get(col_to_visualize, {})
                if stats:
                    cols = st.columns(5)
                    cols[0].metric("Mean", f"{stats.get('mean', 0):.2f}")
                    cols[1].metric("Median", f"{stats.get('median', 0):.2f}")
                    cols[2].metric("Min", f"{stats.get('min', 0):.2f}")
                    cols[3].metric("Max", f"{stats.get('max', 0):.2f}")
                    cols[4].metric("Std Dev", f"{stats.get('std_dev', 0):.2f}")
                    
            except Exception as e:
                st.error(f"Error generating visualization for {col_to_visualize}: {e}")
    else:
        st.warning(f"Selected worksheet '{selected_worksheet}' not found or empty.")

def render_agent_settings_tab(agent_config):
    """Render the settings specific to the selected agent."""
    st.header("🔧 Agent Configuration")
    agent_id = agent_config.get("id")

    # Display current agent config (read-only)
    st.subheader("Current Configuration")
    st.json(agent_config, expanded=False)

    # Prompt Library Section
    st.subheader("💡 Prompt Library")
    category = agent_config.get("category", "General")
    if category not in st.session_state.prompt_library:
        st.session_state.prompt_library[category] = []

    # Add New Prompt Form
    with st.form(key=f"add_prompt_form_{agent_id}"):
        st.markdown("**Add New Prompt**")
        new_prompt_title = st.text_input("Prompt Title")
        new_prompt_text = st.text_area("Prompt Text")
        submitted = st.form_submit_button("Add Prompt")
        if submitted:
            if new_prompt_title and new_prompt_text:
                st.session_state.prompt_library[category].append({
                    "title": new_prompt_title,
                    "prompt": new_prompt_text
                })
                st.success(f"Prompt '{new_prompt_title}' added to {category} library.")
                # Consider saving prompts persistently (e.g., to a file)
                st.rerun() # Rerun to update the display
            else:
                st.warning("Please provide both a title and text for the prompt.")

    # Display Existing Prompts
    st.markdown("**Available Prompts**")
    prompts = st.session_state.prompt_library[category]
    if not prompts:
        st.info(f"No prompts saved for the '{category}' category yet.")
    else:
        for i, prompt in enumerate(prompts):
            with st.expander(f"{prompt['title']}"):
                st.markdown(f"```
{prompt['prompt']}
```")
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("Use", key=f"use_prompt_{agent_id}_{i}"):
                        # Add prompt text to chat input (requires chat_input key access or different approach)
                        # This is tricky with st.chat_input. Alternative: copy to clipboard or set in a text_area.
                        st.session_state[f"chat_input_{agent_id}"] = prompt["prompt"] # May not work directly
                        st.info(f"Prompt '{prompt['title']}' copied to input (rerun may be needed).")
                        # st.rerun() # Force rerun might clear the input depending on Streamlit version
                with col2:
                     if st.button("Delete", key=f"delete_prompt_{agent_id}_{i}"):
                         del st.session_state.prompt_library[category][i]
                         st.success(f"Prompt '{prompt['title']}' deleted.")
                         # Consider saving changes
                         st.rerun()

# --- Main Application Logic ---
def main():
    """Main function to run the Streamlit application."""
    render_sidebar()
    
    # Main content area
    current_page_key = st.session_state.get("current_page")
    
    if not st.session_state.authenticated:
         st.warning("Please authenticate using the sidebar to access agent functionalities.")
    elif current_page_key:
        render_agent_page(current_page_key)
    else:
        st.info("Select an agent from the sidebar to begin.")

if __name__ == "__main__":
    main()

