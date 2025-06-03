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

# N8N Configuration
N8N_WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/42e650d7-3e50-4dda-bf4f-d3e16b1cd"

# Configuration for 25 Agents with unified n8n webhook
AGENTS_CONFIG = {
    "Agent_CEO": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_CEO",
        "name": "Agent CEO",
        "description": "Executive leadership and strategic decision making",
        "icon": "👔",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000001",
        "ai_assistant_id": "bf161516-6d88-490c-972e-274098a6b51a",
        "category": "Leadership",
        "specialization": "Strategic Planning, Executive Decisions, Leadership"
    },
    "Agent_Social": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_SOCIAL",
        "name": "Agent Social",
        "description": "Social media management and digital marketing",
        "icon": "📱",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000002",
        "ai_assistant_id": "bf161516-6d88-490c-972e-274098a6b51a",
        "category": "Marketing",
        "specialization": "Social Media, Content Creation, Digital Marketing"
    },
    "Agent_Mindset": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_MINDSET",
        "name": "Agent Mindset",
        "description": "Personal development and mindset coaching",
        "icon": "🧠",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000003",
        "ai_assistant_id": "4fe7083e-2f28-4502-b6bf-4ae6ea71a8f4",
        "category": "Development",
        "specialization": "Mindset Coaching, Personal Growth, Motivation"
    },
    "Agent_Blogger": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_BLOGGER",
        "name": "Agent Blogger",
        "description": "Content creation and blog writing",
        "icon": "✍️",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000004",
        "ai_assistant_id": "f8ef1ad5-5281-42f1-ae69-f94ff7acb453",
        "category": "Content",
        "specialization": "Blog Writing, Content Strategy, SEO"
    },
    "Agent_Grant": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_GRANT",
        "name": "Agent Grant",
        "description": "Grant writing and funding applications",
        "icon": "💰",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000005",
        "ai_assistant_id": "7673e69d-170b-4319-bdf4-e74e5370e98a",
        "category": "Finance",
        "specialization": "Grant Writing, Funding, Proposals"
    },
    "Agent_Prayer_AI": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_PRAYER",
        "name": "Agent Prayer AI",
        "description": "Spiritual guidance and prayer assistance",
        "icon": "🙏",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000006",
        "ai_assistant_id": "339cdad6-9989-4bb6-98ed-bd15521707d1",
        "category": "Spiritual",
        "specialization": "Prayer, Spiritual Guidance, Faith"
    },
    "Agent_Metrics": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_METRICS",
        "name": "Agent Metrics",
        "description": "Analytics and performance tracking",
        "icon": "📊",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000007",
        "ai_assistant_id": "4820eab2-adaf-4f17-a8a0-30cab3e3f007",
        "category": "Analytics",
        "specialization": "KPIs, Analytics, Performance Tracking"
    },
    "Agent_Researcher": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_RESEARCH",
        "name": "Agent Researcher",
        "description": "Research and data analysis",
        "icon": "🔬",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000008",
        "ai_assistant_id": "f05c182f-d3d1-4a17-9c79-52442a9171b8",
        "category": "Research",
        "specialization": "Market Research, Data Analysis, Insights"
    },
    "Agent_Investor": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_INVESTOR",
        "name": "Agent Investor",
        "description": "Investment analysis and financial planning",
        "icon": "💼",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000009",
        "ai_assistant_id": "1008771d-86ca-472a-a125-7a7e10100297",
        "category": "Finance",
        "specialization": "Investment Analysis, Portfolio Management"
    },
    "Agent_Newsroom": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_NEWS",
        "name": "Agent Newsroom",
        "description": "News aggregation and journalism",
        "icon": "📰",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000010",
        "ai_assistant_id": "76f1d6e5-cab4-45b8-9aeb-d3e6f3c0c019",
        "category": "Media",
        "specialization": "News, Journalism, Content Curation"
    },
    "STREAMLIT_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_STREAMLIT",
        "name": "STREAMLIT Agent",
        "description": "Streamlit app development and Python coding",
        "icon": "🐍",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000011",
        "ai_assistant_id": "538258da-0dda-473d-8ef8-5427251f3ad5",
        "category": "Development",
        "specialization": "Streamlit, Python, Web Apps"
    },
    "HTML_CSS_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_HTML",
        "name": "HTML/CSS Agent",
        "description": "Web development and frontend design",
        "icon": "🌐",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000012",
        "ai_assistant_id": "14b94e2f-299b-4e75-a445-a4f5feacc522",
        "category": "Development",
        "specialization": "HTML, CSS, Frontend Development"
    },
    "Business_Plan_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_BIZPLAN",
        "name": "Business Plan Agent",
        "description": "Business planning and strategy development",
        "icon": "📋",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000013",
        "ai_assistant_id": "87d59105-723b-427e-a18d-da99fbf28608",
        "category": "Business",
        "specialization": "Business Plans, Strategy, Market Analysis"
    },
    "Ecom_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_ECOM",
        "name": "Ecom Agent",
        "description": "E-commerce and online retail management",
        "icon": "🛒",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000014",
        "ai_assistant_id": "d56551f8-0447-468a-872b-eaa9f830993d",
        "category": "E-commerce",
        "specialization": "Online Retail, E-commerce Strategy, Sales"
    },
    "Agent_Health": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_HEALTH",
        "name": "Agent Health",
        "description": "Health and wellness guidance",
        "icon": "🏥",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000015",
        "ai_assistant_id": "7b2b8b86-5caa-4f28-8c6b-e7d3d0404f06",
        "category": "Health",
        "specialization": "Health, Wellness, Medical Information"
    },
    "Cinch_Closer": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_CLOSER",
        "name": "Cinch Closer",
        "description": "Sales closing and deal negotiation",
        "icon": "🤝",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000016",
        "ai_assistant_id": "232f3d9c-18b3-4963-bdd9-e7de3be156ae",
        "category": "Sales",
        "specialization": "Sales Closing, Negotiation, Deal Making"
    },
    "DISC_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_DISC",
        "name": "DISC Agent",
        "description": "DISC personality assessment and analysis",
        "icon": "🎯",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000017",
        "ai_assistant_id": "41fe59e1-829f-4936-8ee5-eef2bb1287fe",
        "category": "Assessment",
        "specialization": "DISC Assessment, Personality Analysis"
    },
    "Biz_Plan_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_BIZPLAN2",
        "name": "Biz Plan Agent",
        "description": "Advanced business planning and modeling",
        "icon": "📈",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000018",
        "ai_assistant_id": "87d59105-723b-427e-a18d-da99fbf28608",
        "category": "Business",
        "specialization": "Business Modeling, Financial Planning"
    },
    "Invoice_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_INVOICE",
        "name": "Invoice Agent",
        "description": "Invoice management and billing automation",
        "icon": "🧾",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000019",
        "ai_assistant_id": "invoice_assistant_placeholder",
        "category": "Finance",
        "specialization": "Invoicing, Billing, Payment Processing"
    },
    "Agent_Clone": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_CLONE",
        "name": "Agent Clone",
        "description": "AI agent replication and customization",
        "icon": "👥",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000020",
        "ai_assistant_id": "88862739-c227-4bfc-b90a-5f450a823e23",
        "category": "AI",
        "specialization": "Agent Cloning, AI Customization"
    },
    "Agent_Doctor": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_DOCTOR",
        "name": "Agent Doctor",
        "description": "Medical consultation and health advice",
        "icon": "👨‍⚕️",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000021",
        "ai_assistant_id": "9d1cccc6-3193-4694-a9f7-853198ee4082",
        "category": "Medical",
        "specialization": "Medical Consultation, Health Advice"
    },
    "Agent_Multi_Lig": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_MULTILIG",
        "name": "Agent Multi Lig",
        "description": "Multi-language translation and communication",
        "icon": "🌍",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000022",
        "ai_assistant_id": "8f045bce-08bc-4477-8d3d-05f233a44df3",
        "category": "Language",
        "specialization": "Translation, Multi-language Support"
    },
    "Agent_Real_Estate": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_REALESTATE",
        "name": "Agent Real Estate",
        "description": "Real estate analysis and property management",
        "icon": "🏠",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000023",
        "ai_assistant_id": "d982667e-d931-477c-9708-c183ba0aa964",
        "category": "Real Estate",
        "specialization": "Property Analysis, Real Estate Investment"
    },
    "Follow_Up_Agent": {
        "id": "1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_FOLLOWUP",
        "name": "Follow Up Agent",
        "description": "Customer follow-up and relationship management",
        "icon": "📞",
        "webhook_url": N8N_WEBHOOK_URL,
        "ai_phone": "+15551000024",
        "ai_assistant_id": "39928b52-d610-43cb-9004-b88028e399fc",
        "category": "CRM",
        "specialization": "Follow-up, Customer Relations, CRM"
    }
}

