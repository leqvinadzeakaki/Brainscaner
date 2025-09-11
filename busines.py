import os
import pathlib
import pickle
import pdfplumber
from pptx import Presentation
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import google.generativeai as genai
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import google.oauth2.credentials

# --- Flask App Configuration ---
app = Flask(_name_)
load_dotenv()
app.secret_key = os.getenv("FLASK_SECRET_KEY", "random_default_secret_key")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # მხოლოდ დეველოპმენტისთვის

# --- Gemini API Configuration ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# --- Helpers ---
def extract_text_from_pdf(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        text = f"PDF წაკითხვის შეცდომა: {e}"
    return text

def extract_text_from_pptx(path):
    text = ""
    try:
        prs = Presentation(path)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    except Exception as e:
        text = f"PPTX წაკითხვის შეცდომა: {e}"
    return text

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            ext = pathlib.Path(file.filename).suffix.lower()
            text = ""
            if ext == ".pdf":
                text = extract_text_from_pdf(filepath)
            elif ext == ".pptx":
                text = extract_text_from_pptx(filepath)
            elif ext == ".txt":
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                text = "ფაილის ფორმატი არ არის მხარდაჭერილი."

            if text.strip():
                try:
                    response = model.generate_content(text)
                    result = response.text
                except Exception as e:
                    result = f"AI ანალიზის შეცდომა: {e}"
            else:
                result = "ფაილიდან ტექსტი ვერ ამოიკითხა."

            return render_template("index.html", result=result)

    return render_template("index.html", result=None)


# --- Main ---
if _name_ == "_main_":
    app.run(host="0.0.0.0", port=5000, debug=True)
