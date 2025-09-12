import os
import pdfplumber
from pptx import Presentation
from flask import Flask, render_template, request, session, redirect, url_for, abort
from dotenv import load_dotenv

import google.generativeai as genai
from google_auth_oauthlib.flow import Flow
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- ENV ---
load_dotenv()
ENV = os.getenv("APP_ENV", "local").lower()  # local / prod
PORT = int(os.getenv("PORT", 5000))

# --- Flask app ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ლოკალზე ქუქი პარამეტრები
if ENV == "local":
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_SAMESITE="Lax",
        PREFERRED_URL_SCHEME="http",
    )
else:
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="None",
        PREFERRED_URL_SCHEME="https",
    )

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Gemini ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))  # თუ არაა საჭირო, დატოვე ცარიელი
model = genai.GenerativeModel("gemini-1.5-flash")

# --- Helpers ---
def extract_text_from_pdf(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"[PDF Error] {e}")
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
        print(f"[PPTX Error] {e}")
    return text

def analyze_idea(idea_text):
    prompt = f"""
შეაფასე შემდეგი ბიზნეს იდეა დეტალურად, შემდეგი სტრუქტურის მიხედვით:

ბიზნეს იდეა:
{idea_text}

1. იდეის მოკლე რეზიუმე
2. მიზნობრივი აუდიტორია
3. მონეტიზაციის გზები
4. ანალოგიური პროდუქტები ან კონკურენტები
5. იდეის სიძლიერეები და სუსტი მხარეები
6. გრძელვადიანი მდგრადობის პროგნოზი
7. რეკომენდაცია იდეის გაუმჯობესებისთვის
"""
    try:
        if not os.environ.get("GEMINI_API_KEY"):
            return "⚠️ GEMINI_API_KEY არაა მითითებული (.env-ში) — პასუხი დაგენერირდება მხოლოდ მაშინ, როცა ჩასვამ."
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"❌ Gemini API შეცდომა: {e}"

def save_analysis_to_file(content, filename="analysis.txt"):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def upload_to_user_drive(filepath, filename, folder_id=None):
    # საჭირო ხდება OAuth-ის გავლა /login-ით
    if "credentials" not in session:
        return None
    creds = google.oauth2.credentials.Credentials(**session['credentials'])
    service = build('drive', 'v3', credentials=creds)

    metadata = {'name': filename}
    if folder_id:
        metadata['parents'] = [folder_id]

    media = MediaFileUpload(filepath, resumable=True)
    created = service.files().create(body=metadata, media_body=media, fields='id').execute()
    file_id = created.get('id')

    # სურვილისამებრ გახადე საჯარო ბმული
    service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
    return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

def save_and_return_link(idea_text, base_filename="idea_analysis"):
    result = analyze_idea(idea_text)
    filename = f"{base_filename}.txt"
    filepath = save_analysis_to_file(result, filename)
    drive_link = upload_to_user_drive(filepath, filename)

    hist = session.get('history', [])
    hist.append({'filename': filename, 'drive_link': drive_link})
    session['history'] = hist[-30:]
    return drive_link, result

# --- OAuth (Web Client, localhost) ---
# შენს Google OAuth client-ს უნდა ჰქონდეს Authorized redirect URI:
#   http://localhost:5000/oauth2callback
# და JavaScript origin:
#   http://localhost:5000
def _redirect_uri():
    # ლოკალზე HTTP, პროდზე HTTPS
    scheme = "http" if ENV == "local" else "https"
    return url_for("oauth2callback", _external=True, _scheme=scheme)

@app.before_request
def require_login():
    # ლოგინამდე დაშვებული endpoint-ები
    allowed = {'login', 'oauth2callback', 'static', 'index'}
    if request.endpoint in allowed or 'credentials' in session:
        return
    return redirect(url_for('login'))

@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=_redirect_uri(),
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["state"] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    state = session.get("state")
    if not state:
        # ლოკალზე უბრალოდ დავაბრუნოთ login-ზე, რომ თავიდან დაიწყოს flow
        return redirect(url_for("login"))

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        state=state,
        redirect_uri=_redirect_uri(),
    )
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    session.pop("state", None)
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Views ---
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    drive_link = None
    error = None

    if request.method == "POST":
        text_idea = request.form.get("text_idea")
        file = request.files.get("file")
        idea_text = ""
        source_name = "text_input"

        if text_idea and text_idea.strip():
            idea_text = text_idea.strip()
        elif file and file.filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            source_name = file.filename
            if filepath.lower().endswith(".pdf"):
                idea_text = extract_text_from_pdf(filepath)
            elif filepath.lower().endswith(".pptx"):
                idea_text = extract_text_from_pptx(filepath)
            else:
                error = "❌ მხოლოდ .pdf და .pptx ფაილებია მხარდაჭერილი."
        else:
            error = "გთხოვთ, შეიყვანეთ ტექსტი ან ატვირთეთ ფაილი."

        if not error and idea_text.strip():
            drive_link, result = save_and_return_link(idea_text, base_filename=source_name)

    return render_template("index.html",
                           result=result,
                           drive_link=drive_link,
                           error=error,
                           history=session.get('history', []))

# --- Run local ---
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=PORT)