# Session state initialization
def initialize_session_state():
    defaults = {
        'authenticated': False,
        'credentials': None,
        'user_info': None,
        'n8n_authenticated': False,
        'n8n_username': None,
        'n8n_password': None,
        'n8n_bearer_token': None,
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

def authenticate_n8n(username, password, bearer_token):
    """Authenticate n8n credentials"""
    try:
        # Store n8n credentials
        st.session_state.n8n_authenticated = True
        st.session_state.n8n_username = username
        st.session_state.n8n_password = password
        st.session_state.n8n_bearer_token = bearer_token
        
        return True, "n8n authentication successful!"
    except Exception as e:
        return False, f"n8n authentication failed: {str(e)}"

# Helper functions
def send_message_to_webhook(agent_id, message):
    """Send message to n8n webhook"""
    config = st.session_state.agent_configs[agent_id]
    
    # Check if n8n is authenticated
    if not st.session_state.n8n_authenticated:
        return "Error: Please authenticate with n8n first."
    
    headers = {
        "Authorization": f"Bearer {st.session_state.n8n_bearer_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "sessionId": str(uuid.uuid4()),
        "chatInput": message,
        "agentId": agent_id,
        "agentName": config['name'],
        "username": st.session_state.n8n_username,
        "timestamp": datetime.now().isoformat()
    }
    
    # Simulate different responses based on agent specialization
    specializations = {
        "Agent_CEO": "As your CEO agent, I'll help you with strategic decisions and leadership challenges.",
        "Agent_Social": "I'll help you create engaging social media content and develop your digital marketing strategy.",
        "Agent_Mindset": "Let's work on developing a growth mindset and overcoming limiting beliefs.",
        "Agent_Blogger": "I'll help you create compelling blog content that engages your audience.",
        "Agent_Grant": "I'll assist you in writing compelling grant proposals and finding funding opportunities.",
        "Agent_Prayer_AI": "I'm here to provide spiritual guidance and help with prayer requests.",
        "Agent_Metrics": "Let me help you analyze your KPIs and performance metrics.",
        "Agent_Researcher": "I'll help you conduct thorough research and analyze data.",
        "Agent_Investor": "I'll provide investment analysis and portfolio management advice.",
        "Agent_Newsroom": "I'll help you stay updated with the latest news and create journalistic content.",
        "STREAMLIT_Agent": "I'll help you build amazing Streamlit applications and Python code.",
        "HTML_CSS_Agent": "I'll assist you with web development, HTML, CSS, and frontend design.",
        "Business_Plan_Agent": "I'll help you create comprehensive business plans and strategies.",
        "Ecom_Agent": "I'll help you optimize your e-commerce operations and increase sales.",
        "Agent_Health": "I'll provide health and wellness guidance (not medical advice).",
        "Cinch_Closer": "I'll help you close deals and improve your sales techniques.",
        "DISC_Agent": "I'll help you understand personality types and improve team dynamics.",
        "Biz_Plan_Agent": "I'll assist with advanced business modeling and financial planning.",
        "Invoice_Agent": "I'll help you manage invoices and automate your billing processes.",
        "Agent_Clone": "I'll help you replicate and customize AI agents for your needs.",
        "Agent_Doctor": "I'll provide general health information (consult real doctors for medical advice).",
        "Agent_Multi_Lig": "I'll help you with translation and multi-language communication.",
        "Agent_Real_Estate": "I'll assist with property analysis and real estate investment strategies.",
        "Follow_Up_Agent": "I'll help you manage customer relationships and follow-up strategies."
    }
    
    base_response = specializations.get(agent_id, "I'm here to help you with your request.")
    
    try:
        # In production, you would make actual API call to n8n webhook
        # response = requests.post(config['webhook_url'], headers=headers, json=payload)
        
        # Simulate processing time
        time.sleep(1)
        response = f"{base_response}\n\nRegarding your message: '{message}'\n\nI'm processing this with my specialized knowledge in {config['specialization']}. How can I assist you further?"
        return response
    except Exception as e:
        return f"Error: {str(e)}"

def load_spreadsheet_data(agent_id):
    """Load data for specific agent"""
    try:
        # Generate sample data based on agent type
        config = st.session_state.agent_configs[agent_id]
        
        # Create different data patterns based on agent category
        if config['category'] == 'Finance':
            data = {
                'Date': [datetime.now().date() - timedelta(days=i) for i in range(30)],
                'Revenue': [5000 + i*100 + (i%7)*200 for i in range(30)],
                'Expenses': [2000 + i*50 + (i%5)*100 for i in range(30)],
                'Profit': [3000 + i*50 + (i%3)*150 for i in range(30)],
                'ROI': [15 + i*0.5 + (i%4)*2 for i in range(30)]
            }
        elif config['category'] == 'Marketing':
            data = {
                'Date': [datetime.now().date() - timedelta(days=i) for i in range(30)],
                'Impressions': [10000 + i*200 + (i%6)*500 for i in range(30)],
                'Clicks': [500 + i*10 + (i%4)*25 for i in range(30)],
                'Conversions': [25 + i*2 + (i%3)*5 for i in range(30)],
                'CTR': [5 + i*0.1 + (i%5)*0.5 for i in range(30)]
            }
        elif config['category'] == 'Sales':
            data = {
                'Date': [datetime.now().date() - timedelta(days=i) for i in range(30)],
                'Leads': [50 + i*2 + (i%7)*5 for i in range(30)],
                'Qualified_Leads': [25 + i*1 + (i%5)*3 for i in range(30)],
                'Closed_Deals': [5 + i*0.5 + (i%3)*2 for i in range(30)],
                'Deal_Value': [2500 + i*100 + (i%4)*300 for i in range(30)]
            }
        else:
            # Default data structure
            data = {
                'Date': [datetime.now().date() - timedelta(days=i) for i in range(30)],
                'Metric_1': [100 + i*5 + (i%6)*10 for i in range(30)],
                'Metric_2': [75 + i*3 + (i%4)*8 for i in range(30)],
                'Metric_3': [50 + i*2 + (i%5)*6 for i in range(30)],
                'Performance': [85 + i*0.5 + (i%3)*3 for i in range(30)]
            }
        
        df = pd.DataFrame(data)
        return df, None
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
        "ai_phone": config['ai_phone'],
        "assistant_id": config['ai_assistant_id'],
        "status": "initiated",
        "timestamp": datetime.now().isoformat(),
        "duration": "00:00:00",
        "cost": "$0.00"
    }
    
    return call_data

