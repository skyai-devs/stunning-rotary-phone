import os
import smtplib
from email.mime.text import MIMEText
from typing import List

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv


SUPABASE_URL = 'https://puzorkxwukqaaupsroux.supabase.co'
SUPABASE_SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1em9ya3h3dWtxYWF1cHNyb3V4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTAwMjczOCwiZXhwIjoyMDgwNTc4NzM4fQ.ebXPmLlZAev3M3yhtoeu-q1zkELtW5wZ8hIeRVQ0cVU'
NEWS_FROM_EMAIL = 'skywave.top@gmail.com'
NEWS_FROM_NAME ="catch a crime"
NEWS_EMAIL_PASSWORD = "Lisakhanya12."
ADMIN_API_KEY = '13323543647546344734374437734637374637374637374637'
PORT = int(os.getenv("PORT", "8000"))


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465")) # 465 for SSL, 587 for TLS
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "false").lower() == "true"

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
	raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars")

if not NEWS_FROM_EMAIL or not NEWS_EMAIL_PASSWORD:
	raise RuntimeError("Missing NEWS_FROM_EMAIL or NEWS_EMAIL_PASSWORD env vars")

if not ADMIN_API_KEY:
	raise RuntimeError("Missing ADMIN_API_KEY env var")

# -------- FASTAPI APP --------
app = FastAPI(title="Catch A Crime Newsletter Server")


class NewsletterRequest(BaseModel):
subject: str
html: str


def get_all_subscriber_emails() -> List[str]:
"""
Fetch all subscriber emails from Supabase using the REST API.
"""
endpoint = f"{SUPABASE_URL}/rest/v1/newsletter_subscribers?select=email"

headers = {
"apikey": SUPABASE_SERVICE_ROLE_KEY,
"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
}

resp = requests.get(endpoint, headers=headers, timeout=30)
if resp.status_code != 200:
raise RuntimeError(f"Supabase REST error: {resp.status_code} {resp.text}")

data = resp.json()
emails = [row.get("email") for row in data if row.get("email")]
return emails


def send_email(to_email: str, subject: str, html_body: str) -> None:
"""
Send a single email via SMTP.
"""
msg = MIMEText(html_body, "html")
msg["Subject"] = subject
msg["From"] = f"{NEWS_FROM_NAME} <{NEWS_FROM_EMAIL}>"
msg["To"] = to_email

if SMTP_USE_TLS:
# TLS (e.g. port 587)
server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
server.starttls()
else:
# SSL (e.g. Gmail 465)
server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)

server.login(NEWS_FROM_EMAIL, NEWS_EMAIL_PASSWORD)
server.send_message(msg)
server.quit()


def send_newsletter_to_all(subject: str, html_body: str):
"""
Fetch all subscribers from Supabase and send the email to each.
"""
emails = get_all_subscriber_emails()
if not emails:
return {"ok": True, "count": 0, "failed": 0}

success = 0
failed = 0

for email_addr in emails:
try:
send_email(email_addr, subject, html_body)
print(f"Sent to: {email_addr}")
success += 1
except Exception as e:
print(f"Failed to send to {email_addr}: {e}")
failed += 1

return {"ok": True, "count": success, "failed": failed}


@app.get("/")
def health():
return {"status": "ok", "service": "crime-newsletter-server"}


@app.post("/send-newsletter")
def send_newsletter(
payload: NewsletterRequest,
x_admin_key: str = Header(None, alias="x-admin-key"),
):
"""
Protected endpoint to send a newsletter to all subscribers.
Requires header: x-admin-key: <ADMIN_API_KEY>
Body JSON: { "subject": "...", "html": "<h1>...</h1>" }
"""
if x_admin_key != ADMIN_API_KEY:
raise HTTPException(status_code=401, detail="Unauthorized")

try:
result = send_newsletter_to_all(payload.subject, payload.html)
return result
except Exception as e:
print("Error sending newsletter:", e)
raise HTTPException(status_code=500, detail="Server error")


# Optional CLI mode: `python main.py send`
if __name__ == "__main__":
import sys

if len(sys.argv) > 1 and sys.argv[1] == "send":
# one-off send from terminal
subject = "Catch A Crime – Safety tips & hotspot update"
html_body = """
<h2>Catch A Crime – Community Update</h2>
<p>Hi there,</p>
<p>This is our latest safety update and hotspot information for the community.</p>
<ul>
<li>• Avoid walking alone at night near high-risk hotspots.</li>
<li>• Keep your phone out of sight when using public transport.</li>
<li>• Report suspicious activity using our Catch A Crime platform.</li>
</ul>
<p>Stay safe,<br>UGU Municipality – Catch A Crime team</p>
"""
print(send_newsletter_to_all(subject, html_body))
else:
# Local dev run (Railway will use uvicorn main:app)
import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)