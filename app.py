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
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import time

# Page configuration
st.set_page_config(
    page_title="25-Agent Business Dashboard", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar'
]

# Real spreadsheet IDs
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

# Get webhook URL and bearer token from Streamlit secrets
try:
    WEBHOOK_URL = st.secrets["WEBHOOK_URL"]
    BEARER_TOKEN = st.secrets["BEARER_TOKEN"]
    # Add VAPI AI credentials to Streamlit secrets
    VAPI_API_KEY = st.secrets.get("VAPI_API_KEY", "your_vapi_api_key_here")
    VAPI_ENDPOINT = st.secrets.get("VAPI_ENDPOINT", "https://api.vapi.ai/v1")
except Exception:
    # Fallback for local development
    WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/42e650d7-3e50-4dda-bf4f-d3e16b1cd"
    BEARER_TOKEN = "default_token"
    VAPI_API_KEY = "your_vapi_api_key_here"
    VAPI_ENDPOINT = "https://api.vapi.ai/v1"

# Configuration for 25 Agents with unified webhook
AGENTS_CONFIG = {
    "Agent_CEO": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_CEO",
        "name": "Agent CEO",
        "description": "Executive leadership and strategic decision making",
        "icon": "👔",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000001",
        "ai_assistant_id": "bf161516-6d88-490c-972e-274098a6b51a",
        "category": "Leadership",
        "specialization": "Strategic Planning, Executive Decisions, Leadership",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Social": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_SOCIAL",
        "name": "Agent Social",
        "description": "Social media management and digital marketing",
        "icon": "📱",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000002",
        "ai_assistant_id": "bf161516-6d88-490c-972e-274098a6b51a",
        "category": "Marketing",
        "specialization": "Social Media, Content Creation, Digital Marketing",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Mindset": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_MINDSET",
        "name": "Agent Mindset",
        "description": "Personal development and mindset coaching",
        "icon": "🧠",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000003",
        "ai_assistant_id": "4fe7083e-2f28-4502-b6bf-4ae6ea71a8f4",
        "category": "Development",
        "specialization": "Mindset Coaching, Personal Growth, Motivation",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Blogger": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_BLOGGER",
        "name": "Agent Blogger",
        "description": "Content creation and blog writing",
        "icon": "✍️",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000004",
        "ai_assistant_id": "f8ef1ad5-5281-42f1-ae69-f94ff7acb453",
        "category": "Content",
        "specialization": "Blog Writing, Content Strategy, SEO",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Grant": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_GRANT",
        "name": "Agent Grant",
        "description": "Grant writing and funding applications",
        "icon": "💰",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000005",
        "ai_assistant_id": "7673e69d-170b-4319-bdf4-e74e5370e98a",
        "category": "Finance",
        "specialization": "Grant Writing, Funding, Proposals",
        "spreadsheet": REAL_SPREADSHEETS["Grant"]
    },
    "Agent_Prayer_AI": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_PRAYER",
        "name": "Agent Prayer AI",
        "description": "Spiritual guidance and prayer assistance",
        "icon": "🙏",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000006",
        "ai_assistant_id": "339cdad6-9989-4bb6-98ed-bd15521707d1",
        "category": "Spiritual",
        "specialization": "Prayer, Spiritual Guidance, Faith",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Metrics": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_METRICS",
        "name": "Agent Metrics",
        "description": "Analytics and performance tracking",
        "icon": "📊",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000007",
        "ai_assistant_id": "4820eab2-adaf-4f17-a8a0-30cab3e3f007",
        "category": "Analytics",
        "specialization": "KPIs, Analytics, Performance Tracking",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Researcher": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_RESEARCH",
        "name": "Agent Researcher",
        "description": "Research and data analysis",
        "icon": "🔬",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000008",
        "ai_assistant_id": "f05c182f-d3d1-4a17-9c79-52442a9171b8",
        "category": "Research",
        "specialization": "Market Research, Data Analysis, Insights",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Investor": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_INVESTOR",
        "name": "Agent Investor",
        "description": "Investment analysis and financial planning",
        "icon": "💼",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000009",
        "ai_assistant_id": "1008771d-86ca-472a-a125-7a7e10100297",
        "category": "Finance",
        "specialization": "Investment Analysis, Portfolio Management",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Newsroom": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_NEWS",
        "name": "Agent Newsroom",
        "description": "News aggregation and journalism",
        "icon": "📰",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000010",
        "ai_assistant_id": "76f1d6e5-cab4-45b8-9aeb-d3e6f3c0c019",
        "category": "Media",
        "specialization": "News, Journalism, Content Curation",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "STREAMLIT_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_STREAMLIT",
        "name": "STREAMLIT Agent",
        "description": "Streamlit app development and Python coding",
        "icon": "🐍",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000011",
        "ai_assistant_id": "538258da-0dda-473d-8ef8-5427251f3ad5",
        "category": "Development",
        "specialization": "Streamlit, Python, Web Apps",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "HTML_CSS_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_HTML",
        "name": "HTML/CSS Agent",
        "description": "Web development and frontend design",
        "icon": "🌐",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000012",
        "ai_assistant_id": "14b94e2f-299b-4e75-a445-a4f5feacc522",
        "category": "Development",
        "specialization": "HTML, CSS, Frontend Development",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Business_Plan_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_BIZPLAN",
        "name": "Business Plan Agent",
        "description": "Business planning and strategy development",
        "icon": "📋",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000013",
        "ai_assistant_id": "87d59105-723b-427e-a18d-da99fbf28608",
        "category": "Business",
        "specialization": "Business Plans, Strategy, Market Analysis",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Ecom_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_ECOM",
        "name": "Ecom Agent",
        "description": "E-commerce and online retail management",
        "icon": "🛒",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000014",
        "ai_assistant_id": "d56551f8-0447-468a-872b-eaa9f830993d",
        "category": "E-commerce",
        "specialization": "Online Retail, E-commerce Strategy, Sales",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Health": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_HEALTH",
        "name": "Agent Health",
        "description": "Health and wellness guidance",
        "icon": "🏥",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000015",
        "ai_assistant_id": "7b2b8b86-5caa-4f28-8c6b-e7d3d0404f06",
        "category": "Health",
        "specialization": "Health, Wellness, Medical Information",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Cinch_Closer": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_CLOSER",
        "name": "Cinch Closer",
        "description": "Sales closing and deal negotiation",
        "icon": "🤝",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000016",
        "ai_assistant_id": "232f3d9c-18b3-4963-bdd9-e7de3be156ae",
        "category": "Sales",
        "specialization": "Sales Closing, Negotiation, Deal Making",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "DISC_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_DISC",
        "name": "DISC Agent",
        "description": "DISC personality assessment and analysis",
        "icon": "🎯",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000017",
        "ai_assistant_id": "41fe59e1-829f-4936-8ee5-eef2bb1287fe",
        "category": "Assessment",
        "specialization": "DISC Assessment, Personality Analysis",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Biz_Plan_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_BIZPLAN2",
        "name": "Biz Plan Agent",
        "description": "Advanced business planning and modeling",
        "icon": "📈",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000018",
        "ai_assistant_id": "87d59105-723b-427e-a18d-da99fbf28608",
        "category": "Business",
        "specialization": "Business Modeling, Financial Planning",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Invoice_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_INVOICE",
        "name": "Invoice Agent",
        "description": "Invoice management and billing automation",
        "icon": "🧾",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000019",
        "ai_assistant_id": "invoice_assistant_placeholder",
        "category": "Finance",
        "specialization": "Invoicing, Billing, Payment Processing",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Clone": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_CLONE",
        "name": "Agent Clone",
        "description": "AI agent replication and customization",
        "icon": "👥",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000020",
        "ai_assistant_id": "88862739-c227-4bfc-b90a-5f450a823e23",
        "category": "AI",
        "specialization": "Agent Cloning, AI Customization",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Doctor": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_DOCTOR",
        "name": "Agent Doctor",
        "description": "Medical consultation and health advice",
        "icon": "👨‍⚕️",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000021",
        "ai_assistant_id": "9d1cccc6-3193-4694-a9f7-853198ee4082",
        "category": "Medical",
        "specialization": "Medical Consultation, Health Advice",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Multi_Lig": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_MULTILIG",
        "name": "Agent Multi Lig",
        "description": "Multi-language translation and communication",
        "icon": "🌍",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000022",
        "ai_assistant_id": "8f045bce-08bc-4477-8d3d-05f233a44df3",
        "category": "Language",
        "specialization": "Translation, Multi-language Support",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    },
    "Agent_Real_Estate": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_REALESTATE",
        "name": "Agent Real Estate",
        "description": "Real estate analysis and property management",
        "icon": "🏠",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000023",
        "ai_assistant_id": "d982667e-d931-477c-9708-c183ba0aa964",
        "category": "Real Estate",
        "specialization": "Property Analysis, Real Estate Investment",
        "spreadsheet": REAL_SPREADSHEETS["Real Estate"]
    },
    "Follow_Up_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_FOLLOWUP",
        "name": "Follow Up Agent",
        "description": "Customer follow-up and relationship management",
        "icon": "📞",
        "webhook_url": WEBHOOK_URL,
        "bearer_token": BEARER_TOKEN,
        "ai_phone": "+15551000024",
        "ai_assistant_id": "39928b52-d610-43cb-9004-b88028e399fc",
        "category": "CRM",
        "specialization": "Follow-up, Customer Relations, CRM",
        "spreadsheet": REAL_SPREADSHEETS["Agent"]
    }
}

