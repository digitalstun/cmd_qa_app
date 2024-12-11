import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
import re

app = Flask(__name__, template_folder='templates')

# Configure Gemini API key (replace with your actual key)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Model configuration
generation_config = {
    "temperature": 0.7,  # Adjust for creativity vs. accuracy
    "max_output_tokens": 512,  # Limit response length
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

def get_gemini_response(question):
    try:
        chat_session = model.start_chat()
        modified_question = f"""Answer this question for the Windows command line, prioritizing command-line solutions first, then providing alternative methods.  Return the command as the first line, followed by the explanation and alternative methods.: {question}"""
        response = chat_session.send_message(modified_question)
        text = response.text
        # More robust regex to handle variations in response format, including backticks
        match = re.search(r"(?:```batch)?\s*(.*?)\s*(?:```)?\n(.*)", text, re.DOTALL | re.IGNORECASE)
        if match:
            command = match.group(1).strip()
            explanation = match.group(2).strip()
            return {"command": command, "explanation": explanation}
        else:
            return {"command": None, "explanation": "Could not extract command from response."}
    except Exception as e:
        return {"command": None, "explanation": f"Error: {e}"}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    query = data["query"]
    response = get_gemini_response(query)
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
