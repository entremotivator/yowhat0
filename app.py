import streamlit as st
import requests
import uuid
import speech_recognition as sr
from gtts import gTTS
import os
import base64
import json
from datetime import datetime
import time

# Function to load secrets from Streamlit secrets
def load_secrets():
    """Load API keys and other secrets from Streamlit's secrets."""
    secrets = {
        "webhook_url": st.secrets["WEBHOOK_URL"],
        "bearer_token": st.secrets["BEARER_TOKEN"]
    }
    return secrets

# App Configuration
st.set_page_config(page_title="Voice Chat Assistant", layout="wide")

# Initialize session state variables if they don't exist
if 'recognizer' not in st.session_state:
    st.session_state.recognizer = sr.Recognizer()
    
if 'active_session' not in st.session_state:
    st.session_state.active_session = "General"
    
if 'active_page' not in st.session_state:
    st.session_state.active_page = "Chat"
    
# Load credentials from Streamlit secrets
if 'credentials' not in st.session_state:
    st.session_state.credentials = load_secrets()
    
if 'sessions' not in st.session_state:
    # Initialize a single general chat session
    st.session_state.sessions = {
        "General": {"messages": [], "session_id": str(uuid.uuid4())}
    }
    
if 'use_tts' not in st.session_state:
    st.session_state.use_tts = True
    
if 'recording_status' not in st.session_state:
    st.session_state.recording_status = False
    
if 'show_timestamps' not in st.session_state:
    st.session_state.show_timestamps = False
    
if 'auto_save' not in st.session_state:
    st.session_state.auto_save = False

if 'prompt_favorites' not in st.session_state:
    st.session_state.prompt_favorites = []

# Prompt Library
if 'prompt_library' not in st.session_state:
    st.session_state.prompt_library = {
        "Email": [
            {
                "title": "Draft Email",
                "prompt": "Draft an email to [recipient] about [subject]. The tone should be [tone]."
            },
            {
                "title": "Reply to Email",
                "prompt": "Craft a response to this email: [paste email content]"
            },
            {
                "title": "Email Summary",
                "prompt": "Summarize these email threads in my inbox about [topic]."
            },
            {
                "title": "Follow Up Email",
                "prompt": "Write a follow-up email to [recipient] regarding our conversation about [topic] on [date]."
            }
        ],
        "Calendar": [
            {
                "title": "Schedule Meeting",
                "prompt": "Schedule a [duration] meeting with [attendees] about [topic] sometime [timeframe]."
            },
            {
                "title": "Meeting Prep",
                "prompt": "Prepare an agenda for my meeting about [topic] with [attendees] on [date]."
            },
            {
                "title": "Reschedule Request",
                "prompt": "Write a message to reschedule my meeting with [person/team] originally set for [date/time]."
            }
        ],
        "General": [
            {
                "title": "Summarize Document",
                "prompt": "Summarize this document: [paste document]"
            },
            {
                "title": "Research Topic",
                "prompt": "Research [topic] and provide me with a comprehensive summary."
            },
            {
                "title": "Compare Options",
                "prompt": "Compare [option 1], [option 2], and [option 3] based on [criteria]."
            }
        ]
    }

# Helper Functions
def get_audio_player(text):
    """Generate an audio player for the given text."""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        # Save the audio file
        audio_file_path = f"response_audio_{uuid.uuid4()}.mp3"
        tts.save(audio_file_path)
        
        # Read the file and encode it
        with open(audio_file_path, "rb") as file:
            audio_bytes = file.read()
        
        # Remove the temporary file
        os.remove(audio_file_path)
        
        # Create the HTML audio player WITHOUT autoplay
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_player = f"""
        <audio controls>
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
        """
        return audio_player
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

def send_message_to_llm(session_id, message):
    """Send a message to the LLM via webhook and retrieve the response."""
    headers = {
        "Authorization": f"Bearer {st.session_state.credentials['bearer_token']}",
        "Content-Type": "application/json"
    }
    payload = {
        "sessionId": session_id,
        "chatInput": message
    }
    
    try:
        with st.spinner("Waiting for response..."):
            resp = requests.post(
                st.session_state.credentials['webhook_url'],
                json=payload, 
                headers=headers, 
                timeout=60  # Increased timeout for longer responses
            )
            
        resp.raise_for_status()
        data = resp.json()
        
        if isinstance(data, dict):
            return data.get("output", "[No output]")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0].get("output", "[No output]")
        
        return str(data) if data else "[Empty response]"
    
    except requests.RequestException as e:
        return f"Request error: {e}"
    except ValueError:
        return "Error parsing JSON response."