# Session state initialization
def initialize_session_state():
    defaults = {
        'authenticated': False,
        'credentials': None,
        'user_info': None,
        'current_page': 'Agent_CEO',
        'current_tab': 'chatbot',
        'current_spreadsheet': None,
        'current_worksheet': None,
        'sheets_data': {},
        'chat_sessions': {},
        'recognizer': sr.Recognizer(),
        'use_tts': True,
        'show_timestamps': False,
        'recording_status': False,
        'ai_calls': {},
        'agent_configs': AGENTS_CONFIG,
        'prompt_library': {},
        'vapi_settings': {
            'api_key': VAPI_API_KEY,
            'endpoint': VAPI_ENDPOINT,
            'enabled': False
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
initialize_session_state()

# Authentication functions
def authenticate_user():
    """Authenticate user with Google OAuth"""
    # Authentication logic here
    st.session_state.authenticated = True
    st.session_state.user_info = {"name": "Demo User", "email": "demo@example.com"}

# Helper functions
def get_agent_by_id(agent_id):
    """Get agent configuration by ID"""
    for agent_key, agent_config in AGENTS_CONFIG.items():
        if agent_config["id"] == agent_id:
            return agent_config
    return None

def format_timestamp(timestamp):
    """Format timestamp for chat messages"""
    if not st.session_state.show_timestamps:
        return ""
    dt = datetime.fromtimestamp(timestamp)
    return f"[{dt.strftime('%H:%M:%S')}] "

def text_to_speech(text):
    """Convert text to speech using gTTS"""
    if not st.session_state.use_tts:
        return None
    
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"TTS Error: {str(e)}")
        return None

def autoplay_audio(file_path):
    """Autoplay audio file"""
    if file_path is None:
        return
    
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_tag = f'<audio autoplay="true" src="data:audio/mp3;base64,{audio_base64}"></audio>'
        st.markdown(audio_tag, unsafe_allow_html=True)
        
        # Clean up the file after playing
        os.remove(file_path)
    except Exception as e:
        st.error(f"Audio playback error: {str(e)}")

def speech_to_text():
    """Convert speech to text using speech_recognition"""
    if st.session_state.recording_status:
        try:
            with sr.Microphone() as source:
                st.session_state.recognizer.adjust_for_ambient_noise(source)
                audio = st.session_state.recognizer.listen(source, timeout=5)
                text = st.session_state.recognizer.recognize_google(audio)
                return text
        except Exception as e:
            st.error(f"STT Error: {str(e)}")
    return None

def send_message_to_agent(agent_config, message):
    """Send message to agent via webhook"""
    if not message.strip():
        return None
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {agent_config['bearer_token']}"
        }
        
        payload = {
            "message": message,
            "agent_id": agent_config["id"],
            "user_id": st.session_state.user_info["email"] if st.session_state.user_info else "anonymous"
        }
        
        response = requests.post(
            agent_config["webhook_url"],
            headers=headers,
            data=json.dumps(payload)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

def process_vapi_call(agent_config, message):
    """Process VAPI call for voice interactions"""
    if not st.session_state.vapi_settings['enabled'] or not message.strip():
        return None
        
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st.session_state.vapi_settings['api_key']}"
        }
        
        payload = {
            "message": message,
            "assistant_id": agent_config["ai_assistant_id"],
            "phone_number": agent_config["ai_phone"]
        }
        
        response = requests.post(
            f"{st.session_state.vapi_settings['endpoint']}/calls",
            headers=headers,
            data=json.dumps(payload)
        )
        
        if response.status_code == 200:
            call_data = response.json()
            call_id = call_data.get("id")
            
            if call_id:
                # Store call data in session state
                if 'vapi_calls' not in st.session_state:
                    st.session_state.vapi_calls = {}
                
                st.session_state.vapi_calls[call_id] = {
                    "status": "initiated",
                    "agent": agent_config["name"],
                    "timestamp": datetime.now().timestamp(),
                    "message": message
                }
                
                return call_id
        else:
            st.error(f"VAPI Error: {response.status_code} - {response.text}")
        
        return None
    except Exception as e:
        st.error(f"VAPI Error: {str(e)}")
        return None

