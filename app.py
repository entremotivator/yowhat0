import streamlit as st
import requests
import uuid
import speech_recognition as sr
import os
import base64
import json
from datetime import datetime
import io
from gtts import gTTS

# App Configuration
st.set_page_config(page_title="Voice Chat Assistant", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state variables if they don't exist
session_defaults = {
    'active_session': "General",
    'active_page': "Chat",
    'use_tts': True,
    'recording_status': False,
    'show_timestamps': False,
    'auto_save': False,
    'messages': [],
    'recognizer': sr.Recognizer()
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

def recognize_speech():
    recognizer = st.session_state.get("recognizer")
    if recognizer is None:
        st.error("Speech recognizer not initialized.")
        return None

    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.5

    placeholder = st.empty()
    placeholder.info("🎙️ Listening... Please speak clearly.")

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=60)
            placeholder.info("🔊 Processing your speech...")
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

def create_new_session(session_name):
    if session_name in st.session_state.sessions:
        return False

    st.session_state.sessions[session_name] = {
        "messages": [],
        "session_id": str(uuid.uuid4())
    }
    return True

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

    user_input = st.chat_input("Your message...")

    voice_col1, voice_col2 = st.columns([1, 5])
    if voice_col1.button("🎙️ Voice Input", key="record_button", use_container_width=True):
        st.session_state.recording_status = True
        user_input = recognize_speech()
        st.session_state.recording_status = False

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

        if st.session_state.auto_save:
            save_chat_history(st.session_state.active_session)

elif st.session_state.active_page == "Settings":
    st.title("⚙️ Settings")
    st.write("Configure application settings here.")
