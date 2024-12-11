import os
import streamlit as st
import google.generativeai as genai
import re

# Configure page settings
st.set_page_config(
    page_title="Windows Command Helper",
    page_icon="💻",
    layout="wide"
)

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
        modified_question = f"""Answer this question for the Windows command line, prioritizing command-line solutions first, then providing alternative methods.  Return the command as the first line, followed by the explanation and alternative methods.: {question}"""
        response = chat_session.send_message(modified_question)
        text = response.text
        match = re.search(r"(?:```batch)?\s*(.*?)\s*(?:```)?\n(.*)", text, re.DOTALL | re.IGNORECASE)
        if match:
            command = match.group(1).strip()
            explanation = match.group(2).strip()
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

    st.title("Windows Command Helper")
    st.write("Ask a question about Windows commands, and I'll help you find the answer!")

    # Create a text input for the user's question with enter key functionality
    user_question = st.text_input(
        "Enter your question:",
        key="question_input",
        on_change=None,
        args=None,
        kwargs=None,
    )

    # Handle both enter key and button click
    submit_button = st.button("Get Answer")
    
    if (user_question and submit_button) or (user_question and st.session_state.get('question_input') == user_question):
        # Show a spinner while processing
        with st.spinner("Getting response..."):
            response = get_gemini_response(user_question)

        # Display the response in separate sections
        if response["command"]:
            st.subheader("Command:")
            st.code(response["command"], language="batch")
            
            st.subheader("Explanation:")
            st.write(response["explanation"])
        else:
            st.error(response["explanation"])

if __name__ == "__main__":
    main()