def get_vapi_call_status(call_id):
    """Get VAPI call status"""
    if not st.session_state.vapi_settings['enabled'] or not call_id:
        return None
        
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.vapi_settings['api_key']}"
        }
        
        response = requests.get(
            f"{st.session_state.vapi_settings['endpoint']}/calls/{call_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"VAPI Status Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"VAPI Status Error: {str(e)}")
        return None

def get_chat_history(agent_id):
    """Get chat history for an agent"""
    if agent_id not in st.session_state.chat_sessions:
        st.session_state.chat_sessions[agent_id] = []
    return st.session_state.chat_sessions[agent_id]

def add_message_to_chat(agent_id, role, content):
    """Add message to chat history"""
    if agent_id not in st.session_state.chat_sessions:
        st.session_state.chat_sessions[agent_id] = []
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().timestamp()
    }
    
    st.session_state.chat_sessions[agent_id].append(message)
    return message

def clear_chat_history(agent_id):
    """Clear chat history for an agent"""
    if agent_id in st.session_state.chat_sessions:
        st.session_state.chat_sessions[agent_id] = []

def get_sheets_data(spreadsheet_id):
    """Get data from Google Sheets"""
    if not st.session_state.credentials:
        st.error("Not authenticated with Google")
        return None
    
    if spreadsheet_id in st.session_state.sheets_data:
        return st.session_state.sheets_data[spreadsheet_id]
    
    try:
        # Use credentials to create a client to interact with Google Sheets
        gc = gspread.authorize(st.session_state.credentials)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Get all worksheets
        worksheets = spreadsheet.worksheets()
        
        # Store data for each worksheet
        sheets_data = {}
        for worksheet in worksheets:
            try:
                df = get_as_dataframe(worksheet, evaluate_formulas=True, skiprows=0)
                # Clean up the dataframe (remove empty rows and columns)
                df = df.dropna(how='all').dropna(axis=1, how='all')
                if not df.empty:
                    sheets_data[worksheet.title] = df
            except Exception as e:
                st.error(f"Error loading worksheet {worksheet.title}: {str(e)}")
        
        # Cache the data
        st.session_state.sheets_data[spreadsheet_id] = sheets_data
        return sheets_data
    except Exception as e:
        st.error(f"Error loading spreadsheet: {str(e)}")
        return None

