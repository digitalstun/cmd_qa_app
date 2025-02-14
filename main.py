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

# Network command templates and security patterns
NETWORK_COMMAND_TEMPLATES = {
    "ip_config": "ipconfig /all",
    "port_scan": "Test-NetConnection -ComputerName {target} -Port {port}",
    "dns_check": "Resolve-DnsName {hostname}",
    "traceroute": "tracert {target}"
}

SAFE_INPUT_REGEX = r"^[a-zA-Z0-9\-\.\:\/\s]{1,100}$"

def get_gemini_response(question):
    try:
        # Validate input for network commands
        if not re.match(SAFE_INPUT_REGEX, question):
            return {"command": None, "explanation": "Invalid input detected. Only alphanumeric characters and common network symbols allowed."}
            
        chat_session = model.start_chat()
        
        # Enhanced prompt with network command context
        modified_question = f"""For Windows network/IP commands: {question}
        - Prioritize PowerShell over CMD
        - Include security warnings for dangerous commands
        - Suggest alternative GUI tools where applicable
        Format: [Command]\n[Explanation]\n[Security Note]\n[Alternatives]"""
        
        response = chat_session.send_message(modified_question)
        text = response.text
        
        # Enhanced parsing for network commands
        match = re.search(
            r"^((?:[A-Za-z0-9\-_]+\.exe\s)?[^\n`]+)(?:\n+)(.*?)(?:\n+Security Note:\s*(.*?))?(?:\n+Alternatives:\s*(.*))?$",
            text.lstrip(),
            re.DOTALL
        )
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
        1. Type your Windows command or network-related question
        2. For network commands, include parameters like:
           - IP addresses (192.168.1.1)
           - Hostnames (example.com)
           - Port numbers (80, 443)
        3. Press Enter or click 'Get Answer' to submit
        4. Review command with security warnings
        
        ### Example Network Questions
        - How to scan open ports on 192.168.1.100?
        - What's the DNS record for api.example.com?
        - Trace route to 8.8.8.8
        - Check firewall rules for port 3389
        
        ### Security Tips
        - Validate commands before execution
        - Use dedicated network testing environments
        - Avoid sharing sensitive IP/host information
        - Monitor network changes carefully

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
                copy_button_key = f"copy_button_{response['command']}"
                if st.button("📋 Copy command", key=copy_button_key):
                    st.session_state[f"copied_{copy_button_key}"] = True
                    st.session_state[f"show_tooltip_{copy_button_key}"] = True
                    
                if st.session_state.get(f"show_tooltip_{copy_button_key}", False):
                    st.markdown("<span class='copy-tooltip show'>Copied!</span>", unsafe_allow_html=True)
                    
                    st.session_state[f"show_tooltip_{copy_button_key}"] = False
                    
                    import time
                    time.sleep(2)
                    
                    st.session_state[f"copied_{copy_button_key}"] = False
                    
                
                
                st.markdown(f"""
                    <h3 style='color: white;'>Explanation:</h3>
                """, unsafe_allow_html=True)
                
                st.write(response["explanation"])
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error(response["explanation"])

if __name__ == "__main__":
    main()

