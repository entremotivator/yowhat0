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

# Import the new enhanced chatbox component
from enhanced_chatbox_component import EnhancedChatbox

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
except Exception:
    # Fallback for local development
    WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/42e650d7-3e50-4dda-bf4f-d3e16b1cd"
    BEARER_TOKEN = "default_token"

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
        'agent_configs': AGENTS_CONFIG,
        'prompt_library': {
            "Leadership": [
                {"title": "Strategic Planning", "prompt": "Help me develop a strategic plan for [company/project]. Consider market conditions, resources, and long-term goals."},
                {"title": "Team Management", "prompt": "Provide guidance on managing a team of [number] people with diverse skills and personalities."},
                {"title": "Decision Making", "prompt": "Help me make a decision about [situation]. Analyze pros, cons, and potential outcomes."},
            ],
            "Sales & Marketing": [
                {"title": "Lead Qualification", "prompt": "Help me qualify this lead: [lead information]. Assess their potential and next steps."},
                {"title": "Social Media Strategy", "prompt": "Create a social media strategy for [business/product] targeting [audience]."},
                {"title": "Content Creation", "prompt": "Generate content ideas for [platform] about [topic] for [target audience]."},
            ],
            "Development": [
                {"title": "Code Review", "prompt": "Review this code and suggest improvements: [code snippet]"},
                {"title": "App Architecture", "prompt": "Help me design the architecture for a [type] application with [requirements]."},
                {"title": "Bug Troubleshooting", "prompt": "Help me troubleshoot this issue: [error description and code]"},
            ],
            "Finance & Business": [
                {"title": "Financial Analysis", "prompt": "Analyze the financial performance of [company/project] based on these metrics: [data]"},
                {"title": "Investment Evaluation", "prompt": "Evaluate this investment opportunity: [investment details]"},
                {"title": "Grant Proposal", "prompt": "Help me write a grant proposal for [project] seeking [amount] for [purpose]."},
            ],
            "Health & Wellness": [
                {"title": "Health Assessment", "prompt": "Provide general health guidance for someone with [symptoms/conditions]. Note: This is not medical advice."},
                {"title": "Wellness Plan", "prompt": "Create a wellness plan focusing on [areas like nutrition, exercise, mental health]."},
            ],
            "Real Estate": [
                {"title": "Property Analysis", "prompt": "Analyze this property investment: [property details, location, price, market conditions]"},
                {"title": "Market Research", "prompt": "Research the real estate market in [location] for [property type]."},
            ]
        },
        'favorites': [],
        'call_logs': {},
        'performance_metrics': {}
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
initialize_session_state()

# Authentication functions
def authenticate_service_account(json_content):
    """Authenticate using service account JSON content"""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            json_content, scopes=SCOPES
        )
        
        email = json_content.get('client_email', 'Service Account')
        
        st.session_state.authenticated = True
        st.session_state.credentials = credentials
        st.session_state.user_info = {'email': email, 'name': 'Service Account'}
        
        return True, "Google authentication successful!"
    except Exception as e:
        return False, f"Google authentication failed: {str(e)}"

# Helper functions (Old send_message_to_webhook removed)