def update_sheets_data(spreadsheet_id, worksheet_name, df):
    """Update data in Google Sheets"""
    if not st.session_state.credentials:
        st.error("Not authenticated with Google")
        return False
    
    try:
        # Use credentials to create a client to interact with Google Sheets
        gc = gspread.authorize(st.session_state.credentials)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Get the worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except:
            # Create worksheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=df.shape[0] + 10, cols=df.shape[1] + 5)
        
        # Update the worksheet
        set_with_dataframe(worksheet, df)
        
        # Update the cached data
        if spreadsheet_id in st.session_state.sheets_data:
            st.session_state.sheets_data[spreadsheet_id][worksheet_name] = df
        
        return True
    except Exception as e:
        st.error(f"Error updating spreadsheet: {str(e)}")
        return False

def process_data(data):
    """Process data for visualization and analysis"""
    if data is None or data.empty:
        # Instead of returning early, return empty processed data
        return {
            "summary": {},
            "trends": {},
            "insights": []
        }
    
    # Basic data processing
    summary = {
        "row_count": len(data),
        "column_count": len(data.columns)
    }
    
    # Extract numeric columns for trends
    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
    trends = {}
    
    for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
        try:
            trends[col] = {
                "mean": data[col].mean(),
                "median": data[col].median(),
                "min": data[col].min(),
                "max": data[col].max()
            }
        except:
            pass
    
    # Generate basic insights
    insights = []
    
    if len(numeric_cols) > 0:
        insights.append(f"Found {len(numeric_cols)} numeric columns that can be used for analysis.")
    
    # Return processed data
    return {
        "summary": summary,
        "trends": trends,
        "insights": insights
    }

