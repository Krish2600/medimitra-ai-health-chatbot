import streamlit as st
import random
import os
import json
import base64
from streamlit_mic_recorder import mic_recorder
from backend import load_data, get_groq_response, check_for_intent, search_faq, transcribe_audio, find_related_questions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(layout="wide", page_title="MediMitra Chatbot")

# --- Custom CSS ---
def load_css():
    css = """
    <style>
        /* === NORMAL MAIN TITLE === */
        .main-title {
            text-align: center;
            font-size: 2.5rem; /* 40px */
            font-weight: 600;
            color: #0099ff; /* A nice blue */
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        /* === SIDEBAR EMERGENCY BOX === */
        .st-emergency-box {
            background-color: #ffffff;
            border-left: 5px solid #ff4b4b;
            border-radius: 10px;
            padding: 1rem;
            margin-top: 2rem;
            color: #333333;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            font-weight: 500;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        .st-emergency-box svg {
            flex-shrink: 0;
            width: 28px;
            height: 28px;
            color: #ff4b4b;
        }

        /* === ALERT BOX === */
        .stAlertCard {
            background-color: #1a1a1a;
            border-radius: 10px;
            padding: 1.2rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            margin-bottom: 1rem;
        }

        .alert-badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            color: white;
            margin-right: 8px;
        }

        .alert-badge.high { background-color: #ff4b4b; }
        .alert-badge.medium { background-color: #ffb300; }

        /* Mic button styling */
        .mic-wrapper {
            position: fixed;
            bottom: 12px;
            right: 20px;
            z-index: 1001;
        }
        .mic-wrapper button {
            height: 52px;
            width: 80px;
            border-radius: 8px;
            border: none;
            background-color: #007BFF;
            color: white;
            font-size: 16px;
            font-weight: 600;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        .mic-wrapper button:active,
        .mic-wrapper button:focus {
            background-color: #FF4B4B;
            box-shadow: 0 0 10px rgba(255, 75, 75, 0.7);
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_css()

# === Session Initialization ===
if 'random' not in st.session_state:
    st.session_state.random = random.Random()
    st.session_state.random.seed(42)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "language" not in st.session_state:
    st.session_state.language = "English"

if "last_audio_bytes" not in st.session_state:
    st.session_state.last_audio_bytes = None

# --- REMOVED THE BAD HEADER INJECTION ---

# === Load Data ===
@st.cache_resource
def load_all_data():
    all_data = {}
    for lang in ["English", "Hindi", "Bhojpuri"]:
        lang_data, faq_data, alerts_data = load_data(lang)
        if lang_data and faq_data and alerts_data:
            all_data[lang] = (lang_data, faq_data, alerts_data)
        else:
            st.error(f"Failed to load data for {lang}. Please check all data files.")
            return None
    return all_data

all_language_data = load_all_data()
if not all_language_data:
    st.error("Failed to load required data.")
    st.stop()

# === Functions ===
def display_alerts(lang_data, alerts_data):
    alert_title = lang_data.get('TRANSLATIONS', {}).get('alert_title', 'Important Alerts')
    lang_code = lang_data.get('language_code', 'en')
    message_key = "hindi_message" if lang_code in ["hi", "bho"] else "english_message"

    with st.expander(f"⚠ {alert_title}", expanded=True):
        st.markdown("<div class='stAlertCard'>", unsafe_allow_html=True)
        for alert_type in ["general_alerts", "seasonal_alerts"]:
            for alert in alerts_data.get(alert_type, []):
                priority = alert['priority'].upper()
                badge_class = "high" if priority == "HIGH" else "medium"
                st.markdown(
                    f"<span class='alert-badge {badge_class}'>{priority}</span>"
                    f"{alert.get(message_key, alert['english_message'])}<br><br>",
                    unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)

def set_language():
    st.session_state.language = st.session_state.language_selector
    st.session_state.messages = []
    st.session_state.last_audio_bytes = None
    st.rerun()

def handle_related_question_click():
    for i in range(len(st.session_state.messages)):
        key = f"related_q_{i}"
        if key in st.session_state and st.session_state[key] is not None:
            question = st.session_state[key]
            st.session_state[key] = None
            current_lang = st.session_state.language
            lang_data, faq_data, _ = all_language_data[current_lang]
            process_chat(question, lang_data, faq_data, current_lang)
            st.rerun()

def process_chat(user_input, lang_data, faq_data, language):
    lang_code = lang_data.get('language_code', 'en')
    st.session_state.messages.append({"role": "user", "content": user_input, "lang_code": lang_code})
    with st.spinner(lang_data.get('TRANSLATIONS', {}).get('thinking', 'Thinking...')):
        chat_history_for_groq = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages]
        response_text = check_for_intent(user_input, lang_data)
        faq_response = None
        if not response_text:
            faq_response = search_faq(user_input, faq_data)
            if faq_response:
                response_text = faq_response
        related_questions = find_related_questions(user_input, faq_data, response_text if response_text else "")
        if not response_text:
            response_text = get_groq_response(user_input, chat_history_for_groq[:-1], language)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "lang_code": lang_code,
        "related": related_questions
    })

# === UI ===
current_lang = st.session_state.language
lang_data, faq_data, alerts_data = all_language_data[current_lang]

# === SIDEBAR ===
with st.sidebar:
    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("## MediMitra")

    lang_label = lang_data.get('TRANSLATIONS', {}).get('language_select', 'Select Language')
    language_options = ["English", "Hindi", "Bhojpuri"]
    st.selectbox(label=lang_label, options=language_options,
                 key="language_selector", on_change=set_language,
                 index=language_options.index(current_lang))
    st.divider()

    emergency_text = lang_data.get('TRANSLATIONS', {}).get('emergency_info')
    if emergency_text:
        st.markdown(f"""
        <div class="st-emergency-box">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <div>{emergency_text}</div>
        </div>
        """, unsafe_allow_html=True)

# === MAIN CONTENT ===

# --- ADDED THE "NORMAL" TITLE HERE ---
st.markdown("<h1 class='main-title'>MediMitra: Health Assistant</h1>", unsafe_allow_html=True)

display_alerts(lang_data, alerts_data)

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            lang_code = message.get('lang_code', 'en')
            safe_text = json.dumps(message["content"])
            button_id = f"speak-button-{i}"
            button_html = f"""
            <div>
                <button id='{button_id}' style="background: none; border: none; cursor: pointer; font-size: 1.25rem; padding-left: 0; color: white;">🔊 Speak</button>
                <script>
                (function(){{
                    const button = document.getElementById('{button_id}');
                    if(!button) return;
                    function toggleSpeak(text, lang){{
                        try{{
                            if(button.innerHTML.includes('Stop')||button.innerHTML.includes('⏹')){{
                                window.speechSynthesis.cancel();
                                button.innerHTML='🔊 Speak';
                                return;
                            }}
                            window.speechSynthesis.cancel();
                            const utterance=new SpeechSynthesisUtterance(text);
                            let langCode='en-US';
                            if(lang==='hi'||lang==='bho') langCode='hi-IN';
                            utterance.lang=langCode; utterance.rate=0.9; utterance.pitch=1;
                            let voices=window.speechSynthesis.getVoices();
                            let v=voices.find(voice=>voice.lang===langCode);
                            if(v) utterance.voice=v;
                            utterance.onstart=()=>button.innerHTML='⏹ Stop';
                            utterance.onend=()=>button.innerHTML='🔊 Speak';
                            window.speechSynthesis.speak(utterance);
                        }}catch(e){{button.innerHTML='🔊 Speak';}}
                    }}
                    button.addEventListener('click',()=>{{toggleSpeak({safe_text},'{lang_code}');}});
                }})();
                </script>
            </div>
            """
            st.components.v1.html(button_html, height=40)

            related_qs = message.get("related")
            if related_qs:
                placeholder = lang_data.get('TRANSLATIONS', {}).get('related_questions_placeholder', 'Select a related question...')
                options = [placeholder] + related_qs
                st.selectbox(label=lang_data.get('TRANSLATIONS', {}).get('related_questions_title', 'Related Questions:'),
                             options=options, index=0,
                             key=f"related_q_{i}",
                             on_change=handle_related_question_click)

# === Input Section ===
speak_prompt = "Speak"
speaking_prompt = lang_data.get('TRANSLATIONS', {}).get('speaking_prompt', 'Recording...')
st.markdown('<div class="mic-wrapper">', unsafe_allow_html=True)
audio = mic_recorder(start_prompt=speak_prompt, stop_prompt=speaking_prompt, key='recorder', format="wav")
st.markdown('</div>', unsafe_allow_html=True)
prompt = st.chat_input(lang_data.get('TRANSLATIONS', {}).get('enter_query', 'Enter your query here...'))

if prompt:
    st.session_state.last_audio_bytes = None
    process_chat(prompt, lang_data, faq_data, current_lang)
    st.rerun()

elif audio is not None and audio['bytes'] and audio['bytes'] != st.session_state.last_audio_bytes:
    audio_bytes = audio['bytes']
    temp_audio_file = os.path.join(BASE_DIR, "temp_audio.wav")
    try:
        with open(temp_audio_file, "wb") as f:
            f.write(audio_bytes)
        with st.spinner(lang_data.get('TRANSLATIONS', {}).get('transcribing', 'Transcribing...')):
            transcribed_text = transcribe_audio(temp_audio_file)
    finally:
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
    if transcribed_text and transcribed_text.strip():
        process_chat(transcribed_text, lang_data, faq_data, current_lang)
        st.session_state.last_audio_bytes = audio_bytes
        st.rerun()
    else:
        st.warning(lang_data.get('TRANSLATIONS', {}).get('stt_fail', 'Could not understand audio. Please try again.'))