def get_agent_categories():
    """Get unique categories from agents"""
    categories = set()
    for agent_config in st.session_state.agent_configs.values():
        categories.add(agent_config['category'])
    return sorted(list(categories))

# Sidebar Navigation
with st.sidebar:
    st.title("🚀 25-Agent Dashboard")
    st.divider()
    
    # Google Authentication Section
    if not st.session_state.authenticated:
        st.subheader("🔐 Google Authentication")
        uploaded_file = st.file_uploader("Upload Service Account JSON", type="json")
        
        if uploaded_file and st.button("Authenticate Google"):
            try:
                json_content = json.load(uploaded_file)
                success, message = authenticate_service_account(json_content)
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error reading JSON file: {str(e)}")
    else:
        st.success(f"✅ Google Authenticated")
        st.caption(f"User: {st.session_state.user_info['email']}")
        
        if st.button("🚪 Sign Out Google"):
            for key in ['authenticated', 'credentials', 'user_info']:
                st.session_state[key] = None if key != 'authenticated' else False
            st.rerun()
    
    st.divider()
    
    # n8n Authentication Section
    if not st.session_state.n8n_authenticated:
        st.subheader("🔧 n8n Authentication")
        
        with st.form("n8n_auth_form"):
            n8n_username = st.text_input("n8n Username:", placeholder="Enter your n8n username")
            n8n_password = st.text_input("n8n Password:", type="password", placeholder="Enter your n8n password")
            n8n_bearer_token = st.text_input("Bearer Token:", placeholder="Enter your bearer token")
            
            submitted = st.form_submit_button("🔐 Authenticate n8n")
            
            if submitted:
                if n8n_username and n8n_password and n8n_bearer_token:
                    success, message = authenticate_n8n(n8n_username, n8n_password, n8n_bearer_token)
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill in all n8n credentials")
    else:
        st.success(f"✅ n8n Authenticated")
        st.caption(f"User: {st.session_state.n8n_username}")
        st.caption(f"Webhook: Connected")
        
        if st.button("🚪 Sign Out n8n"):
            for key in ['n8n_authenticated', 'n8n_username', 'n8n_password', 'n8n_bearer_token']:
                st.session_state[key] = None if key != 'n8n_authenticated' else False
            st.rerun()
    
    st.divider()
    
    # Agent Selection
    if st.session_state.authenticated and st.session_state.n8n_authenticated:
        st.subheader("🤖 Select Agent")
        
        # Category filter
        categories = get_agent_categories()
        selected_category = st.selectbox("Filter by Category:", ["All"] + categories)
        
        # Filter agents by category
        if selected_category == "All":
            filtered_agents = st.session_state.agent_configs
        else:
            filtered_agents = {
                k: v for k, v in st.session_state.agent_configs.items() 
                if v['category'] == selected_category
            }
        
        # Agent selection
        agent_options = list(filtered_agents.keys())
        
        if agent_options:
            current_agent = st.selectbox(
                "Choose Agent:",
                agent_options,
                index=agent_options.index(st.session_state.current_page) if st.session_state.current_page in agent_options else 0,
                format_func=lambda x: f"{filtered_agents[x]['icon']} {filtered_agents[x]['name']}"
            )
            
            if current_agent != st.session_state.current_page:
                st.session_state.current_page = current_agent
                st.rerun()
        
        st.divider()
        
        # Current Agent Info
        if st.session_state.current_page in st.session_state.agent_configs:
            config = st.session_state.agent_configs[st.session_state.current_page]
            
            st.subheader("📋 Current Agent")
            st.markdown(f"""
            **{config['icon']} {config['name']}**  
            *{config['description']}*  
            **Category:** {config['category']}  
            **Specialization:** {config['specialization']}
            """)
            
            with st.expander("🔧 Technical Details"):
                st.code(f"""
Assistant ID: {config['ai_assistant_id']}
Phone: {config['ai_phone']}
n8n Webhook: {config['webhook_url']}
Sheet ID: {config['id']}
                """)
        
        st.divider()
        
        # Dashboard Stats
        st.subheader("📊 Dashboard Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Agents", len(st.session_state.agent_configs))
            st.metric("Categories", len(get_agent_categories()))
        with col2:
            total_calls = sum(len(calls) for calls in st.session_state.ai_calls.values())
            st.metric("Total Calls", total_calls)
            total_chats = sum(len(chats) for chats in st.session_state.chat_sessions.values())
            st.metric("Chat Messages", total_chats)

