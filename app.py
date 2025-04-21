import streamlit as st
import requests
import uuid
import speech_recognition as sr
from gtts import gTTS
import os
import base64
import json
from datetime import datetime

# App Configuration
st.set_page_config(page_title="Voice Chat Assistant", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state variables if they don't exist
if 'recognizer' not in st.session_state:
    st.session_state.recognizer = sr.Recognizer()

if 'active_session' not in st.session_state:
    st.session_state.active_session = "General"

if 'active_page' not in st.session_state:
    st.session_state.active_page = "Chat"

if 'credentials' not in st.session_state:
    st.session_state.credentials = {
        "webhook_url": st.secrets["WEBHOOK_URL"],  # Use Streamlit secrets
        "bearer_token": st.secrets["BEARER_TOKEN"]  # Use Streamlit secrets
    }

if 'sessions' not in st.session_state:
    # Initialize a single general chat session
    st.session_state.sessions = {
        "General": {"messages": [], "session_id": str(uuid.uuid4())}
    }

if 'use_tts' not in st.session_state:
    st.session_state.use_tts = True  # TTS is auto-selected

if 'recording_status' not in st.session_state:
    st.session_state.recording_status = False

if 'show_timestamps' not in st.session_state:
    st.session_state.show_timestamps = False

if 'auto_save' not in st.session_state:
    st.session_state.auto_save = False

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

# Navigation - Main App Structure
main_tabs = ["💬 Chat", "⚙️ Settings"]  # Removed "Prompt Library"
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

# Settings Page Content
elif st.session_state.active_page == "Settings":
    st.title("⚙️ Settings")
    st.write("Configure application settings here.")
