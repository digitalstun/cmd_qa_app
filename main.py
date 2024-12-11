import os
import streamlit as st
import google.generativeai as genai
import re
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="Windows Command Helper",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapse on small screens
)

# Get API key from environment variable or Streamlit secrets
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]

# Configure Gemini API key
genai.configure(api_key=api_key)

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
        - If you receive an error please adjust your question and try again

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