def recognize_speech():
    """Capture voice input from the microphone and return transcribed text."""
    recognizer = st.session_state.get("recognizer")
    if recognizer is None:
        st.error("Speech recognizer not initialized.")
        return None

    # Configure recognizer with more lenient parameters
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.5  # Longer pause to avoid cutting off

    placeholder = st.empty()
    placeholder.info("🎙️ Listening... Please speak clearly.")
    
    try:
        with sr.Microphone() as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Listen with extended timeout and phrase limit
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=60)
            
            placeholder.info("🔊 Processing your speech...")
            
            # Use Google Speech Recognition with extended timeout
            text = recognizer.recognize_google(audio, language='en-US')
            placeholder.success(f"✅ You said: {text}")
            return text
            
    except sr.WaitTimeoutError:
        placeholder.warning("⚠️ No speech detected. Please try again.")
    except sr.UnknownValueError:
        placeholder.warning("⚠️ Could not understand the audio. Please try again.")
    except sr.RequestError as e:
        placeholder.error(f"🚨 API request error: {e}")
    except Exception as e:
        placeholder.error(f"🚨 Error capturing audio: {e}")
    
    return None

def save_chat_history(session_name):
    """Save the current chat session to a file."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_history_{session_name}_{timestamp}.json"
        
        # Create simplified message history without audio players
        export_messages = []
        for msg in st.session_state.sessions[session_name]["messages"]:
            export_messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", "")
            })
            
        export_data = {
            "session_id": st.session_state.sessions[session_name]["session_id"],
            "messages": export_messages
        }
        
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)
            
        return f"Chat history saved to {filename}"
    except Exception as e:
        return f"Error saving chat history: {e}"

def create_new_session(session_name):
    """Create a new chat session with the given name."""
    if session_name in st.session_state.sessions:
        return False
    
    st.session_state.sessions[session_name] = {
        "messages": [],
        "session_id": str(uuid.uuid4())
    }
    return True

def add_custom_prompt(category, title, prompt_text):
    """Add a custom prompt to the prompt library."""
    if category not in st.session_state.prompt_library:
        st.session_state.prompt_library[category] = []
    
    st.session_state.prompt_library[category].append({
        "title": title,
        "prompt": prompt_text
    })
    return True

def toggle_favorite(category, prompt_index):
    """Toggle favorite status of a prompt."""
    prompt = st.session_state.prompt_library[category][prompt_index]
    
    # Create a unique identifier for the prompt
    prompt_id = f"{category}_{prompt_index}"
    
    if prompt_id in st.session_state.prompt_favorites:
        st.session_state.prompt_favorites.remove(prompt_id)
    else:
        st.session_state.prompt_favorites.append(prompt_id)

def is_favorite(category, prompt_index):
    """Check if a prompt is favorited."""
    prompt_id = f"{category}_{prompt_index}"
    return prompt_id in st.session_state.prompt_favorites

def export_prompts():
    """Export the prompt library to a JSON file."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_library_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(st.session_state.prompt_library, f, indent=2)
            
        return f"Prompt library exported to {filename}"
    except Exception as e:
        return f"Error exporting prompt library: {e}"

def import_prompts(file):
    """Import prompts from a JSON file."""
    try:
        imported_data = json.load(file)
        if isinstance(imported_data, dict):
            for category, prompts in imported_data.items():
                if category not in st.session_state.prompt_library:
                    st.session_state.prompt_library[category] = []
                
                for prompt in prompts:
                    if isinstance(prompt, dict) and "title" in prompt and "prompt" in prompt:
                        st.session_state.prompt_library[category].append(prompt)
            
            return f"Successfully imported prompts"
        return "Invalid file format"
    except Exception as e:
        return f"Error importing prompts: {e}"

# Navigation - Main App Structure
main_tabs = ["💬 Chat", "📚 Prompt Library", "⚙️ Settings"]
selected_tab = st.sidebar.selectbox("Navigation", main_tabs)

st.session_state.active_page = selected_tab.split()[-1]  # Extract page name without emoji

# Sidebar Content
with st.sidebar:
    st.title("🛠️ Assistant Controls")
    
    # Add credentials settings
    st.subheader("🔑 API Credentials")
    with st.expander("Update Credentials"):
        webhook_url = st.text_input("Webhook URL:", value=st.session_state.credentials["webhook_url"])
        bearer_token = st.text_input("Bearer Token:", value=st.session_state.credentials["bearer_token"], type="password")
        
        if st.button("Save Credentials"):
            st.session_state.credentials["webhook_url"] = webhook_url
            st.session_state.credentials["bearer_token"] = bearer_token
            st.success("Credentials updated successfully!")
    
    # Only show these settings in Chat page
    if st.session_state.active_page == "Chat":
        # Input/Output Settings
        st.subheader("⚙️ I/O Settings")
        st.session_state.use_tts = st.checkbox("🔈 Text-to-Speech", value=st.session_state.use_tts)
        st.session_state.show_timestamps = st.checkbox("🕒 Show Timestamps", value=st.session_state.show_timestamps)
        st.session_state.auto_save = st.checkbox("💾 Auto-save on Exit", value=st.session_state.auto_save)
        
        # Session Management
        st.subheader("📁 Session Management")
        
        if st.button("💾 Save Chat History"):
            result = save_chat_history(st.session_state.active_session)
            st.info(result)
            
        if st.button("🗑️ Clear Chat History"):
            st.session_state.sessions[st.session_state.active_session]["messages"] = []
            st.success("Cleared chat history")
            st.experimental_rerun()

