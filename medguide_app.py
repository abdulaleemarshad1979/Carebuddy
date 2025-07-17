import streamlit as st
import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv
import os
from PIL import Image
import pytesseract
from collections import deque
import datetime

# ---------- Load API Key ----------
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.error("❌ OpenRouter API key not found. Please check your .env file.")
    st.stop()

# ---------- Page Config ----------
st.set_page_config(
    page_title="CareBuddy - Medical Q&A",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ---------- Instant Visible Output to Prevent Stuck Cooking Screen ----------
st.title("🩺 CareBuddy")
st.info("👋 Welcome! Upload a report or ask your health-related question below.")

# ---------- Custom CSS for Styling ----------
st.markdown(
    """
    <style>
        /* Pleasant Background Gradient */
        body, .main {
            background-image: linear-gradient(180deg, #E0F7FA 0%, #FFFFFF 100%);
        }

        /* Title and Subtitle Styling */
        .title {
            text-align: center;
            color: #01579B;
            font-size: 38px;
            font-weight: bold;
            padding-top: 20px;
        }
        .subtitle {
            text-align: center;
            color: #546E7A;
            font-size: 18px;
            padding-bottom: 20px;
        }
        hr {
            border: 1px solid #B0BEC5;
        }

        /* Chat Bubble Styling */
        .bubble-user {
            background-color: #0288D1;
            color: white;
            padding: 12px;
            border-radius: 20px 20px 5px 20px;
            margin: 8px 0;
            max-width: 80%;
            align-self: flex-end;
            float: right;
            clear: both;
        }
        .bubble-bot {
            background-color: #ECEFF1;
            color: #111111;
            padding: 12px;
            border-radius: 20px 20px 20px 5px;
            margin: 8px 0;
            max-width: 80%;
            align-self: flex-start;
            float: left;
            clear: both;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
            padding-bottom: 20px;
        }

        .stButton>button {
            width: 100%;
            text-align: left;
            background-color: #CFD8DC;
            color: #263238;
            border: 1px solid #B0BEC5;
            margin-bottom: 5px;
        }
    </style>
    <div class='title'>🩺 CareBuddy</div>
    <div class='subtitle'>Your friendly guide to understanding your health.</div>
    <hr />
    """,
    unsafe_allow_html=True
)

# ---------- Text Extraction Functions ----------
@st.cache_data
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    return text

@st.cache_data
def extract_text_from_image(image_file):
    image = Image.open(image_file)
    text = pytesseract.image_to_string(image)
    return text

# ---------- AI Function ----------
def ask_openrouter(question, report_text):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    system_prompt = """
    You are 'CareBuddy', a specialized AI assistant. Your ONLY function is to provide helpful, safe, and informative answers STRICTLY related to human health and medicine.
    Your Core Directives:
    1.  **Scope Limitation:** You MUST ONLY answer questions about medical conditions, symptoms, treatments, anatomy, physiology, nutrition, mental health, and general wellness. If the user's question is based on a provided medical report, use the report's text as the primary source of context.
    2.  **Strictly Reject Off-Topic Questions:** If a user asks a question that is NOT about health or medicine (e.g., "What is the capital of India?", "Who is the president?", "Write a story"), you MUST politely refuse.
    3.  **Refusal Protocol:** When you reject a question, use a clear and helpful response. For example: "My purpose is to assist with health and medical questions. I cannot answer queries outside of this topic. How can I help you with your health today?"
    4.  **CRITICAL SAFETY DISCLAIMER:** You are NOT a doctor. You MUST NEVER provide a medical diagnosis or a direct prescription. **Every single one of your responses must end with the following disclaimer, without exception:**
    ---
    ***Disclaimer:** This information is for educational purposes only. It is not a substitute for professional medical advice. Always consult with a qualified healthcare provider for any health concerns or before making any decisions related to your health.*
    """
    data = {
        "model": "openai/gpt-3.5-turbo",
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Medical Report Context:\n{report_text}\n\nUser's Question:\n{question}"}
        ]
    }
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        error_details = res.json().get("error", {}).get("message", "No specific error message.")
        raise Exception(f"API Error: {e.response.status_code} - {error_details}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {e}")

# ---------- Function to handle chat logic ----------
def handle_chat(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    if prompt not in st.session_state.recent_searches:
        st.session_state.recent_searches.appendleft(prompt)
    report_context = st.session_state.get('report_text', "No report was uploaded.")
    with st.spinner("🤖 Thinking..."):
        try:
            response = ask_openrouter(prompt, report_context)
            st.session_state.messages.append({"role": "bot", "content": response})
        except Exception as e:
            st.session_state.messages.append({"role": "bot", "content": f"❌ Error: {e}"})
    st.rerun()

# ---------- Session State Initialization ----------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "bot", "content": "Hello! I'm CareBuddy. Feel free to upload a medical report using the sidebar, or ask me a general health question. I'm here to help you understand."}]
if "recent_searches" not in st.session_state:
    st.session_state.recent_searches = deque(maxlen=5)
if 'report_text' not in st.session_state:
    st.session_state.report_text = "No report was uploaded."

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Actions")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [{"role": "bot", "content": "Hello again! How can I help you today?"}]
        st.session_state.report_text = "No report was uploaded."
        st.session_state.recent_searches.clear()
        st.rerun()

    # NEW: Download Chat History Button
    if st.session_state.messages:
        chat_history_str = "\n\n".join(
            f"{msg['role'].title()}:\n{msg['content']}" for msg in st.session_state.messages
        )
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        st.download_button(
            label="💾 Download Chat",
            data=chat_history_str,
            file_name=f"CareBuddy_Chat_{timestamp}.txt",
            mime="text/plain"
        )

    st.markdown("---")
    
    st.header("Upload Report")
    uploaded_file = st.file_uploader(
        "Upload a report for context.",
        type=["pdf", "png", "jpg", "jpeg"]
    )
    if uploaded_file:
        with st.spinner("📄 Extracting text..."):
            if uploaded_file.type == "application/pdf":
                report_text = extract_text_from_pdf(uploaded_file)
            else:
                report_text = extract_text_from_image(uploaded_file)
            st.session_state.report_text = report_text
            if report_text.strip():
                st.success("✅ Report loaded!")
                with st.expander("📃 View Extracted Text"):
                    st.text_area("", report_text, height=200)
            else:
                st.warning("⚠️ No readable text found.")
    
    st.markdown("---")
    
    st.header("Recent Searches")
    if not st.session_state.recent_searches:
        st.info("Your recent questions will appear here.")
    else:
        for search in list(st.session_state.recent_searches):
            if st.button(search, key=f"recent_{search}"):
                handle_chat(search)

# ---------- Main Chat Interface ----------
for message in st.session_state.messages:
    css_class = "bubble-user" if message["role"] == "user" else "bubble-bot"
    st.markdown(f"<div class='{css_class}'>{message['content']}</div>", unsafe_allow_html=True)
st.markdown("<div style='clear: both;'></div>", unsafe_allow_html=True)

if prompt := st.chat_input("Ask a health question..."):
    handle_chat(prompt)