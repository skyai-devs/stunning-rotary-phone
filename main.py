import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from supabase import create_client, Client


SUPABASE_URL = "https://puzorkxwukqaaupsroux.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1em9ya3h3dWtxYWF1cHNyb3V4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTAwMjczOCwiZXhwIjoyMDgwNTc4NzM4fQ.ebXPmLlZAev3M3yhtoeu-q1zkELtW5wZ8hIeRVQ0cVU"

SMTP_HOST = os.getenv("SMTP_HOST") 
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = "skywave.top@gmail.com"
SMTP_PASSWORD = "ownr wzmc vald fsak"
FROM_EMAIL = "skywave.top@gmail.com"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
	raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")

if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
	raise RuntimeError("SMTP_HOST, SMTP_USER, and SMTP_PASSWORD must be set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="Catch A Crime – Newsletter API")


app.add_middleware(
CORSMiddleware,
allow_origins=["*"], 
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)




class NewsletterPayload(BaseModel):
	subject: str
	html_body: str
	test_email: Optional[EmailStr] = None
	send_test_only: bool = False


class SendResult(BaseModel):
	message: str
	sent_count: int = 0
	test_only: bool = False



def send_email(to_email: str, subject: str, html_body: str):
	"""
	Send one HTML email using SMTP.
	"""
	msg = MIMEMultipart("alternative")
	msg["Subject"] = subject
	msg["From"] = FROM_EMAIL
	msg["To"] = to_email

	text_body = "This email contains HTML content. Please enable HTML view."
	part_text = MIMEText(text_body, "plain")
	part_html = MIMEText(html_body, "html")

	msg.attach(part_text)
	msg.attach(part_html)

	
	with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
		server.starttls()
		server.login(SMTP_USER, SMTP_PASSWORD)
		server.sendmail(FROM_EMAIL, [to_email], msg.as_string())


def get_all_subscriber_emails() -> List[str]:
	"""
	Fetch all distinct emails from the newsletter_subscribers table in Supabase.
	Uses the service_role key so it ignores RLS and can read everything.
	"""
	resp = supabase.table("newsletter_subscribers").select("email").execute()
	rows = resp.data or []

	emails: List[str] = []
	for row in rows:
		email = row.get("email")
		if email and isinstance(email, str):
			emails.append(email.strip())

	unique = sorted({e for e in emails if e})
	return unique



@app.get("/")
def root():
	return {"status": "ok", "message": "Catch A Crime newsletter server running."}


@app.post("/send-newsletter", response_model=SendResult)
def send_newsletter(payload: NewsletterPayload):
	"""
	Called by newsletter_admin.html (your admin page).

	- If send_test_only = True: send to test_email only.
	- Else: optional test to test_email, then broadcast to all subscribers.
	"""
	subject = payload.subject.strip()
	html_body = payload.html_body.strip()

	if not subject or not html_body:
		raise HTTPException(status_code=400, detail="Subject and body are required.")

	
	if payload.send_test_only:
		if not payload.test_email:
			raise HTTPException(status_code=400, detail="Test email address is required for test mode.")
		try:
			send_email(str(payload.test_email), subject, html_body)
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"Failed to send test email: {e}")
		return SendResult(
			message=f"Test email sent to {payload.test_email}.",
			sent_count=1,
			test_only=True
		)


	if payload.test_email:
		try:
			send_email(str(payload.test_email), subject, html_body)
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"Failed to send test email before broadcast: {e}")

	try:
		subscribers = get_all_subscriber_emails()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to load subscribers: {e}")

	if not subscribers:
		return SendResult(
			message="No subscribers found in newsletter_subscribers.",
			sent_count=0,
			test_only=False
		)

	sent_count = 0
	errors = 0

	for email in subscribers:
		try:
			send_email(email, subject, html_body)
			sent_count += 1
		except Exception as e:
			print(f"Error sending to {email}: {e}")
			errors += 1

	msg = f"Newsletter sent to {sent_count} subscribers."
	if errors:
		msg += f" {errors} emails failed (see logs)."

	return SendResult(
		message=msg,
		sent_count=sent_count,
		test_only=False
	)



if __name__ == "__main__":
	import uvicorn

	port = int(os.getenv("PORT", "8000"))
	uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)