# Main Page Content - Chat Interface
if st.session_state.active_page == "Chat":
    st.title("🗣️ AI Chat Assistant")
    st.markdown("Type or use the voice button to interact with the assistant.")

    # Display chat history for current session
    for msg in st.session_state.sessions[st.session_state.active_session]["messages"]:
        with st.chat_message(msg['role']):
            # Show timestamp if enabled
            if st.session_state.show_timestamps and 'timestamp' in msg:
                st.caption(f"⏱️ {msg['timestamp']}")
                
            st.markdown(msg['content'])
            
            # Only render audio player if it exists and TTS is enabled
            if msg['role'] == 'assistant' and st.session_state.use_tts and 'audio_player' in msg and msg['audio_player']:
                st.markdown(msg['audio_player'], unsafe_allow_html=True)

    # Get user input (text or speech)
    user_input = None
    
    # Text input area
    user_input = st.chat_input("Your message...")
    
    # Voice input button
    voice_col1, voice_col2 = st.columns([1, 5])
    if voice_col1.button("🎙️ Voice Input", key="record_button", use_container_width=True):
        # Toggle recording status
        st.session_state.recording_status = True
        user_input = recognize_speech()
        st.session_state.recording_status = False

    # Process user input and respond if valid input is provided
    if user_input:
        # Add timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add user message to chat
        user_message = {
            "role": "user", 
            "content": user_input,
            "timestamp": current_time
        }
        st.session_state.sessions[st.session_state.active_session]["messages"].append(user_message)
        
        with st.chat_message("user"):
            if st.session_state.show_timestamps:
                st.caption(f"⏱️ {current_time}")
            st.markdown(user_input)
        
        # Get response from LLM webhook
        session_id = st.session_state.sessions[st.session_state.active_session]["session_id"]
        response = send_message_to_llm(session_id, user_input)
        
        # Create audio player for response if TTS is enabled
        audio_player = None
        if st.session_state.use_tts:
            audio_player = get_audio_player(response)
        
        # Add assistant message to chat
        assistant_message = {
            "role": "assistant", 
            "content": response,
            "audio_player": audio_player,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        st.session_state.sessions[st.session_state.active_session]["messages"].append(assistant_message)
        
        # Display assistant message
        with st.chat_message("assistant"):
            if st.session_state.show_timestamps:
                st.caption(f"⏱️ {assistant_message['timestamp']}")
            st.markdown(response)
            if audio_player:
                st.markdown(audio_player, unsafe_allow_html=True)
        
        # Auto-save if enabled
        if st.session_state.auto_save:
            save_chat_history(st.session_state.active_session)

# Main Page Content - Prompt Library
elif st.session_state.active_page == "Prompt":
    st.title("📚 Prompt Library")
    st.sidebar.subheader("⚙️ Manage Prompts")
    
    # Add custom prompt
    with st.sidebar.expander("➕ Add Custom Prompt"):
        category = st.selectbox("Category:", list(st.session_state.prompt_library.keys()) + ["New Category"])
        
        # Allow creating a new category
        if category == "New Category":
            new_category = st.text_input("New Category Name:")
            if new_category:
                category = new_category
        
        title = st.text_input("Prompt Title:")
        prompt_text = st.text_area("Prompt Text:")
        
        if st.button("Add Prompt"):
            if category and title and prompt_text:
                if add_custom_prompt(category, title, prompt_text):
                    st.success("Prompt added successfully!")
                else:
                    st.error("Failed to add prompt.")
            else:
                st.warning("Please fill out all fields.")
    
    # Import prompts from JSON file
    with st.sidebar.expander("📂 Import Prompts"):
        uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
        if uploaded_file:
            result = import_prompts(uploaded_file)
            st.info(result)
            
    # Export prompts to JSON file
    if st.sidebar.button("Export Prompt Library"):
        result = export_prompts()
        st.info(result)
    
    # Display prompts in main area
    for category, prompts in st.session_state.prompt_library.items():
        st.header(f"{category}")
        cols = st.columns(3)  # Display prompts in 3 columns
        col_num = 0
        
        for i, prompt in enumerate(prompts):
            with cols[col_num]:
                # Checkbox to add/remove prompt from favorites
                is_fav = is_favorite(category, i)
                if st.checkbox(f"⭐ Favorite", value=is_fav, key=f"fav_{category}_{i}") != is_fav:
                    toggle_favorite(category, i)
                    st.experimental_rerun()  # Refresh to update the UI
                
                st.subheader(prompt["title"])
                st.write(prompt["prompt"])
                
                # Button to use the prompt in chat
                if st.button(f"Use this prompt", key=f"use_{category}_{i}"):
                    st.session_state.active_page = "Chat"  # Switch to chat interface
                    st.experimental_rerun()  # Refresh to switch pages
                    
            col_num = (col_num + 1) % 3  # Rotate through the columns

# Main Page Content - Settings
elif st.session_state.active_page == "Settings":
    st.title("⚙️ Settings")
    st.write("App settings and configurations.")
    
    # Add more settings options as needed

# Auto-save chat history on app exit (if enabled)
if st.session_state.auto_save:
    st.session_state.on_change(save_chat_history, args=(st.session_state.active_session,))
