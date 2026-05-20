import streamlit as st
import json
import os
from groq import Groq
import requests # Keep this for Groq API calls if needed
from difflib import SequenceMatcher # *** NEW IMPORT for related questions ***

# --- Constants and Configuration ---

# Define file paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Dictionary to map language to its specific data files
# All TTS (Text-to-Speech) keys have been removed.
LANGUAGE_FILES = {
    "English": {
        "lang_config": os.path.join(DATA_DIR, "english_data.json"),
        "faq": os.path.join(DATA_DIR, "faq_english.json"),
        "language_code": "en"
    },
    "Hindi": {
        "lang_config": os.path.join(DATA_DIR, "hindi_data.json"),
        "faq": os.path.join(DATA_DIR, "faq_hindi.json"),
        "language_code": "hi"
    },
    "Bhojpuri": {
        "lang_config": os.path.join(DATA_DIR, "bhojpuri_data.json"),
        "faq": os.path.join(DATA_DIR, "faq_bhojpuri.json"),
        "language_code": "bho" # Use 'bho' for Bhojpuri
    }
}
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")

# --- Data Loading ---

@st.cache_data(ttl=3600) # Cache data for 1 hour
def load_data(language="Hindi"):
    """
    Loads all necessary data files based on the selected language.
    Returns:
        tuple: (lang_data, faq_data, alerts_data)
               Returns (None, None, None) if files are not found.
    """
    try:
        lang_file_paths = LANGUAGE_FILES.get(language)
        if not lang_file_paths:
            st.error(f"Language configuration for '{language}' not found.")
            return None, None, None

        # Load main language config (intents, translations)
        with open(lang_file_paths["lang_config"], 'r', encoding='utf-8') as f:
            lang_data = json.load(f)

        # Load language-specific FAQ
        with open(lang_file_paths["faq"], 'r', encoding='utf-8') as f:
            faq_data = json.load(f)

        # Load alerts data (which contains all languages)
        with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
            alerts_data = json.load(f)
            
        # Add the language code to lang_data for easy access in app.py
        lang_data["language_code"] = lang_file_paths["language_code"]

        return lang_data, faq_data, alerts_data

    except FileNotFoundError as e:
        # This will be the error if a file is missing
        st.error(f"Error: Required data file not found: {e.filename}")
        st.markdown("Please ensure the **data/** directory exists and contains all 7 required JSON files.")
        return None, None, None
    except json.JSONDecodeError as e:
        # This is the error you are currently seeing
        st.error(f"Error decoding JSON from a file: {e}. One of your data files might be empty or malformed.")
        return None, None, None

# --- Core AI and Logic Functions ---

def get_groq_client():
    """Initializes and returns the Groq client using Streamlit secrets."""
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        if not api_key:
            st.error("GROQ_API_KEY not found in Streamlit secrets. Please add it to .streamlit/secrets.toml")
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing Groq client: {e}")
        return None

def check_for_intent(query, lang_data):
    """
    Checks if the query matches a simple, predefined intent (e.g., greeting).
    This is a simple keyword-based check.
    """
    if not lang_data or 'INTENTS' not in lang_data:
        return None

    query_lower = query.lower().strip()

    for intent in lang_data["INTENTS"]:
        # Use the correct key based on language (e.g., 'hindi_keywords' or 'bhojpuri_keywords')
        lang_key = f"{lang_data['language_code'].lower()}_keywords"
        
        if lang_key in intent:
            for keyword in intent[lang_key]:
                if keyword.lower() in query_lower:
                    # Return a random response from the intent's response list
                    return st.session_state.random.choice(intent["responses"])
    return None

def search_faq(query, faq_data):
    """
    Searches the loaded FAQ data for a direct match.
    This is a simple RAG (Retrieval-Aided Generation) step.
    """
    if not faq_data:
        return None

    query_lower = query.lower().strip()
    
    # Prioritize full question match first
    for item in faq_data:
        # Use .get() for safety
        q_lower = item.get('q', '').lower().strip()
        if query_lower == q_lower:
            return item.get('a') # Return exact answer
            
    # Optional: Add a check for keywords in the question if no exact match is found
    # (Keeping it simple for now)
            
    return None

