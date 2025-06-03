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
        'chat_sessions': {},
        'recognizer': sr.Recognizer(),
        'use_tts': True,
        'show_timestamps': False,
        'recording_status': False,
        'ai_calls': {},
        'agent_configs': AGENTS_CONFIG,
        'prompt_library': {
            "Leadership": [
                {"title": "Strategic Planning", "prompt": "Help me develop a strategic plan for my business."},
                {"title": "Executive Decisions", "prompt": "What should I consider before making a major executive decision?"}
            ],
            "Marketing": [
                {"title": "Social Strategy", "prompt": "Suggest a social media strategy for a new product."},
                {"title": "Content Ideas", "prompt": "Give me 5 blog post ideas for my brand."}
            ],
            "Development": [
                {"title": "Python Help", "prompt": "How do I create a Streamlit app?"},
                {"title": "Frontend Tips", "prompt": "Best practices for responsive web design?"}
            ],
            "Finance": [
                {"title": "Grant Search", "prompt": "Find grants for small businesses."},
                {"title": "Investment Advice", "prompt": "What are safe investment options for 2024?"}
            ]
            # Add more prompt libraries as needed per category
        }
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- Chatbot Page Implementation (Modern Multi-turn) ---
def send_message_to_agent(agent_config, message, session_id):
    # Simulate sending a message to the agent's webhook and getting a response
    headers = {
        "Authorization": f"Bearer {agent_config['bearer_token']}",
        "Content-Type": "application/json"
    }
    payload = {
        "assistant_id": agent_config["ai_assistant_id"],
        "session_id": session_id,
        "message": message
    }
    try:
        response = requests.post(agent_config["webhook_url"], headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "No response from agent.")
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error contacting agent: {str(e)}"

def render_chatbot_page(agent_key, agent_config):
    st.markdown(f"### {agent_config['icon']} {agent_config['name']} Chatbot")
    st.caption(agent_config['description'])

    # Use a unique session for each agent
    if 'chat_sessions' not in st.session_state:
        st.session_state['chat_sessions'] = {}
    if agent_key not in st.session_state['chat_sessions']:
        st.session_state['chat_sessions'][agent_key] = {
            "session_id": str(uuid.uuid4()),
            "history": []
        }

    chat_session = st.session_state['chat_sessions'][agent_key]

    # Display chat history
    for entry in chat_session["history"]:
        if entry["role"] == "user":
            st.markdown(f"<div style='text-align:right; background:#e6f7ff; padding:8px; border-radius:8px; margin-bottom:4px'><b>You:</b> {entry['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:left; background:#f6f6f6; padding:8px; border-radius:8px; margin-bottom:4px'><b>{agent_config['name']}:</b> {entry['content']}</div>", unsafe_allow_html=True)

    # User input
    with st.form(key=f"chat_input_form_{agent_key}", clear_on_submit=True):
        user_input = st.text_input("Type your message...", key=f"chat_input_{agent_key}")
        submitted = st.form_submit_button("Send")
    if submitted and user_input.strip():
        chat_session["history"].append({"role": "user", "content": user_input})
        with st.spinner("Agent is replying..."):
            response = send_message_to_agent(agent_config, user_input, chat_session["session_id"])
        chat_session["history"].append({"role": "agent", "content": response})
        st.experimental_rerun()

    # Option to clear chat
    if st.button("Clear Conversation", key=f"clear_{agent_key}"):
        chat_session["history"] = []

    # Optionally, add prompt library buttons
    st.markdown("---")
    st.markdown("#### Quick Prompts")
    prompts = st.session_state['prompt_library'].get(agent_config["category"], [])
    if prompts:
        cols = st.columns(len(prompts))
        for i, prompt in enumerate(prompts):
            if cols[i].button(prompt["title"], key=f"prompt_{agent_key}_{i}"):
                chat_session["history"].append({"role": "user", "content": prompt["prompt"]})
                with st.spinner("Agent is replying..."):
                    response = send_message_to_agent(agent_config, prompt["prompt"], chat_session["session_id"])
                chat_session["history"].append({"role": "agent", "content": response})
                st.experimental_rerun()

# --- Dashboard Page (Placeholder) ---
def render_dashboard_page(agent_key, agent_config):
    st.markdown(f"### {agent_config['icon']} {agent_config['name']} Dashboard")
    st.info("Dashboard features coming soon!")

# --- Settings Page (Placeholder) ---
def render_settings_page(agent_key, agent_config):
    st.markdown(f"### ⚙️ Settings for {agent_config['name']}")
    st.info("Settings features coming soon!")

# --- Main App ---
def main():
    initialize_session_state()
    st.sidebar.title("25-Agent Business Dashboard")
    agent_keys = list(AGENTS_CONFIG.keys())
    agent_names = [AGENTS_CONFIG[k]['name'] for k in agent_keys]
    selected_agent_idx = st.sidebar.selectbox("Select Agent", range(len(agent_keys)), format_func=lambda i: agent_names[i])
    selected_agent_key = agent_keys[selected_agent_idx]
    selected_agent_config = AGENTS_CONFIG[selected_agent_key]

    # Tab navigation
    tabs = ["chatbot", "dashboard", "settings"]
    selected_tab = st.sidebar.radio("Select Tab", tabs, format_func=lambda t: t.capitalize())
    st.session_state['current_tab'] = selected_tab

    # Render the selected tab
    if selected_tab == "chatbot":
        render_chatbot_page(selected_agent_key, selected_agent_config)
    elif selected_tab == "dashboard":
        render_dashboard_page(selected_agent_key, selected_agent_config)
    elif selected_tab == "settings":
        render_settings_page(selected_agent_key, selected_agent_config)

if __name__ == "__main__":
    main()