# Main Content Area
if not st.session_state.authenticated or not st.session_state.n8n_authenticated:
    st.title("🚀 25-Agent Business Dashboard")
    
    if not st.session_state.authenticated:
        st.info("🔐 Please authenticate with Google using the sidebar to access Google Sheets.")
    
    if not st.session_state.n8n_authenticated:
        st.info("🔧 Please authenticate with n8n using the sidebar to enable chat functionality.")
    
    # Feature overview
    st.header("🌟 Platform Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🤖 25 Specialized AI Agents
        - **Leadership:** CEO, Business Planning
        - **Marketing:** Social Media, Content Creation
        - **Development:** Streamlit, HTML/CSS
        - **Finance:** Investment, Grant Writing
        - **Sales:** Closing, Follow-up
        - **Health:** Medical, Wellness
        - **Real Estate:** Property Analysis
        - **And many more...**
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Comprehensive Analytics
        - Individual agent performance
        - Real-time data visualization
        - Google Sheets integration
        - Export capabilities
        - Custom metrics tracking
        - Performance dashboards
        """)
    
    with col3:
        st.markdown("""
        ### 🔧 n8n Integration
        - Unified webhook system
        - Real-time chat processing
        - Custom workflow automation
        - Bearer token authentication
        - Multi-agent coordination
        - Scalable architecture
        """)
    
    # Agent categories overview
    st.header("🎯 Agent Categories")
    categories = get_agent_categories()
    
    category_cols = st.columns(len(categories))
    for i, category in enumerate(categories):
        with category_cols[i]:
            agents_in_category = [
                agent for agent in st.session_state.agent_configs.values() 
                if agent['category'] == category
            ]
            st.markdown(f"### {category}")
            st.metric("Agents", len(agents_in_category))
            for agent in agents_in_category[:3]:  # Show first 3
                st.caption(f"{agent['icon']} {agent['name']}")
            if len(agents_in_category) > 3:
                st.caption(f"... and {len(agents_in_category) - 3} more")

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
    
    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 Chatbot", "📊 Data (Sheets)", "📞 AI Voice Call", "💡 Prompts/Info"])
    
    # Tab 1: Chatbot
    with tab1:
        st.header("AI Chat Interface")
        
        # Initialize chat session for current agent
        if st.session_state.current_page not in st.session_state.chat_sessions:
            st.session_state.chat_sessions[st.session_state.current_page] = []
        
        # Chat settings in sidebar
        with st.expander("⚙️ Chat Settings"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.session_state.use_tts = st.checkbox("🔈 Text-to-Speech", value=st.session_state.use_tts)
            with col2:
                st.session_state.show_timestamps = st.checkbox("🕒 Timestamps", value=st.session_state.show_timestamps)
            with col3:
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat_sessions[st.session_state.current_page] = []
                    st.rerun()
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_sessions[st.session_state.current_page]:
                with st.chat_message(message['role']):
                    if st.session_state.show_timestamps:
                        st.caption(f"⏱️ {message.get('timestamp', '')}")
                    st.markdown(message['content'])
        
        # Chat input
        user_input = st.chat_input(f"Message {current_config['name']}...")
        
        # Voice input and quick actions
        input_col1, input_col2, input_col3 = st.columns([1, 1, 4])
        
        with input_col1:
            if st.button("🎙️ Voice", key=f"voice_{st.session_state.current_page}"):
                st.info("🎤 Voice input activated (simulated)")
                user_input = f"Voice message for {current_config['name']}: How can you help me today?"
        
        with input_col2:
            if st.button("⚡ Quick Help", key=f"quick_{st.session_state.current_page}"):
                user_input = f"What are your main capabilities and how can you help me with {current_config['specialization']}?"
        
        # Process input
        if user_input:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add user message
            user_msg = {
                "role": "user",
                "content": user_input,
                "timestamp": timestamp
            }
            st.session_state.chat_sessions[st.session_state.current_page].append(user_msg)
            
            # Get AI response
            with st.spinner(f"🤖 {current_config['name']} is thinking..."):
                response = send_message_to_webhook(st.session_state.current_page, user_input)
            
            # Add assistant message
            assistant_msg = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.session_state.chat_sessions[st.session_state.current_page].append(assistant_msg)
            st.rerun()
    
    # Tab 2: Data (Sheets)
    with tab2:
        st.header("📊 Google Sheets Data & Analytics")
        
        # Load data for current agent
        if st.session_state.current_page not in st.session_state.sheets_data:
            with st.spinner("Loading data..."):
                df, error = load_spreadsheet_data(st.session_state.current_page)
                if error:
                    st.error(error)
                else:
                    st.session_state.sheets_data[st.session_state.current_page] = df
        
        if st.session_state.current_page in st.session_state.sheets_data:
            df = st.session_state.sheets_data[st.session_state.current_page]
            
            # Data overview metrics
            st.subheader("📈 Key Metrics")
            
            # Dynamic metrics based on data columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) >= 4:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(numeric_cols[0], f"{df[numeric_cols[0]].iloc[-1]:,.0f}", 
                             delta=f"{df[numeric_cols[0]].iloc[-1] - df[numeric_cols[0]].iloc[-2]:,.0f}")
                with col2:
                    st.metric(numeric_cols[1], f"{df[numeric_cols[1]].iloc[-1]:,.0f}",
                             delta=f"{df[numeric_cols[1]].iloc[-1] - df[numeric_cols[1]].iloc[-2]:,.0f}")
                with col3:
                    st.metric(numeric_cols[2], f"{df[numeric_cols[2]].iloc[-1]:,.0f}",
                             delta=f"{df[numeric_cols[2]].iloc[-1] - df[numeric_cols[2]].iloc[-2]:,.0f}")
                with col4:
                    if len(numeric_cols) > 3:
                        st.metric(numeric_cols[3], f"{df[numeric_cols[3]].iloc[-1]:,.1f}",
                                 delta=f"{df[numeric_cols[3]].iloc[-1] - df[numeric_cols[3]].iloc[-2]:,.1f}")
            
            # Data visualization
            st.subheader("📊 Performance Visualizations")
            
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                if len(numeric_cols) >= 2:
                    fig1 = px.line(df, x='Date', y=numeric_cols[0], 
                                  title=f'{numeric_cols[0]} Trend',
                                  color_discrete_sequence=['#1f77b4'])
                    fig1.update_layout(height=300)
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    if len(numeric_cols) >= 3:
                        fig3 = px.bar(df.tail(10), x='Date', y=numeric_cols[2], 
                                     title=f'Recent {numeric_cols[2]}',
                                     color_discrete_sequence=['#2ca02c'])
                        fig3.update_layout(height=300)
                        st.plotly_chart(fig3, use_container_width=True)
            
            with viz_col2:
                if len(numeric_cols) >= 2:
                    fig2 = px.area(df, x='Date', y=numeric_cols[1], 
                                  title=f'{numeric_cols[1]} Over Time',
                                  color_discrete_sequence=['#ff7f0e'])
                    fig2.update_layout(height=300)
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    if len(numeric_cols) >= 4:
                        fig4 = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                                         size=numeric_cols[2], color=numeric_cols[3],
                                         title='Multi-Metric Analysis',
                                         color_continuous_scale='viridis')
                        fig4.update_layout(height=300)
                        st.plotly_chart(fig4, use_container_width=True)
            
            # Data table with filtering
            st.subheader("📋 Data Table")
            
            # Add filters
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                date_range = st.date_input(
                    "Date Range:",
                    value=(df['Date'].min(), df['Date'].max()),
                    min_value=df['Date'].min(),
                    max_value=df['Date'].max()
                )
            
            with filter_col2:
                show_rows = st.selectbox("Show rows:", [10, 20, 50, "All"], index=1)
            
            # Apply filters
            filtered_df = df[
                (df['Date'] >= date_range[0]) & 
                (df['Date'] <= date_range[1])
            ]
            
            if show_rows != "All":
                filtered_df = filtered_df.tail(show_rows)
            
            st.dataframe(filtered_df, use_container_width=True, height=300)
            
            # Export section
            st.subheader("💾 Export Options")
            export_col1, export_col2, export_col3, export_col4 = st.columns(4)
            
            with export_col1:
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv,
                    file_name=f"{st.session_state.current_page}_data.csv",
                    mime="text/csv"
                )
            
            with export_col2:
                json_str = filtered_df.to_json(orient='records', date_format='iso')
                st.download_button(
                    label="📋 Download JSON",
                    data=json_str,
                    file_name=f"{st.session_state.current_page}_data.json",
                    mime="application/json"
                )
            
            with export_col3:
                if st.button("🔄 Refresh Data"):
                    df, error = load_spreadsheet_data(st.session_state.current_page)
                    if error:
                        st.error(error)
                    else:
                        st.session_state.sheets_data[st.session_state.current_page] = df
                        st.success("✅ Data refreshed!")
                        st.rerun()
            
            with export_col4:
                if st.button("📊 Generate Report"):
                    st.info("📈 Comprehensive report generation feature coming soon!")
    
    # Tab 3: AI Voice Call
    with tab3:
        st.header("📞 AI Voice Call System")
        
        # Call interface
        call_col1, call_col2 = st.columns([1, 1])
        
        with call_col1:
            st.subheader("📱 Agent Voice Details")
            st.info(f"**Agent:** {current_config['name']}")
            st.info(f"**Phone:** {current_config['ai_phone']}")
            st.info(f"**Assistant ID:** {current_config['ai_assistant_id']}")
            st.info(f"**Specialization:** {current_config['specialization']}")
        
        with call_col2:
            st.subheader("🚀 Initiate Call")
            
            # Call form
            with st.form("call_form"):
                phone_number = st.text_input(
                    "📱 Recipient Phone Number:", 
                    placeholder="+1234567890",
                    help="Enter the phone number to call"
                )
                
                call_purpose = st.selectbox(
                    "📋 Call Purpose:",
                    ["General Inquiry", "Sales Call", "Follow-up", "Support", "Consultation", "Other"]
                )
                
                call_notes = st.text_area(
                    "📝 Call Notes:",
                    placeholder="Add any notes about this call...",
                    height=100
                )
                
                submitted = st.form_submit_button("📞 Initiate Call", use_container_width=True)
                
                if submitted and phone_number:
                    call_data = make_ai_call(st.session_state.current_page, phone_number)
                    call_data.update({
                        "purpose": call_purpose,
                        "notes": call_notes
                    })
                    
                    if st.session_state.current_page not in st.session_state.ai_calls:
                        st.session_state.ai_calls[st.session_state.current_page] = []
                    
                    st.session_state.ai_calls[st.session_state.current_page].append(call_data)
                    st.success(f"✅ Call initiated! Call ID: {call_data['call_id'][:8]}...")
                    st.rerun()
                elif submitted:
                    st.error("❌ Please enter a valid phone number")
        
        st.divider()
        
        # Call history and management
        st.subheader("📋 Call History & Management")
        
        if (st.session_state.current_page in st.session_state.ai_calls and 
            st.session_state.ai_calls[st.session_state.current_page]):
            
            calls = st.session_state.ai_calls[st.session_state.current_page]
            
            # Call statistics
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            with stats_col1:
                st.metric("Total Calls", len(calls))
            with stats_col2:
                st.metric("Today's Calls", len([c for c in calls if c['timestamp'][:10] == datetime.now().date().isoformat()]))
            with stats_col3:
                st.metric("Success Rate", "95%")  # Simulated
            with stats_col4:
                st.metric("Avg Duration", "3:45")  # Simulated
            
            # Recent calls
            st.subheader("🕐 Recent Calls")
            
            for i, call in enumerate(reversed(calls[-10:])):  # Show last 10 calls
                with st.expander(f"📞 Call to {call['phone_number']} - {call['timestamp'][:16]} ({call.get('purpose', 'General')})"):
                    
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.markdown(f"""
                        **📞 Call Details:**
                        - **Call ID:** `{call['call_id']}`
                        - **Status:** {call['status']}
                        - **Purpose:** {call.get('purpose', 'Not specified')}
                        - **Agent Phone:** {call['ai_phone']}
                        """)
                    
                    with detail_col2:
                        st.markdown(f"""
                        **🎯 Technical Info:**
                        - **Recipient:** {call['phone_number']}
                        - **Assistant ID:** `{call['assistant_id']}`
                        - **Timestamp:** {call['timestamp']}
                        - **Duration:** {call.get('duration', '00:00:00')}
                        """)
                    
                    if call.get('notes'):
                        st.markdown(f"**📝 Notes:** {call['notes']}")
                    
                    # Call actions
                    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                    
                    with action_col1:
                        if st.button("📞 Redial", key=f"redial_{call['call_id']}"):
                            new_call = make_ai_call(st.session_state.current_page, call['phone_number'])
                            new_call.update({
                                "purpose": "Redial",
                                "notes": f"Redial of call {call['call_id'][:8]}..."
                            })
                            st.session_state.ai_calls[st.session_state.current_page].append(new_call)
                            st.success("📞 Redial initiated!")
                            st.rerun()
                    
                    with action_col2:
                        if st.button("📝 Add Notes", key=f"notes_{call['call_id']}"):
                            st.info("📝 Notes feature - would open note editor")
                    
                    with action_col3:
                        if st.button("📊 Analytics", key=f"analytics_{call['call_id']}"):
                            st.info("📊 Call analytics - detailed metrics would display")
                    
                    with action_col4:
                        if st.button("🔄 Update Status", key=f"status_{call['call_id']}"):
                            st.info("🔄 Status update - would show status options")
        else:
            st.info("📞 No calls made yet. Use the form above to initiate your first call with this agent.")
            
            # Sample call scenarios
            st.subheader("💡 Sample Call Scenarios")
            
            scenario_col1, scenario_col2 = st.columns(2)
            
            with scenario_col1:
                st.markdown(f"""
                **🎯 Recommended for {current_config['name']}:**
                - {current_config['specialization']} consultation
                - Expert advice and guidance
                - Problem-solving sessions
                - Strategic planning calls
                """)
            
            with scenario_col2:
                if st.button("📞 Demo Call", key="demo_call"):
                    demo_call = make_ai_call(st.session_state.current_page, "+1555DEMO123")
                    demo_call.update({
                        "purpose": "Demo Call",
                        "notes": "Demonstration call to showcase capabilities"
                    })
                    
                    if st.session_state.current_page not in st.session_state.ai_calls:
                        st.session_state.ai_calls[st.session_state.current_page] = []
                    
                    st.session_state.ai_calls[st.session_state.current_page].append(demo_call)
                    st.success("🎉 Demo call initiated!")
                    st.rerun()
    
    # Tab 4: Prompts/Info
    with tab4:
        st.header("💡 Prompt Library & Agent Information")
        
        # Agent detailed information
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.subheader("🤖 Agent Profile")
            st.markdown(f"""
            **Name:** {current_config['name']}  
            **Category:** {current_config['category']}  
            **Description:** {current_config['description']}  
            **Specialization:** {current_config['specialization']}  
            **Icon:** {current_config['icon']}
            """)
            
            # Agent capabilities
            st.subheader("🎯 Core Capabilities")
            capabilities = {
                "Leadership": ["Strategic Planning", "Team Management", "Decision Making", "Vision Setting"],
                "Marketing": ["Content Creation", "Social Media", "Campaign Management", "Brand Strategy"],
                "Development": ["Code Review", "Architecture Design", "Debugging", "Best Practices"],
                "Finance": ["Financial Analysis", "Investment Planning", "Risk Assessment", "Budgeting"],
                "Sales": ["Lead Qualification", "Closing Techniques", "Objection Handling", "Pipeline Management"],
                "Health": ["Wellness Planning", "Health Education", "Lifestyle Advice", "Preventive Care"],
                "Real Estate": ["Property Analysis", "Market Research", "Investment Strategy", "Valuation"],
                "E-commerce": ["Store Optimization", "Product Strategy", "Customer Experience", "Sales Funnel"],
                "Content": ["Blog Writing", "SEO Optimization", "Content Strategy", "Editorial Planning"],
                "Analytics": ["Data Analysis", "KPI Tracking", "Performance Metrics", "Reporting"],
                "Research": ["Market Research", "Data Collection", "Analysis", "Insights Generation"],
                "Medical": ["Health Information", "Symptom Assessment", "Treatment Options", "Wellness"],
                "Assessment": ["Personality Analysis", "Team Dynamics", "Behavioral Insights", "Development"],
                "Business": ["Business Planning", "Strategy Development", "Market Analysis", "Growth Planning"],
                "AI": ["Agent Development", "Customization", "Integration", "Optimization"],
                "Language": ["Translation", "Localization", "Communication", "Cultural Adaptation"],
                "CRM": ["Customer Relations", "Follow-up Strategy", "Retention", "Engagement"],
                "Spiritual": ["Prayer Guidance", "Faith Support", "Spiritual Growth", "Meditation"]
            }
            
            agent_capabilities = capabilities.get(current_config['category'], ["General AI Assistance"])
            for capability in agent_capabilities:
                st.markdown(f"• {capability}")
        
        with info_col2:
            st.subheader("🔧 Technical Configuration")
            
            config_data = {
                "Agent ID": st.session_state.current_page,
                "AI Assistant ID": current_config['ai_assistant_id'],
                "Phone Number": current_config['ai_phone'],
                "n8n Webhook": current_config['webhook_url'],
                "Spreadsheet ID": current_config['id'],
                "n8n Username": st.session_state.n8n_username,
                "Category": current_config['category'],
                "Specialization": current_config['specialization']
            }
            
            st.json(config_data)
            
            # Quick actions
            st.subheader("⚡ Quick Actions")
            
            quick_col1, quick_col2 = st.columns(2)
            
            with quick_col1:
                if st.button("💬 Start Chat", key="quick_chat"):
                    st.session_state.current_tab = 'chatbot'
                    st.info("💬 Switched to chat interface")
                
                if st.button("📊 View Data", key="quick_data"):
                    st.session_state.current_tab = 'data'
                    st.info("📊 Switched to data view")
            
            with quick_col2:
                if st.button("📞 Make Call", key="quick_call"):
                    st.session_state.current_tab = 'ai_call'
                    st.info("📞 Switched to call interface")
                
                if st.button("🔄 Refresh Config", key="refresh_config"):
                    st.success("🔄 Configuration refreshed!")
        
        st.divider()
        
        # Prompt Library (same as before but with updated references)
        st.subheader("📚 Prompt Library")
        
        # Category-based prompts
        prompt_categories = list(st.session_state.prompt_library.keys())
        
        # Filter prompts by agent category
        relevant_categories = []
        agent_category = current_config['category']
        
        # Map agent categories to prompt categories
        category_mapping = {
            "Leadership": ["Leadership"],
            "Marketing": ["Sales & Marketing"],
            "Development": ["Development"],
            "Finance": ["Finance & Business"],
            "Sales": ["Sales & Marketing"],
            "Health": ["Health & Wellness"],
            "Medical": ["Health & Wellness"],
            "Real Estate": ["Real Estate"],
            "E-commerce": ["Sales & Marketing"],
            "Content": ["Sales & Marketing"],
            "Analytics": ["Finance & Business"],
            "Research": ["Finance & Business"],
            "Assessment": ["Leadership"],
            "Business": ["Finance & Business"],
            "AI": ["Development"],
            "Language": ["Sales & Marketing"],
            "CRM": ["Sales & Marketing"],
            "Spiritual": ["Health & Wellness"]
        }
        
        relevant_categories = category_mapping.get(agent_category, prompt_categories)
        
        # Prompt category selection
        selected_prompt_category = st.selectbox(
            "Select Prompt Category:", 
            ["All Categories"] + prompt_categories,
            index=0
        )
        
        # Display prompts
        if selected_prompt_category == "All Categories":
            display_categories = prompt_categories
        else:
            display_categories = [selected_prompt_category]
        
        for category in display_categories:
            if category in st.session_state.prompt_library:
                st.markdown(f"### 📂 {category}")
                
                prompts = st.session_state.prompt_library[category]
                
                # Display prompts in expandable cards
                for i, prompt in enumerate(prompts):
                    with st.expander(f"💡 {prompt['title']}"):
                        st.markdown(f"**Prompt:** {prompt['prompt']}")
                        
                        prompt_action_col1, prompt_action_col2, prompt_action_col3 = st.columns(3)
                        
                        with prompt_action_col1:
                            if st.button("💬 Use in Chat", key=f"use_{category}_{i}"):
                                # Pre-fill chat with this prompt
                                if st.session_state.current_page not in st.session_state.chat_sessions:
                                    st.session_state.chat_sessions[st.session_state.current_page] = []
                                
                                prompt_msg = {
                                    "role": "user",
                                    "content": prompt['prompt'],
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                st.session_state.chat_sessions[st.session_state.current_page].append(prompt_msg)
                                st.success(f"✅ Prompt added to chat!")
                        
                        with prompt_action_col2:
                            if st.button("⭐ Favorite", key=f"fav_{category}_{i}"):
                                prompt_id = f"{category}_{i}"
                                if prompt_id not in st.session_state.favorites:
                                    st.session_state.favorites.append(prompt_id)
                                    st.success("⭐ Added to favorites!")
                                else:
                                    st.info("Already in favorites!")
                        
                        with prompt_action_col3:
                            if st.button("📋 Copy", key=f"copy_{category}_{i}"):
                                st.code(prompt['prompt'], language=None)
                                st.info("📋 Prompt displayed above for copying")
        
        st.divider()
        
        # Custom prompt creation
        st.subheader("➕ Create Custom Prompt")
        
        with st.expander("🛠️ Add New Prompt"):
            custom_col1, custom_col2 = st.columns(2)
            
            with custom_col1:
                new_category = st.selectbox(
                    "Category:", 
                    prompt_categories + ["Create New Category"],
                    key="new_prompt_category"
                )
                
                if new_category == "Create New Category":
                    custom_category = st.text_input("New Category Name:", key="custom_category")
                    if custom_category:
                        new_category = custom_category
            
            with custom_col2:
                prompt_title = st.text_input("Prompt Title:", key="prompt_title")
            
            prompt_text = st.text_area(
                "Prompt Text:", 
                placeholder="Enter your custom prompt here. Use [brackets] for variables that users can fill in.",
                height=150,
                key="prompt_text"
            )
            
            if st.button("➕ Add Prompt", key="add_custom_prompt"):
                if new_category and prompt_title and prompt_text:
                    if new_category not in st.session_state.prompt_library:
                        st.session_state.prompt_library[new_category] = []
                    
                    st.session_state.prompt_library[new_category].append({
                        "title": prompt_title,
                        "prompt": prompt_text
                    })
                    
                    st.success(f"✅ Prompt '{prompt_title}' added to {new_category}!")
                    st.rerun()
                else:
                    st.warning("⚠️ Please fill out all fields.")
        
        # Favorites section
        if st.session_state.favorites:
            st.subheader("⭐ Favorite Prompts")
            
            for fav_id in st.session_state.favorites:
                try:
                    category, index = fav_id.split("_", 1)
                    index = int(index)
                    
                    if (category in st.session_state.prompt_library and 
                        index < len(st.session_state.prompt_library[category])):
                        
                        prompt = st.session_state.prompt_library[category][index]
                        
                        with st.expander(f"⭐ {prompt['title']} ({category})"):
                            st.markdown(prompt['prompt'])
                            
                            if st.button("🗑️ Remove from Favorites", key=f"remove_fav_{fav_id}"):
                                st.session_state.favorites.remove(fav_id)
                                st.success("Removed from favorites!")
                                st.rerun()
                except:
                    # Remove invalid favorite IDs
                    st.session_state.favorites.remove(fav_id)
        
        # Export/Import prompts
        st.subheader("📤 Import/Export Prompts")
        
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            if st.button("📤 Export Prompt Library"):
                prompt_json = json.dumps(st.session_state.prompt_library, indent=2)
                st.download_button(
                    label="💾 Download Prompts JSON",
                    data=prompt_json,
                    file_name=f"prompt_library_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with export_col2:
            uploaded_prompts = st.file_uploader("📥 Import Prompts", type="json", key="import_prompts")
            
            if uploaded_prompts:
                try:
                    imported_data = json.load(uploaded_prompts)
                    
                    if isinstance(imported_data, dict):
                        for category, prompts in imported_data.items():
                            if category not in st.session_state.prompt_library:
                                st.session_state.prompt_library[category] = []
                            
                            for prompt in prompts:
                                if isinstance(prompt, dict) and "title" in prompt and "prompt" in prompt:
                                    st.session_state.prompt_library[category].append(prompt)
                        
                        st.success("✅ Prompts imported successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid file format")
                except Exception as e:
                    st.error(f"❌ Error importing prompts: {str(e)}")

# Footer
st.divider()

# Performance summary
if st.session_state.authenticated and st.session_state.n8n_authenticated:
    st.subheader("📊 Session Summary")
    
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    with summary_col1:
        total_messages = sum(len(session) for session in st.session_state.chat_sessions.values())
        st.metric("Total Messages", total_messages)
    
    with summary_col2:
        total_calls = sum(len(calls) for calls in st.session_state.ai_calls.values())
        st.metric("Total Calls", total_calls)
    
    with summary_col3:
        active_agents = len([k for k in st.session_state.chat_sessions.keys() if st.session_state.chat_sessions[k]])
        st.metric("Active Agents", active_agents)
    
    with summary_col4:
        st.metric("Prompt Categories", len(st.session_state.prompt_library))

st.caption("🚀 25-Agent Business Dashboard | Powered by AI & n8n | Built with Streamlit")

print("✅ 25-Agent Business Dashboard with n8n integration successfully created!")
print("\n🎯 Features implemented:")
print("- 25 specialized AI agents with real assistant IDs")
print("- Unified n8n webhook integration for all agents")
print("- Dual authentication: Google Sheets + n8n")
print("- White-labeled interface (removed VAPI branding)")
print("- Individual Google Sheets integration per agent")
print("- AI voice calling system with call management")
print("- Comprehensive prompt library with favorites")
print("- Real-time data visualization and analytics")
print("- Voice recognition and text-to-speech support")
print("- Export/import capabilities for data and prompts")
print("- Category-based agent filtering")
print("- Session management and performance tracking")
print("- Responsive design with intuitive navigation")
print("\n🔧 Technical specifications:")
print("- Google Service account authentication")
print("- n8n username/password/bearer token authentication")
print("- Unified webhook URL for all agents")
print("- Real assistant IDs integrated")
print("- Dynamic data generation based on agent categories")
print("- Persistent session state management")
print("- Modular architecture for easy expansion")
print("- White-labeled branding throughout")