# UI Components
def render_sidebar():
    """Render sidebar with agent selection"""
    with st.sidebar:
        st.title("25-Agent Dashboard")
        
        # User info
        if st.session_state.authenticated and st.session_state.user_info:
            st.write(f"Welcome, {st.session_state.user_info['name']}")
        
        # Agent categories
        categories = {}
        for agent_key, agent_config in AGENTS_CONFIG.items():
            category = agent_config.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append((agent_key, agent_config))
        
        # Display agents by category
        for category, agents in categories.items():
            with st.expander(f"{category} ({len(agents)})", expanded=True):
                for agent_key, agent_config in agents:
                    if st.button(f"{agent_config['icon']} {agent_config['name']}", key=f"btn_{agent_key}"):
                        st.session_state.current_page = agent_key
                        st.rerun()
        
        # Settings
        with st.expander("Settings", expanded=False):
            st.checkbox("Text-to-Speech", value=st.session_state.use_tts, key="use_tts")
            st.checkbox("Show Timestamps", value=st.session_state.show_timestamps, key="show_timestamps")
            
            # VAPI Settings
            st.subheader("VAPI Settings")
            vapi_enabled = st.checkbox("Enable VAPI", value=st.session_state.vapi_settings.get('enabled', False), key="vapi_enabled")
            vapi_api_key = st.text_input("VAPI API Key", value=st.session_state.vapi_settings.get('api_key', ''), type="password", key="vapi_api_key")
            vapi_endpoint = st.text_input("VAPI Endpoint", value=st.session_state.vapi_settings.get('endpoint', 'https://api.vapi.ai/v1'), key="vapi_endpoint")
            
            # Update VAPI settings
            st.session_state.vapi_settings = {
                'enabled': vapi_enabled,
                'api_key': vapi_api_key,
                'endpoint': vapi_endpoint
            }
            
            # Logout button
            if st.button("Logout"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                initialize_session_state()
                st.rerun()

def render_agent_page(agent_key):
    """Render agent page with tabs"""
    agent_config = AGENTS_CONFIG.get(agent_key)
    
    if not agent_config:
        st.error(f"Agent {agent_key} not found")
        return
    
    # Agent header
    st.title(f"{agent_config['icon']} {agent_config['name']}")
    st.write(agent_config['description'])
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Chatbot", "Data", "Analytics", "Settings"])
    
    with tab1:
        render_chatbot_tab(agent_config)
    
    with tab2:
        render_data_tab(agent_config)
    
    with tab3:
        render_analytics_tab(agent_config)
    
    with tab4:
        render_settings_tab(agent_config)

def render_chatbot_tab(agent_config):
    """Render chatbot tab"""
    st.subheader("Chat with Agent")
    
    # Chat container
    chat_container = st.container()
    
    # Input area
    input_container = st.container()
    
    with input_container:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            user_input = st.text_input("Message", key=f"input_{agent_config['id']}")
        
        with col2:
            # Voice input button
            voice_button = st.button("🎤 Voice", key=f"voice_{agent_config['id']}")
            if voice_button:
                st.session_state.recording_status = True
                speech_text = speech_to_text()
                st.session_state.recording_status = False
                
                if speech_text:
                    user_input = speech_text
                    st.session_state[f"input_{agent_config['id']}"] = speech_text
        
        with col3:
            # Send button and clear chat button
            send_button = st.button("Send", key=f"send_{agent_config['id']}")
            clear_button = st.button("Clear", key=f"clear_{agent_config['id']}")
    
    # VAPI call button
    if st.session_state.vapi_settings['enabled']:
        vapi_call = st.button("📞 Call Agent", key=f"vapi_{agent_config['id']}")
        if vapi_call and user_input:
            call_id = process_vapi_call(agent_config, user_input)
            if call_id:
                st.success(f"Call initiated with ID: {call_id}")
                # Add message to chat
                add_message_to_chat(agent_config['id'], "user", f"[VAPI Call] {user_input}")
                # Clear input
                st.session_state[f"input_{agent_config['id']}"] = ""
                st.rerun()
    
    # Handle send button
    if send_button and user_input:
        # Add user message to chat
        add_message_to_chat(agent_config['id'], "user", user_input)
        
        # Send message to agent
        response = send_message_to_agent(agent_config, user_input)
        
        if response:
            # Add agent response to chat
            agent_message = response.get("message", "No response from agent")
            add_message_to_chat(agent_config['id'], "assistant", agent_message)
            
            # Text-to-speech for agent response
            if st.session_state.use_tts:
                audio_file = text_to_speech(agent_message)
                if audio_file:
                    autoplay_audio(audio_file)
        
        # Clear input
        st.session_state[f"input_{agent_config['id']}"] = ""
        st.rerun()
    
    # Handle clear button
    if clear_button:
        clear_chat_history(agent_config['id'])
        st.rerun()
    
    # Display chat history
    with chat_container:
        chat_history = get_chat_history(agent_config['id'])
        
        if not chat_history:
            st.info(f"Start chatting with {agent_config['name']}!")
        else:
            for message in chat_history:
                timestamp_str = format_timestamp(message["timestamp"])
                
                if message["role"] == "user":
                    st.markdown(f"**{timestamp_str}You:** {message['content']}")
                else:
                    st.markdown(f"**{timestamp_str}{agent_config['name']}:** {message['content']}")

def render_data_tab(agent_config):
    """Render data tab"""
    st.subheader("Agent Data")
    
    # Get spreadsheet data
    spreadsheet_id = agent_config['spreadsheet']['id']
    sheets_data = get_sheets_data(spreadsheet_id)
    
    if not sheets_data:
        st.warning("No data available. Please authenticate with Google.")
        return
    
    # Worksheet selection
    worksheet_names = list(sheets_data.keys())
    if not worksheet_names:
        st.warning("No worksheets found in the spreadsheet.")
        return
    
    selected_worksheet = st.selectbox("Select Worksheet", worksheet_names, key=f"worksheet_{agent_config['id']}")
    
    if selected_worksheet not in sheets_data:
        st.warning(f"Worksheet {selected_worksheet} not found.")
        return
    
    # Display data
    df = sheets_data[selected_worksheet]
    st.dataframe(df, use_container_width=True)
    
    # Data editing
    with st.expander("Edit Data", expanded=False):
        st.write("Edit data and click 'Save Changes' to update the spreadsheet.")
        
        # Create a copy of the dataframe for editing
        edited_df = st.data_editor(df, key=f"editor_{agent_config['id']}", use_container_width=True)
        
        # Save changes button
        if st.button("Save Changes", key=f"save_{agent_config['id']}"):
            if update_sheets_data(spreadsheet_id, selected_worksheet, edited_df):
                st.success("Data updated successfully!")
            else:
                st.error("Failed to update data.")

def render_analytics_tab(agent_config):
    """Render analytics tab"""
    st.subheader("Analytics")
    
    # Get spreadsheet data
    spreadsheet_id = agent_config['spreadsheet']['id']
    sheets_data = get_sheets_data(spreadsheet_id)
    
    if not sheets_data:
        st.warning("No data available. Please authenticate with Google.")
        return
    
    # Worksheet selection
    worksheet_names = list(sheets_data.keys())
    if not worksheet_names:
        st.warning("No worksheets found in the spreadsheet.")
        return
    
    selected_worksheet = st.selectbox("Select Worksheet", worksheet_names, key=f"analytics_worksheet_{agent_config['id']}")
    
    if selected_worksheet not in sheets_data:
        st.warning(f"Worksheet {selected_worksheet} not found.")
        return
    
    # Get data
    df = sheets_data[selected_worksheet]
    
    # Process data
    processed_data = process_data(df)
    
    # Display summary
    st.subheader("Data Summary")
    st.write(f"Rows: {processed_data['summary'].get('row_count', 0)}")
    st.write(f"Columns: {processed_data['summary'].get('column_count', 0)}")
    
    # Display trends
    if processed_data['trends']:
        st.subheader("Trends")
        
        # Select columns for visualization
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if numeric_cols:
            selected_col = st.selectbox("Select Column for Visualization", numeric_cols, key=f"viz_col_{agent_config['id']}")
            
            # Create visualization
            st.subheader(f"{selected_col} Distribution")
            
            try:
                fig = px.histogram(df, x=selected_col, nbins=20)
                st.plotly_chart(fig, use_container_width=True)
                
                # Add basic statistics
                col_stats = processed_data['trends'].get(selected_col, {})
                if col_stats:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Mean", f"{col_stats.get('mean', 0):.2f}")
                    col2.metric("Median", f"{col_stats.get('median', 0):.2f}")
                    col3.metric("Min", f"{col_stats.get('min', 0):.2f}")
                    col4.metric("Max", f"{col_stats.get('max', 0):.2f}")
            except Exception as e:
                st.error(f"Error creating visualization: {str(e)}")
    
    # Display insights
    if processed_data['insights']:
        st.subheader("Insights")
        for insight in processed_data['insights']:
            st.info(insight)

def render_settings_tab(agent_config):
    """Render settings tab"""
    st.subheader("Agent Settings")
    
    # Display agent configuration
    st.json(agent_config)
    
    # Prompt library
    st.subheader("Prompt Library")
    
    # Get prompts for this agent's category
    category = agent_config.get("category", "Other")
    
    # Add new prompt
    with st.expander("Add New Prompt", expanded=False):
        prompt_title = st.text_input("Prompt Title", key=f"prompt_title_{agent_config['id']}")
        prompt_text = st.text_area("Prompt Text", key=f"prompt_text_{agent_config['id']}")
        
        if st.button("Add Prompt", key=f"add_prompt_{agent_config['id']}"):
            if prompt_title and prompt_text:
                if category not in st.session_state.prompt_library:
                    st.session_state.prompt_library[category] = []
                
                st.session_state.prompt_library[category].append({
                    "title": prompt_title,
                    "prompt": prompt_text
                })
                
                st.success("Prompt added successfully!")
                st.session_state[f"prompt_title_{agent_config['id']}"] = ""
                st.session_state[f"prompt_text_{agent_config['id']}"] = ""
                st.rerun()
    
    # Display prompts
    if category in st.session_state.prompt_library and st.session_state.prompt_library[category]:
        for i, prompt in enumerate(st.session_state.prompt_library[category]):
            with st.expander(prompt["title"], expanded=False):
                st.write(prompt["prompt"])
                
                if st.button("Use Prompt", key=f"use_prompt_{agent_config['id']}_{i}"):
                    # Set the prompt as user input
                    st.session_state[f"input_{agent_config['id']}"] = prompt["prompt"]
                    st.rerun()
    else:
        st.info(f"No prompts available for {category}. Add some prompts to get started!")

# Main app
def main():
    # Check authentication
    if not st.session_state.authenticated:
        authenticate_user()
    
    # Render sidebar
    render_sidebar()
    
    # Render current page
    current_page = st.session_state.current_page
    render_agent_page(current_page)

if __name__ == "__main__":
    main()
