## Live Demo

https://medimitra-ai-health.streamlit.app


# MediMitra – AI Healthcare Chatbot

MediMitra is a multilingual AI-powered healthcare chatbot designed to provide healthcare guidance, symptom-related assistance, and medical FAQ support through an interactive conversational interface.

## Features

- Multilingual chatbot support
  - English
  - Hindi
  - Bhojpuri
- Real-time conversational healthcare assistance
- Emergency healthcare alert section
- AI-powered query handling
- Interactive Streamlit-based UI
- Structured healthcare FAQ retrieval
- Lightweight and deployable web application

## Technologies Used

- Python
- Streamlit
- NLP (Natural Language Processing)
- Generative AI
- JSON-based knowledge base
- Session State Management

## Project Structure

```text
MediMitra1/
│
├── data/
│   ├── english_data.json
│   ├── hindi_data.json
│   ├── bhojpuri_data.json
│   ├── faq_english.json
│   ├── faq_hindi.json
│   └── faq_bhojpuri.json
│
├── app.py
├── backend.py
├── logo.png
├── requirements.txt
├── README.md
└── .gitignore
```

## How to Run Locally

### 1. Clone Repository

```bash
git clone https://github.com/Krish2600/medimitra-ai-health-chatbot.git
```

### 2. Navigate to Project Folder

```bash
cd medimitra-ai-health-chatbot
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Streamlit App

```bash
streamlit run app.py
```

## Deployment

This project can be deployed for free using:

- Streamlit Community Cloud
- HuggingFace Spaces
- Render

## Future Improvements

- Voice input support
- AI symptom prediction
- Appointment booking integration
- Medical report analysis
- User authentication system

## Author

Krish Sharma
