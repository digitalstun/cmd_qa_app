import os
import streamlit as st
import google.generativeai as genai
import re

# Configure page settings
st.set_page_config(
    page_title="Windows Command Helper",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapse on small screens
)

# Custom CSS for responsive design
st.markdown("""
    <style>
    /* Main container padding - ensure enough space at top */
    .main .block-container {
        padding: 2rem 1rem 1rem 1rem !important;
        max-width: 100% !important;
    }
    
    /* App header/title container - improve visibility */
    .app-header {
        padding: 1.5rem;
        margin: 0 0 1rem 0;
        background-color: #1E1E1E;
        border-radius: 10px;
        width: 100%;
        display: block;
    }
    
    /* Title styling - ensure full visibility */
    .app-title {
        color: white !important;
        font-size: 2rem !important;
        font-weight: bold !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.4 !important;
    }
    
    /* Title container span - improve emoji alignment */
    .app-title span {
        display: inline-flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
        vertical-align: middle !important;
    }

    /* Ensure emoji is properly aligned */
    .app-title span img {
        vertical-align: middle !important;
    }
    
    /* Remove default Streamlit container padding that might affect title */
    .element-container:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Custom container adjustments */
    .custom-container {
        background-color: #1E1E1E;  /* Match dark theme */
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid #333;
        color: white;
    }
    
    /* Header adjustments */
    h1, h2, h3 {
        margin: 0 !important;
        padding: 0.5rem 0 !important;
        color: white;
    }
    
    /* Input field adjustments */
    .stTextInput {
        margin: 1rem 0 0.5rem 0;
    }
    
    .stTextInput > div > div > input {
        padding: 0.5rem 1rem;
        font-size: 16px;
        border-radius: 10px;
        background-color: #2E2E2E;
        color: white;
        border: 1px solid #333;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        padding: 0.5rem;
        border-radius: 10px;
        font-weight: 500;
        background-color: #2E2E2E;
        color: white;
        border: 1px solid #333;
    }
    
    /* Code block styling */
    .stCodeBlock {
        margin: 0.5rem 0;
        background-color: #2E2E2E !important;
    }
    
    /* Copy button styling */
    .copy-button {
        background: none;
        border: none;
        color: #4CAF50;
        cursor: pointer;
        padding: 0.25rem 0;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    /* Remove extra whitespace */
    .element-container {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stMarkdown {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Main content column styling */
    [data-testid="column"] {
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Responsive adjustments */
    @media (max-width: 640px) {
        .main .block-container {
            padding: 0 !important;
        }
        .custom-container {
            padding: 0.75rem;
            margin: 0.25rem 0;
        }
    }

    /* Copy notification styling */
    .copy-tooltip {
        position: absolute;
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.875rem;
        margin-left: 10px;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }

    .copy-tooltip.show {
        opacity: 1;
    }

    .copy-button-container {
        display: inline-flex;
        align-items: center;
        position: relative;
    }

    .copy-button {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        color: #4CAF50;
        cursor: pointer;
        padding: 0.25rem 0;
    }

    .copy-button:hover {
        color: #69DB7C;
    }
    </style>
""", unsafe_allow_html=True)

# Configure Gemini API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Model configuration
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 512,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

def get_gemini_response(question):
    try:
        chat_session = model.start_chat()
        modified_question = f"""Answer this question for the Windows command line, prioritizing command-line solutions first, then providing alternative methods. Return the command as the first line WITHOUT any backticks or code formatting, followed by the explanation and alternative methods.: {question}"""
        response = chat_session.send_message(modified_question)
        text = response.text
        
        # Updated regex to better handle command extraction
        match = re.search(r"^([^`\n]+)(?:\n|$)(.*)", text.lstrip(), re.DOTALL)
        if match:
            command = match.group(1).strip()
            explanation = match.group(2).strip()
            # Clean any remaining backticks from the command
            command = command.replace('`', '').strip()
            return {"command": command, "explanation": explanation}
        else:
            return {"command": None, "explanation": "Could not extract command from response."}
    except Exception as e:
        return {"command": None, "explanation": f"Error: {e}"}

def main():
    # Sidebar with instructions
    with st.sidebar:
        st.header("📖 How to Use")
        st.markdown("""
        ### Quick Start Guide
        1. Type your Windows command-related question in the input box
        2. Press Enter or click 'Get Answer' to submit
        3. View the command and its explanation
        
        ### Example Questions
        - How do I list all files in a directory?
        - How can I find large files on my system?
        - How do I check my IP address?
        
        ### Tips
        - Be specific in your questions
        - Questions can be in natural language
        - Commands are provided with detailed explanations
        """)

    # Main content with adjusted layout
    col1, col2, col3 = st.columns([1, 8, 1])
    
    with col2:
        # Updated title markup with better structure
        st.markdown("""
        <div class="app-header">
            <div class="app-title">
                <span>🖥️ Windows Command Helper</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Create a text input for the user's question
        user_question = st.text_input(
            "",
            key="question_input",
            placeholder="Ask a question about Windows commands...",
            help="Press Enter or click 'Get Answer' to submit",
        )

        # Handle both enter key and button click
        submit_button = st.button("Get Answer")
        
        if (user_question and submit_button) or (user_question and st.session_state.get('question_input') == user_question):
            with st.spinner("Getting response..."):
                response = get_gemini_response(user_question)

            if response["command"]:
                st.markdown("""
                <div class='custom-container'>
                    <h3 style='margin-top: 0; color: white;'>Command:</h3>
                """, unsafe_allow_html=True)
                
                st.code(response["command"], language="batch")
                
                # Updated copy button with inline tooltip
                st.markdown(f"""
                    <div class="copy-button-container">
                        <button class="copy-button" onclick="
                            navigator.clipboard.writeText('{response["command"]}');
                            this.nextElementSibling.classList.add('show');
                            setTimeout(() => {{
                                this.nextElementSibling.classList.remove('show');
                            }}, 2000);
                        ">
                            📋 Copy command
                        </button>
                        <span class="copy-tooltip">Copied!</span>
                    </div>
                    <h3 style='color: white;'>Explanation:</h3>
                """, unsafe_allow_html=True)
                
                st.write(response["explanation"])
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error(response["explanation"])

if __name__ == "__main__":
    main()