def get_groq_response(user_input, chat_history, language):
    """
    Gets a response from the Groq LLM, incorporating a system prompt.
    """
    client = get_groq_client()
    if client is None:
        st.error("Error: Groq client is not initialized. Check API key.")
        return "Sorry, the AI service is not connected. Please check the API key."

    # === UPDATED, STRICTER SYSTEM PROMPT ===
    system_prompt = f"""
    You are MediMitra, a helpful and empathetic health assistant.
    
    You are NOT a doctor. You must NOT diagnose, prescribe, or give urgent medical advice.
    Your primary role is to provide general health information (based on your knowledge) and to identify when a user needs professional help.
    
    *** SAFETY AND DIAGNOSIS RULE ***
    If a user asks for a diagnosis, describes personal symptoms (e.g., "I have a fever", "my son is sick"), or asks for medication advice (e.g., "what medicine should I take?"), 
    you MUST refuse to diagnose. You must state that you are an AI assistant and cannot provide a diagnosis or medical advice. 
    You MUST strongly recommend they consult a registered doctor or healthcare professional immediately.
    
    *** LANGUAGE RULE ***
    The user is asking a question in {language}.
    You MUST provide your entire response *only* in the {language} language.
    DO NOT, under any circumstances, respond in Hindi if the user's language is Bhojpuri.
    Your whole answer must be in {language}.
    ---
    """
    # === END OF PROMPT ===

    # Combine system prompt with chat history
    messages_for_api = [
        {"role": "system", "content": system_prompt}
    ] + chat_history + [
        {"role": "user", "content": user_input}
    ]

    try:
        chat_completion = client.chat.completions.create(
            messages=messages_for_api,
            model="llama-3.1-8b-instant", # Using a stable, non-deprecated model
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stop=None,
            stream=False,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"Groq API Error: {e}")
        # Try to get a translated error message, fallback to English
        error_translation = "Sorry, I encountered an error trying to connect to the AI model."
        if 'lang_data' in locals() and lang_data:
            error_translation = lang_data.get('TRANSLATIONS', {}).get('groq_fail', error_translation)
        return error_translation


# --- NEW: Speech-to-Text (STT) Function ---

def transcribe_audio(file_path):
    """
    Transcribes audio using Groq's Whisper API.
    """
    client = get_groq_client()
    if client is None:
        st.error("Groq client not initialized. Cannot transcribe audio.")
        return None

    try:
        with open(file_path, "rb") as audio_file:
            # Send the audio file to Groq's transcription service
            transcription = client.audio.transcriptions.create(
                file=(file_path, audio_file.read()),
                model="whisper-large-v3", # Use Whisper model for transcription
                # language="en" # You can specify language, but Whisper is good at auto-detecting
            )
        return transcription.text
    except Exception as e:
        st.error(f"Groq Transcription Error: {e}")
        return None

# --- TTS FUNCTION HAS BEEN REMOVED ---
# (e.g., get_tts_audio is gone)


# --- *** NEW FUNCTION FOR RELATED QUESTIONS *** ---

def find_related_questions(user_query, faq_data, response_text, top_n=3):
    """
    Finds related questions from the FAQ data based on the user query and response.
    """
    if not faq_data:
        return []

    # Use a simple string similarity metric
    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()

    # Combine query and response for better keyword matching
    context_text = user_query.lower() + " " + response_text.lower()
    
    # Calculate similarity for each FAQ question
    scores = []
    for item in faq_data:
        faq_q = item.get('q', '')
        # Don't suggest the exact question the user just asked
        if faq_q.lower().strip() == user_query.lower().strip():
            continue
            
        # Score based on similarity to the combined context
        score = similarity(context_text, faq_q.lower())
        
        # Boost score if keywords overlap
        query_words = set(context_text.split())
        faq_words = set(faq_q.lower().split())
        overlap = len(query_words.intersection(faq_words))
        
        # Add a boost for overlapping words
        final_score = score + (overlap * 0.1) 
        
        scores.append((final_score, faq_q))

    # Sort by score and get the top N questions
    scores.sort(key=lambda x: x[0], reverse=True)
    
    related_qs = [q for score, q in scores[:top_n] if score > 0.1] # Threshold to avoid bad matches
    
    return related_qs

