import streamlit as st
import requests
import uuid
from gtts import gTTS
import os
import base64
import json
from datetime import datetime
import io
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, RTCConfiguration
import logging

logger = logging.getLogger(__name__)

# App Configuration
st.set_page_config(page_title="Voice Chat Assistant", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state variables
session_defaults = {
    'active_session': "General",
    'active_page': "Chat",
    'use_tts': True,
    'show_timestamps': False,
    'auto_save': False,
    'messages': [],
    'text_from_audio': ""  # Added to store transcribed text
}
for key, val in session_defaults.items():
    st.session_state.setdefault(key, val)

st.session_state.setdefault('credentials', {
    "webhook_url": st.secrets["WEBHOOK_URL"],
    "bearer_token": st.secrets["BEARER_TOKEN"]
})

st.session_state.setdefault('sessions', {
    "General": {"messages": [], "session_id": str(uuid.uuid4())}
})

# Configuration for streamlit-webrtc
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Audio Processor Class
class SpeechToTextProcessor(AudioProcessorBase):
    def __init__(self):
        self.transcript = ""

    def recv(self, frame):
        try:
            import speech_recognition as sr  # Import here to avoid blocking
            audio = frame.to_ndarray()
            sr_audio = sr.AudioData(audio.tobytes(), source_sample_rate=48000, source_sample_width=2)
            r = sr.Recognizer()
            self.transcript = r.recognize_google(sr_audio)
            st.session_state['text_from_audio'] = self.transcript
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            self.transcript = ""
            st.error(f"Speech recognition error: {e}") # Report errors in the UI
        return frame

# Helper Functions
def text_to_speech(text):
    tts = gTTS(text=text, lang='en')
    speech = io.BytesIO()
    tts.write_to_fp(speech)
    return base64.b64encode(speech.getvalue()).decode('utf-8')

def send_message_to_llm(session_id, message):
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
                timeout=60
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

def save_chat_history(session_name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_history_{session_name}_{timestamp}.json"

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

# Navigation - Main App Structure
main_tabs = ["💬 Chat", "⚙️ Settings"]
selected_tab = st.sidebar.selectbox("Navigation", main_tabs)
st.session_state.active_page = selected_tab.split()[-1]

# Sidebar Content
with st.sidebar:
    st.title("🛠️ Assistant Controls")

    st.subheader("🔑 API Credentials")
    with st.expander("Update Credentials"):
        webhook_url = st.text_input("Webhook URL:", value=st.session_state.credentials["webhook_url"])
        bearer_token = st.text_input("Bearer Token:", value=st.session_state.credentials["bearer_token"], type="password")

        if st.button("Save Credentials"):
            st.session_state.credentials["webhook_url"] = webhook_url
            st.session_state.credentials["bearer_token"] = bearer_token
            st.success("Credentials updated successfully!")

    if st.session_state.active_page == "Chat":
        st.subheader("⚙️ I/O Settings")
        st.session_state.use_tts = st.checkbox("🔈 Text-to-Speech", value=st.session_state.use_tts)
        st.session_state.show_timestamps = st.checkbox("🕒 Show Timestamps", value=st.session_state.show_timestamps)
        st.session_state.auto_save = st.checkbox("💾 Auto-save on Exit", value=st.session_state.auto_save)

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

    for msg in st.session_state.sessions[st.session_state.active_session]["messages"]:
        with st.chat_message(msg['role']):
            if st.session_state.show_timestamps and 'timestamp' in msg:
                st.caption(f"⏱️ {msg['timestamp']}")
            st.markdown(msg['content'])
            if msg['role'] == 'assistant' and st.session_state.use_tts:
                audio_data = text_to_speech(msg['content'])
                st.audio(audio_data, format='audio/mpeg')

    user_input = None

    # Voice Input using streamlit-webrtc
    text_from_audio = ""
    webrtc_streamer(
        key="speech-to-text",
        audio_processor_factory=SpeechToTextProcessor,
        rtc_configuration=RTC_CONFIGURATION,
        media_stream_constraints={"audio": True, "video": False},  # Only audio
    )
    text_from_audio = st.session_state.get('text_from_audio', "")

    user_input = st.chat_input("Your message...", value=text_from_audio) # Prefill

    if user_input:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        session_id = st.session_state.sessions[st.session_state.active_session]["session_id"]
        response = send_message_to_llm(session_id, user_input)

        assistant_message = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        st.session_state.sessions[st.session_state.active_session]["messages"].append(assistant_message)

        with st.chat_message("assistant"):
            if st.session_state.show_timestamps:
                st.caption(f"⏱️ {assistant_message['timestamp']}")
            st.markdown(response)
            if st.session_state.use_tts:
                audio_data = text_to_speech(response)
                st.audio(audio_data, format='audio/mpeg')

# Settings Page Content
elif st.session_state.active_page == "Settings":
    st.title("⚙️ Settings")
    st.write("Configure application settings here.")