def load_spreadsheet_data(agent_id):
    """Load data for specific agent - ONLY REAL DATA FROM SHEETS"""
    try:
        # Get the agent config
        config = st.session_state.agent_configs[agent_id]
        
        # Check if we have real spreadsheet data for this agent
        if 'spreadsheet' in config:
            spreadsheet_info = config['spreadsheet']
            spreadsheet_id = spreadsheet_info['id']
            
            # Only proceed if authenticated
            if st.session_state.authenticated:
                try:
                    # Initialize gspread client
                    gc = gspread.authorize(st.session_state.credentials)
                    
                    # Open the spreadsheet
                    spreadsheet = gc.open_by_key(spreadsheet_id)
                    
                    # Get all worksheets
                    worksheets = spreadsheet.worksheets()
                    
                    if not worksheets:
                        return None, "No worksheets found in the spreadsheet."
                    
                    # Get the first worksheet
                    worksheet = worksheets[0]
                    
                    # Get all values
                    data = worksheet.get_all_records()
                    
                    if not data:
                        return None, f"No data found in worksheet '{worksheet.title}'. Please add data to the spreadsheet first."
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data)
                    
                    # Clean the data - remove empty rows
                    df = df.dropna(how='all')
                    
                    if df.empty:
                        return None, f"Spreadsheet '{spreadsheet_info['name']}' contains no valid data. Please add data to the spreadsheet."
                    
                    # Convert date columns if they exist
                    date_columns = ['Date', 'date', 'DATE', 'Created', 'created', 'Timestamp', 'timestamp']
                    for col in df.columns:
                        if col in date_columns:
                            try:
                                df[col] = pd.to_datetime(df[col], errors='coerce')
                            except:
                                pass
                    
                    return df, None
                    
                except gspread.exceptions.SpreadsheetNotFound:
                    return None, f"Spreadsheet with ID '{spreadsheet_id}' not found. Please check the spreadsheet ID and permissions."
                except gspread.exceptions.APIError as e:
                    return None, f"Google Sheets API error: {str(e)}. Please check your permissions and try again."
                except Exception as e:
                    return None, f"Error loading spreadsheet data: {str(e)}"
            else:
                return None, "Please authenticate with Google to access spreadsheet data."
        else:
            return None, f"No spreadsheet configured for {config['name']}."
            
    except Exception as e:
        return None, f"Error loading data: {str(e)}"

def make_ai_call(agent_id, phone_number):
    """Initiate AI voice call"""
    config = st.session_state.agent_configs[agent_id]
    
    call_data = {
        "call_id": str(uuid.uuid4()),
        "agent_id": agent_id,
        "agent_name": config['name'],
        "phone_number": phone_number,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "initiated"
    }
    
    # In a real implementation, this would make an API call to initiate the call
    # For now, we'll just simulate it
    
    # Add to call logs
    if 'call_logs' not in st.session_state:
        st.session_state.call_logs = {}
        
    if agent_id not in st.session_state.call_logs:
        st.session_state.call_logs[agent_id] = []
        
    st.session_state.call_logs[agent_id].append(call_data)
    
    return call_data

# Sidebar
with st.sidebar:
    st.image("https://i.imgur.com/8M0fQBS.png", width=100)
    st.title("25-Agent Dashboard")
    
    # Authentication status
    if st.session_state.authenticated:
        st.success("✅ Authenticated with Google")
        if st.button("Sign Out"):
            st.session_state.authenticated = False
            st.session_state.credentials = None
            st.session_state.user_info = None
            st.rerun()
    else:
        st.warning("⚠️ Not authenticated with Google")
        # Service account JSON upload
        uploaded_file = st.file_uploader("Upload Service Account JSON", type="json")
        if uploaded_file is not None:
            try:
                json_content = json.load(uploaded_file)
                success, message = authenticate_service_account(json_content)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error processing JSON file: {str(e)}")
        st.caption("Or use the demo mode below.")
        if st.button("Use Demo Mode (No Google Access)"):
            st.session_state.authenticated = True # Simulate auth for demo
            st.session_state.user_info = {"name": "Demo User", "email": "demo@example.com"}
            st.session_state.credentials = None # No real credentials in demo
            st.info("Demo mode activated. Google Sheets data will not be available.")
            st.rerun()
    
    # Agent selection
    st.subheader("Select Agent")
    
    # Group agents by category
    categories = {}
    for agent_id, config in AGENTS_CONFIG.items():
        category = config.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append((agent_id, config))
    
    # Display agents by category
    for category, agents in sorted(categories.items()):
        with st.expander(f"**{category}**", expanded=(category == AGENTS_CONFIG[st.session_state.current_page]['category'])):
            for agent_id, config in sorted(agents, key=lambda x: x[1]['name']):
                if st.button(f"{config['icon']} {config['name']}", key=f"select_{agent_id}", use_container_width=True):
                    st.session_state.current_page = agent_id
                    st.rerun()
    
    # Settings (moved chat settings to main panel)
    st.subheader("Global Settings")
    # Add any global settings here if needed
    st.caption("Chat settings are available in the Chatbot tab.")
    
    # About
    st.markdown("---")
    st.markdown("### About")
    st.markdown("This dashboard connects to 25 specialized AI agents through a unified webhook system.")
    st.markdown("Each agent has specific capabilities and can access relevant data sources.")
    st.markdown("© 2023 AI Agent Network")

