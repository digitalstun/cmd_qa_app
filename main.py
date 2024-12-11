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
    st.title("Windows Command Helper")
    st.write("Ask a question about Windows commands, and I'll help you find the answer!")

    # Create a text input for the user's question
    user_question = st.text_input("Enter your question:")

    # Add a submit button
    if st.button("Get Answer") and user_question:
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
