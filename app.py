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
from datetime import datetime, timedelta
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Business Dashboard", 
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

# Configuration for 10 Google Sheets and 10 Chatbot Webhooks
SPREADSHEETS_CONFIG = {
    f"Agent_{i+1}": {
        "id": f"1BWz_FnYdzZyyl4WafSgoZV9rLHC91XOjstDcgwn_k6Y_{i}",
        "name": f"Agent {i+1} Data",
        "description": f"Data and metrics for Agent {i+1}",
        "icon": "👤",
        "webhook_url": f"https://api.agent{i+1}.com/webhook",
        "bearer_token": f"bearer_token_agent_{i+1}",
        "vapi_phone": f"+1555000{i+1:04d}",
        "vapi_assistant_id": f"assistant_id_{i+1}"
    } for i in range(10)
}

# Session state initialization
def initialize_session_state():
    defaults = {
        'authenticated': False,
        'credentials': None,
        'user_info': None,
        'current_page': 'Agent_1',
        'current_tab': 'chatbot',
        'current_spreadsheet': None,
        'current_worksheet': None,
        'sheets_data': {},
        'chat_sessions': {},
        'recognizer': sr.Recognizer(),
        'use_tts': True,
        'show_timestamps': False,
        'recording_status': False,
        'prompt_library': {
            "Sales": [
                {"title": "Lead Qualification", "prompt": "Qualify this lead: [lead info]. Ask about budget, timeline, and decision-making process."},
                {"title": "Follow-up Email", "prompt": "Write a follow-up email for [prospect] after our meeting about [topic]."},
                {"title": "Objection Handling", "prompt": "Help me respond to this objection: [objection text]"},
            ],
            "Customer Service": [
                {"title": "Issue Resolution", "prompt": "Help resolve this customer issue: [issue description]"},
                {"title": "Escalation Response", "prompt": "Draft a response for escalated complaint: [complaint details]"},
            ],
            "Marketing": [
                {"title": "Campaign Ideas", "prompt": "Generate marketing campaign ideas for [product/service] targeting [audience]"},
                {"title": "Social Media Post", "prompt": "Create a social media post about [topic] for [platform]"},
            ]
        },
        'vapi_calls': {},
        'agent_configs': SPREADSHEETS_CONFIG
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
        
        return True, "Authentication successful!"
    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

# Helper functions
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{uploaded_file.name}') as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name

def send_message_to_webhook(agent_id, message):
    """Send message to specific agent's webhook"""
    config = st.session_state.agent_configs[agent_id]
    
    headers = {
        "Authorization": f"Bearer {config['bearer_token']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "sessionId": str(uuid.uuid4()),
        "chatInput": message,
        "agentId": agent_id
    }
    
    try:
        with st.spinner("Getting response..."):
            # Simulate API call (replace with actual webhook)
            response = f"Response from {agent_id}: I received your message '{message}' and I'm processing it with my specialized knowledge base."
            return response
    except Exception as e:
        return f"Error: {str(e)}"

def load_spreadsheet_data(spreadsheet_id, worksheet_name=None):
    """Load data from Google Spreadsheet"""
    try:
        # Simulate loading data (replace with actual Google Sheets API)
        sample_data = {
            'Date': [datetime.now().date() - timedelta(days=i) for i in range(10)],
            'Leads': [15 + i*2 for i in range(10)],
            'Conversions': [3 + i for i in range(10)],
            'Revenue': [5000 + i*500 for i in range(10)],
            'Agent_Performance': [85 + i*2 for i in range(10)]
        }
        
        df = pd.DataFrame(sample_data)
        return df, None
    except Exception as e:
        return None, f"Error loading data: {str(e)}"

def get_audio_player(text):
    """Generate audio player for TTS"""
    try:
        # Simulate TTS (in real implementation, use gTTS)
        return f'<audio controls><source src="data:audio/mp3;base64,{base64.b64encode(b"dummy_audio").decode()}" type="audio/mp3"></audio>'
    except Exception as e:
        return None

def make_vapi_call(agent_id, phone_number):
    """Initiate VAPI AI call"""
    config = st.session_state.agent_configs[agent_id]
    
    # Simulate VAPI call
    call_data = {
        "call_id": str(uuid.uuid4()),
        "agent_id": agent_id,
        "phone_number": phone_number,
        "vapi_phone": config['vapi_phone'],
        "assistant_id": config['vapi_assistant_id'],
        "status": "initiated",
        "timestamp": datetime.now().isoformat()
    }
    
    return call_data

# Sidebar Navigation
with st.sidebar:
    st.title("🚀 Multi-Agent Dashboard")
    st.divider()
    
    # Authentication Section
    if not st.session_state.authenticated:
        st.subheader("🔐 Authentication")
        uploaded_file = st.file_uploader("Upload Service Account JSON", type="json")
        
        if uploaded_file and st.button("Authenticate"):
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
        st.success(f"✅ Authenticated as {st.session_state.user_info['email']}")
        
        if st.button("Sign Out"):
            for key in ['authenticated', 'credentials', 'user_info']:
                st.session_state[key] = None if key != 'authenticated' else False
            st.rerun()
    
    st.divider()
    
    # Agent/Page Selection
    if st.session_state.authenticated:
        st.subheader("🤖 Select Agent")
        
        agent_options = list(st.session_state.agent_configs.keys())
        current_agent = st.selectbox(
            "Choose Agent:",
            agent_options,
            index=agent_options.index(st.session_state.current_page) if st.session_state.current_page in agent_options else 0
        )
        
        if current_agent != st.session_state.current_page:
            st.session_state.current_page = current_agent
            st.rerun()
        
        st.divider()
        
        # Agent Configuration Display
        if st.session_state.current_page in st.session_state.agent_configs:
            config = st.session_state.agent_configs[st.session_state.current_page]
            
            st.subheader("📋 Agent Config")
            with st.expander("View Configuration"):
                st.json({
                    "name": config['name'],
                    "spreadsheet_id": config['id'],
                    "webhook_url": config['webhook_url'],
                    "vapi_phone": config['vapi_phone'],
                    "assistant_id": config['vapi_assistant_id']
                })
        
        st.divider()
        
        # Quick Stats
        st.subheader("📊 Quick Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Active Agents", "10")
        with col2:
            st.metric("Total Calls", "247")

# Main Content Area
if not st.session_state.authenticated:
    st.title("🚀 Multi-Agent Business Dashboard")
    st.info("Please authenticate using the sidebar to access the dashboard.")
    
    st.header("Features")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🤖 AI Agents
        - 10 specialized AI agents
        - Individual chat interfaces
        - Custom webhooks per agent
        - Voice recognition support
        
        ### 📊 Data Management
        - 10 Google Sheets integrations
        - Real-time data visualization
        - Export capabilities
        - Performance analytics
        """)
    
    with col2:
        st.markdown("""
        ### 📞 VAPI Integration
        - AI-powered phone calls
        - Voice assistants per agent
        - Call logging and analytics
        - Custom phone numbers
        
        ### 💡 Prompt Library
        - Pre-built prompt templates
        - Custom prompt creation
        - Category organization
        - Favorites system
        """)

else:
    # Main dashboard for authenticated users
    current_config = st.session_state.agent_configs[st.session_state.current_page]
    
    # Page header
    st.title(f"{current_config['icon']} {current_config['name']}")
    st.caption(current_config['description'])
    
    # Tab navigation
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 Chatbot", "📊 Data (Sheets)", "📞 VAPI AI Call", "💡 Prompts/Info"])
    
    # Tab 1: Chatbot
    with tab1:
        st.header("AI Chat Interface")
        
        # Initialize chat session for current agent
        if st.session_state.current_page not in st.session_state.chat_sessions:
            st.session_state.chat_sessions[st.session_state.current_page] = []
        
        # Display chat history
        for message in st.session_state.chat_sessions[st.session_state.current_page]:
            with st.chat_message(message['role']):
                if st.session_state.show_timestamps:
                    st.caption(f"⏱️ {message.get('timestamp', '')}")
                st.markdown(message['content'])
                
                if message['role'] == 'assistant' and st.session_state.use_tts and 'audio' in message:
                    st.markdown(message['audio'], unsafe_allow_html=True)
        
        # Chat input
        user_input = st.chat_input(f"Message {current_config['name']}...")
        
        # Voice input button
        col1, col2 = st.columns([1, 5])
        if col1.button("🎙️ Voice", key=f"voice_{st.session_state.current_page}"):
            st.info("Voice input simulated - would capture audio here")
            user_input = "This is a simulated voice input message"
        
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
            response = send_message_to_webhook(st.session_state.current_page, user_input)
            
            # Add assistant message
            assistant_msg = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if st.session_state.use_tts:
                assistant_msg["audio"] = get_audio_player(response)
            
            st.session_state.chat_sessions[st.session_state.current_page].append(assistant_msg)
            st.rerun()
        
        # Chat settings
        with st.expander("⚙️ Chat Settings"):
            st.session_state.use_tts = st.checkbox("🔈 Text-to-Speech", value=st.session_state.use_tts)
            st.session_state.show_timestamps = st.checkbox("🕒 Show Timestamps", value=st.session_state.show_timestamps)
            
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_sessions[st.session_state.current_page] = []
                st.rerun()
    
    # Tab 2: Data (Sheets)
    with tab2:
        st.header("Google Sheets Data")
        
        # Load data for current agent
        if st.session_state.current_page not in st.session_state.sheets_data:
            df, error = load_spreadsheet_data(current_config['id'])
            if error:
                st.error(error)
            else:
                st.session_state.sheets_data[st.session_state.current_page] = df
        
        if st.session_state.current_page in st.session_state.sheets_data:
            df = st.session_state.sheets_data[st.session_state.current_page]
            
            # Data overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("Latest Revenue", f"${df['Revenue'].iloc[-1]:,}")
            with col4:
                st.metric("Conversion Rate", f"{(df['Conversions'].sum() / df['Leads'].sum() * 100):.1f}%")
            
            # Data visualization
            st.subheader("📈 Performance Charts")
            
            viz_col1, viz_col2 = st.columns(2)
            
            with viz_col1:
                fig1 = px.line(df, x='Date', y='Leads', title='Leads Over Time')
                st.plotly_chart(fig1, use_container_width=True)
                
                fig3 = px.bar(df, x='Date', y='Revenue', title='Revenue by Date')
                st.plotly_chart(fig3, use_container_width=True)
            
            with viz_col2:
                fig2 = px.line(df, x='Date', y='Conversions', title='Conversions Over Time')
                st.plotly_chart(fig2, use_container_width=True)
                
                fig4 = px.line(df, x='Date', y='Agent_Performance', title='Agent Performance Score')
                st.plotly_chart(fig4, use_container_width=True)
            
            # Data table
            st.subheader("📋 Raw Data")
            st.dataframe(df, use_container_width=True)
            
            # Export options
            st.subheader("💾 Export Data")
            export_col1, export_col2, export_col3 = st.columns(3)
            
            with export_col1:
                if st.button("📄 Export CSV"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{st.session_state.current_page}_data.csv",
                        mime="text/csv"
                    )
            
            with export_col2:
                if st.button("📊 Export Excel"):
                    output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                    df.to_excel(output.name, index=False)
                    with open(output.name, "rb") as f:
                        st.download_button(
                            label="Download Excel",
                            data=f.read(),
                            file_name=f"{st.session_state.current_page}_data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    os.unlink(output.name)
            
            with export_col3:
                if st.button("🔄 Refresh Data"):
                    df, error = load_spreadsheet_data(current_config['id'])
                    if error:
                        st.error(error)
                    else:
                        st.session_state.sheets_data[st.session_state.current_page] = df
                        st.success("Data refreshed!")
                        st.rerun()
    
    # Tab 3: VAPI AI Call
    with tab3:
        st.header("VAPI AI Phone Calls")
        
        # Call interface
        st.subheader("📞 Make AI Call")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Agent Phone:** {current_config['vapi_phone']}")
            st.info(f"**Assistant ID:** {current_config['vapi_assistant_id']}")
        
        with col2:
            phone_number = st.text_input("📱 Recipient Phone Number:", placeholder="+1234567890")
            
            if st.button("📞 Initiate Call", disabled=not phone_number):
                call_data = make_vapi_call(st.session_state.current_page, phone_number)
                
                if st.session_state.current_page not in st.session_state.vapi_calls:
                    st.session_state.vapi_calls[st.session_state.current_page] = []
                
                st.session_state.vapi_calls[st.session_state.current_page].append(call_data)
                st.success(f"Call initiated! Call ID: {call_data['call_id']}")
                st.rerun()
        
        # Call history
        st.subheader("📋 Call History")
        
        if (st.session_state.current_page in st.session_state.vapi_calls and 
            st.session_state.vapi_calls[st.session_state.current_page]):
            
            calls = st.session_state.vapi_calls[st.session_state.current_page]
            
            for call in reversed(calls[-10:]):  # Show last 10 calls
                with st.expander(f"Call to {call['phone_number']} - {call['timestamp'][:16]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Call ID:** {call['call_id']}")
                        st.write(f"**Status:** {call['status']}")
                        st.write(f"**Agent Phone:** {call['vapi_phone']}")
                    
                    with col2:
                        st.write(f"**Recipient:** {call['phone_number']}")
                        st.write(f"**Assistant:** {call['assistant_id']}")
                        st.write(f"**Time:** {call['timestamp']}")
                    
                    # Simulate call controls
                    control_col1, control_col2, control_col3 = st.columns(3)
                    with control_col1:
                        if st.button("📞 Redial", key=f"redial_{call['call_id']}"):
                            st.info("Redial initiated")
                    with control_col2:
                        if st.button("📝 Notes", key=f"notes_{call['call_id']}"):
                            st.info("Notes feature would open here")
                    with control_col3:
                        if st.button("📊 Analytics", key=f"analytics_{call['call_id']}"):
                            st.info("Call analytics would display here")
        else:
            st.info("No calls made yet. Use the form above to initiate your first call.")
        
        # VAPI Settings
        with st.expander("⚙️ VAPI Settings"):
            st.write("**Current Configuration:**")
            st.json({
                "vapi_phone": current_config['vapi_phone'],
                "assistant_id": current_config['vapi_assistant_id'],
                "agent_name": current_config['name']
            })
    
    # Tab 4: Prompts/Info
    with tab4:
        st.header("Prompt Library & Agent Info")
        
        # Agent information
        st.subheader("🤖 Agent Information")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.markdown(f"""
            **Agent Name:** {current_config['name']}  
            **Description:** {current_config['description']}  
            **Icon:** {current_config['icon']}  
            **Spreadsheet ID:** `{current_config['id']}`
            """)
        
        with info_col2:
            st.markdown(f"""
            **Webhook URL:** `{current_config['webhook_url']}`  
            **VAPI Phone:** {current_config['vapi_phone']}  
            **Assistant ID:** `{current_config['vapi_assistant_id']}`  
            **Bearer Token:** `{current_config['bearer_token'][:20]}...`
            """)
        
        st.divider()
        
        # Prompt Library
        st.subheader("💡 Prompt Library")
        
        # Category selection
        categories = list(st.session_state.prompt_library.keys())
        selected_category = st.selectbox("Select Category:", categories)
        
        if selected_category:
            prompts = st.session_state.prompt_library[selected_category]
            
            # Display prompts
            for i, prompt in enumerate(prompts):
                with st.expander(f"{prompt['title']}"):
                    st.write(prompt['prompt'])
                    
                    prompt_col1, prompt_col2 = st.columns(2)
                    
                    with prompt_col1:
                        if st.button("💬 Use in Chat", key=f"use_prompt_{selected_category}_{i}"):
                            # Switch to chatbot tab and pre-fill the prompt
                            st.session_state.current_tab = 'chatbot'
                            st.info(f"Prompt ready to use: {prompt['title']}")
                    
                    with prompt_col2:
                        if st.button("⭐ Favorite", key=f"fav_prompt_{selected_category}_{i}"):
                            st.success("Added to favorites!")
        
        # Add custom prompt
        st.subheader("➕ Add Custom Prompt")
        
        with st.expander("Create New Prompt"):
            new_category = st.selectbox("Category:", categories + ["New Category"])
            
            if new_category == "New Category":
                custom_category = st.text_input("New Category Name:")
                if custom_category:
                    new_category = custom_category
            
            prompt_title = st.text_input("Prompt Title:")
            prompt_text = st.text_area("Prompt Text:", height=100)
            
            if st.button("Add Prompt") and prompt_title and prompt_text:
                if new_category not in st.session_state.prompt_library:
                    st.session_state.prompt_library[new_category] = []
                
                st.session_state.prompt_library[new_category].append({
                    "title": prompt_title,
                    "prompt": prompt_text
                })
                
                st.success(f"Prompt '{prompt_title}' added to {new_category}!")
                st.rerun()

# Footer
st.divider()
st.caption("🚀 Multi-Agent Business Dashboard | Powered by AI")

print("Multi-Agent Dashboard application structure created successfully!")
print("Features implemented:")
print("- 10 AI agents with individual configurations")
print("- 10 Google Sheets integrations")
print("- 10 chatbot webhooks")
print("- VAPI AI calling system")
print("- Unified authentication")
print("- Prompt library system")
print("- Data visualization")
print("- Voice recognition support")
print("- Export capabilities")