# Main content area
if not st.session_state.authenticated:
    # Show welcome message if not authenticated
    st.title("Welcome to the 25-Agent Business Dashboard!")
    st.markdown("Please authenticate using your Google Service Account JSON file via the sidebar to access all features, or use the Demo Mode.")
    st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=300)
    
    st.header("Available Agent Categories")
    # Display categories and agent counts
    category_counts = {}
    for config in AGENTS_CONFIG.values():
        category = config.get('category', 'Other')
        category_counts[category] = category_counts.get(category, 0) + 1
        
    cat_cols = st.columns(len(category_counts))
    i = 0
    for category, count in sorted(category_counts.items()):
        with cat_cols[i]:
            st.metric(category, count)
        i += 1

else:
    # Main dashboard for authenticated users
    current_config = st.session_state.agent_configs[st.session_state.current_page]
    
    # Page header with agent info
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title(f"{current_config['icon']} {current_config['name']}")
        st.caption(f"{current_config['description']} | Category: {current_config['category']}")
    
    with col2:
        st.metric("AI Assistant", "Active")
        st.caption(f"ID: {current_config['ai_assistant_id'][:8]}...")
    
    with col3:
        st.metric("Phone Number", current_config['ai_phone'])
        st.caption("Ready for calls")
    
    # Page Navigation Buttons
    st.write("### 📑 Page Navigation")
    page_nav_cols = st.columns(4)
    
    with page_nav_cols[0]:
        if st.button("🤖 Chatbot", use_container_width=True):
            st.session_state.current_tab = 'chatbot'
            st.rerun()
    
    with page_nav_cols[1]:
        if st.button("📊 Data (Sheets)", use_container_width=True):
            st.session_state.current_tab = 'data'
            st.rerun()
    
    with page_nav_cols[2]:
        if st.button("📞 AI Voice Call", use_container_width=True):
            st.session_state.current_tab = 'ai_call'
            st.rerun()
    
    with page_nav_cols[3]:
        if st.button("💡 Prompts/Info", use_container_width=True):
            st.session_state.current_tab = 'prompts'
            st.rerun()
    
    # Set default tab if not set
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 'chatbot'
    
    # Display content based on current tab
    if st.session_state.current_tab == 'chatbot':
        st.header("🤖 AI Chat Interface")
        
        # Instantiate and render the enhanced chatbox
        chatbox = EnhancedChatbox(agent_config=current_config)
        chatbox.render_full_chatbox()
    
    elif st.session_state.current_tab == 'data':
        st.header("📊 Google Sheets Data & Analytics")
        
        # Show spreadsheet info if available
        if 'spreadsheet' in current_config:
            spreadsheet_info = current_config['spreadsheet']
            st.info(f"📋 Connected to: **{spreadsheet_info['name']}** ({spreadsheet_info['description']}) - ID: `{spreadsheet_info['id']}`")
        
        # Load data for current agent
        if st.session_state.current_page not in st.session_state.sheets_data:
            with st.spinner("Loading data from Google Sheets..."):
                df, error = load_spreadsheet_data(st.session_state.current_page)
                if error:
                    st.error(f"❌ {error}")
                    
                    # Show helpful instructions
                    st.markdown("""
                    ### 📝 To view data in this section:
                    
                    1. **Ensure you're authenticated** with Google (check sidebar)
                    2. **Add data to your Google Sheet** with the configured spreadsheet ID
                    3. **Make sure the spreadsheet is shared** with your service account email
                    4. **Include column headers** in your first row
                    5. **Click 'Refresh Data'** button below to reload
                    
                    **Spreadsheet Requirements:**
                    - At least one row of data (excluding headers)
                    - Proper column names in the first row
                    - Accessible to your service account
                    """)
                    
                    if st.button("🔄 Refresh Data", key="refresh_error"):
                        # Clear cached data and try again
                        if st.session_state.current_page in st.session_state.sheets_data:
                            del st.session_state.sheets_data[st.session_state.current_page]
                        st.rerun()
                    
                    st.stop()  # Exit early if no data
                else:
                    st.session_state.sheets_data[st.session_state.current_page] = df
        
        if st.session_state.current_page in st.session_state.sheets_data:
            df = st.session_state.sheets_data[st.session_state.current_page]
            
            # Show data info
            st.success(f"✅ Successfully loaded {len(df)} rows and {len(df.columns)} columns from Google Sheets")
            
            # Data overview metrics
            st.subheader("📈 Key Metrics")
            
            # Dynamic metrics based on data columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            if len(numeric_cols) >= 1:
                # Create metrics based on available numeric columns
                metric_cols = st.columns(min(4, len(numeric_cols)))
                
                for i, col in enumerate(numeric_cols[:4]):  # Show up to 4 metrics
                    with metric_cols[i]:
                        if len(df) >= 2:
                            current_val = df[col].iloc[-1] if not pd.isna(df[col].iloc[-1]) else 0
                            prev_val = df[col].iloc[-2] if not pd.isna(df[col].iloc[-2]) else 0
                            delta = current_val - prev_val
                            
                            # Format numbers appropriately
                            if abs(current_val) >= 1000000:
                                display_val = f"{current_val/1000000:.1f}M"
                            elif abs(current_val) >= 1000:
                                display_val = f"{current_val/1000:.1f}K"
                            else:
                                display_val = f"{current_val:,.1f}"
                            
                            st.metric(col, display_val, delta=f"{delta:,.1f}")
                        else:
                            st.metric(col, f"{df[col].iloc[-1]:,.1f}" if not pd.isna(df[col].iloc[-1]) else "N/A")
            else:
                st.info("📊 No numeric columns found for metrics. Add numeric data to see key performance indicators.")
            
            # Data visualization
            st.subheader("📊 Data Visualizations")
            
            if len(numeric_cols) >= 1:
                viz_col1, viz_col2 = st.columns(2)
                
                # Find date column for time series
                date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or 'created' in col.lower()]
                date_col = date_cols[0] if date_cols else None
                
                with viz_col1:
                    if date_col and len(numeric_cols) >= 1:
                        # Time series chart
                        fig1 = px.line(df, x=date_col, y=numeric_cols[0], 
                                      title=f'{numeric_cols[0]} Over Time',
                                      color_discrete_sequence=['#1f77b4'])
                        fig1.update_layout(height=300)
                        st.plotly_chart(fig1, use_container_width=True)
                    elif len(numeric_cols) >= 1:
                        # Bar chart if no date column
                        fig1 = px.bar(df.head(10), x=df.columns[0], y=numeric_cols[0], 
                                     title=f'{numeric_cols[0]} by {df.columns[0]}',
                                     color_discrete_sequence=['#1f77b4'])
                        fig1.update_layout(height=300)
                        st.plotly_chart(fig1, use_container_width=True)
                
                with viz_col2:
                    if len(numeric_cols) >= 2:
                        if date_col:
                            # Second time series
                            fig2 = px.area(df, x=date_col, y=numeric_cols[1], 
                                          title=f'{numeric_cols[1]} Over Time',
                                          color_discrete_sequence=['#ff7f0e'])
                            fig2.update_layout(height=300)
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            # Scatter plot
                            fig2 = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                                             title=f'{numeric_cols[1]} vs {numeric_cols[0]}',
                                             color_discrete_sequence=['#ff7f0e'])
                            fig2.update_layout(height=300)
                            st.plotly_chart(fig2, use_container_width=True)
                    else:
                        # Histogram if only one numeric column
                        fig2 = px.histogram(df, x=numeric_cols[0], 
                                           title=f'Distribution of {numeric_cols[0]}',
                                           color_discrete_sequence=['#ff7f0e'])
                        fig2.update_layout(height=300)
                        st.plotly_chart(fig2, use_container_width=True)
                
                # Correlation heatmap if multiple numeric columns
                if len(numeric_cols) > 2:
                    st.subheader("🔥 Correlation Analysis")
                    correlation_matrix = df[numeric_cols].corr()
                    fig_heatmap = px.imshow(correlation_matrix, 
                                           text_auto=True, 
                                           aspect="auto",
                                           title="Metrics Correlation Heatmap",
                                           color_continuous_scale='RdBu')
                    fig_heatmap.update_layout(height=400)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
            else:
                st.info("📈 Add numeric columns to your spreadsheet to see data visualizations.")
            
            # Data table with filtering
            st.subheader("📋 Data Table")
            
            # Add filters
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                # Date filter if date column exists
                date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
                if date_cols:
                    date_col = date_cols[0]
                    try:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        min_date = df[date_col].min().date()
                        max_date = df[date_col].max().date()
                        date_range = st.date_input(
                            "Date Range:",
                            value=(min_date, max_date),
                            min_value=min_date,
                            max_value=max_date,
                            key=f"date_filter_{st.session_state.current_page}"
                        )
                        if len(date_range) == 2:
                            df = df[(df[date_col].dt.date >= date_range[0]) & (df[date_col].dt.date <= date_range[1])]
                    except Exception as e:
                        st.warning(f"Could not apply date filter: {e}")
                else:
                    st.caption("No date column found for filtering.")
            
            with filter_col2:
                # Text search filter
                search_term = st.text_input("Search Table:", key=f"search_{st.session_state.current_page}")
                if search_term:
                    # Search across all string columns
                    string_cols = df.select_dtypes(include=['object']).columns
                    df = df[df[string_cols].apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
            
            # Display filtered dataframe
            st.dataframe(df, use_container_width=True)
            
            # Option to download data
            @st.cache_data
            def convert_df(df_to_convert):
                return df_to_convert.to_csv(index=False).encode('utf-8')

            csv = convert_df(df)
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name=f"{current_config['name']}_data.csv",
                mime='text/csv',
            )
        else:
            # This case should not happen if st.stop() works correctly
            st.info("Data is currently being loaded or is unavailable.")

    elif st.session_state.current_tab == 'ai_call':
        st.header("📞 AI Voice Call Interface")
        
        st.info("This feature allows initiating AI-powered voice calls.")
        
        # Display agent's AI phone number
        st.write(f"**Agent Phone:** {current_config['ai_phone']}")
        
        # Input for target phone number
        target_phone = st.text_input("Enter phone number to call:", placeholder="+1234567890")
        
        if st.button("📞 Initiate Call", key=f"call_{st.session_state.current_page}"):
            if target_phone:
                with st.spinner("Initiating call..."):
                    call_info = make_ai_call(st.session_state.current_page, target_phone)
                    st.success(f"Call initiated to {target_phone}. Call ID: {call_info['call_id']}")
            else:
                st.warning("Please enter a phone number to call.")
        
        # Display call logs for this agent
        st.subheader("Recent Call Logs")
        if st.session_state.current_page in st.session_state.call_logs:
            call_log_df = pd.DataFrame(st.session_state.call_logs[st.session_state.current_page])
            st.dataframe(call_log_df.sort_values(by='timestamp', ascending=False), use_container_width=True)
        else:
            st.info("No call logs available for this agent yet.")

    elif st.session_state.current_tab == 'prompts':
        st.header("💡 Prompts & Agent Information")
        
        st.subheader("Agent Details")
        st.markdown(f"**Name:** {current_config['name']} ({current_config['icon']})")
        st.markdown(f"**Category:** {current_config['category']}")
        st.markdown(f"**Description:** {current_config['description']}")
        st.markdown(f"**Specialization:** {current_config['specialization']}")
        st.markdown(f"**AI Assistant ID:** `{current_config['ai_assistant_id']}`")
        st.markdown(f"**AI Phone:** `{current_config['ai_phone']}`")
        if 'spreadsheet' in current_config:
            st.markdown(f"**Connected Spreadsheet:** {current_config['spreadsheet']['name']} (`{current_config['spreadsheet']['id']}`)")
        
        st.subheader("Prompt Library")
        st.info("Use these prompts as starting points for your conversations.")
        
        # Use the chatbox component's prompt rendering
        chatbox = EnhancedChatbox(agent_config=current_config)
        chatbox.render_prompt_suggestions()
        
        # Display full prompt library
        with st.expander("View Full Prompt Library"):
            st.json(st.session_state.prompt_library)

    else:
        st.error("Invalid tab selected.")

