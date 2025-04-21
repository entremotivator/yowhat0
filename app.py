import streamlit as st
from gtts import gTTS
import base64
import json
import speech_recognition as sr

# App Configuration
st.set_page_config(page_title="Voice Assistant", layout="wide", initial_sidebar_state="collapsed")

# Initialize core session states
session_defaults = {
    'active_session': "General",
    'use_tts': True,
    'messages': [],
    'recognizer': sr.Recognizer()
}
for key, val in session_defaults.items():
    st.session_state.setdefault(key, val)

# Core functions
def text_to_speech(text):
    tts = gTTS(text=text, lang='en')
    speech = io.BytesIO()
    tts.write_to_fp(speech)
    return base64.b64encode(speech.getvalue()).decode('utf-8')

def process_query(query):
    headers = {
        "Authorization": f"Bearer {st.secrets['BEARER_TOKEN']}",
        "Content-Type": "application/json"
    }
    response = requests.post(st.secrets['WEBHOOK_URL'], 
                            json={"query": query},
                            headers=headers)
    return response.json().get("response", "Error processing request")

# UI Elements
with st.container():
    st.title("Voice Assistant")
    
    # Chat interface
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/mpeg")

    # Input handling
    if prompt := st.chat_input("Speak or type your request"):
        with st.spinner("Processing..."):
            response = process_query(prompt)
            
            # Store messages with audio
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "audio": f"data:audio/mpeg;base64,{text_to_speech(response)}"
            })
            
            st.rerun()
