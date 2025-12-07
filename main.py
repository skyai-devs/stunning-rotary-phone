import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from supabase import create_client, Client



SUPABASE_URL = "https://puzorkxwukqaaupsroux.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1em9ya3h3dWtxYWF1cHNyb3V4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTAwMjczOCwiZXhwIjoyMDgwNTc4NzM4fQ.ebXPmLlZAev3M3yhtoeu-q1zkELtW5wZ8hIeRVQ0cVU"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = "skywave.top@gmail.com"
SMTP_PASSWORD = "xugh akbm ogpi fjhw"
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



def send_email(to_email: str, subject: str, html_body: str):
	"""
	Send one HTML email using SMTP.
	Logs what it's doing so you can see it in Railway logs.
	"""
	print(f"[send_email] Preparing to send to {to_email} with subject '{subject}'")

	msg = MIMEMultipart("alternative")
	msg["Subject"] = subject
	msg["From"] = FROM_EMAIL
	msg["To"] = to_email


	text_body = "This email contains HTML content. Please enable HTML view."
	part_text = MIMEText(text_body, "plain")
	part_html = MIMEText(html_body, "html")

	msg.attach(part_text)
	msg.attach(part_html)

	try:
		with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
			print(f"[send_email] Connecting to SMTP {SMTP_HOST}:{SMTP_PORT}")
			server.starttls()
			print("[send_email] TLS started, logging in...")
			server.login(SMTP_USER, SMTP_PASSWORD)
			print(f"[send_email] Logged in as {SMTP_USER}, sending...")
			server.sendmail(FROM_EMAIL, [to_email], msg.as_string())
			print(f"[send_email] Successfully sent to {to_email}")
	except Exception as e:
		print(f"[send_email] ERROR sending to {to_email}: {e}")
		raise


def get_all_subscriber_emails() -> List[str]:
	"""
	Fetch all distinct emails from newsletter_subscribers (Supabase).
	Uses service_role key so it ignores RLS.
	"""
	print("[get_all_subscriber_emails] Loading from Supabase...")
	resp = supabase.table("newsletter_subscribers").select("email").execute()

	if resp.error:
		print(f"[get_all_subscriber_emails] Supabase error: {resp.error}")
		raise RuntimeError(f"Supabase error: {resp.error}")

	rows = resp.data or []
	print(f"[get_all_subscriber_emails] Raw rows count: {len(rows)}")

	emails: List[str] = []
	for row in rows:
		email = row.get("email")
		if email and isinstance(email, str):
			emails.append(email.strip())

	unique = sorted({e for e in emails if e})
	print(f"[get_all_subscriber_emails] Unique emails: {unique}")
	return unique



@app.get("/")
def root():
	return {"status": "ok", "message": "Catch A Crime newsletter server running."}


@app.post("/send-newsletter")
async def send_newsletter(request: Request):
	"""
	Called by newsletter_admin.html.

	Expected JSON:
	{
	"subject": "string",
	"html_body": "string",
	"test_email": "optional string",
	"send_test_only": bool
	}
	"""
	try:
		payload = await request.json()
	except Exception:
		raise HTTPException(status_code=400, detail="Invalid JSON body.")

	print(f"[send-newsletter] Payload received: {payload}")

	subject = str(payload.get("subject", "")).strip()
	html_body = str(payload.get("html_body", "")).strip()
	test_email_raw = payload.get("test_email")
	send_test_only = bool(payload.get("send_test_only", False))

	test_email = None
	if isinstance(test_email_raw, str) and test_email_raw.strip():
		test_email = test_email_raw.strip()

	if not subject or not html_body:
		raise HTTPException(status_code=400, detail="Subject and html_body are required.")


	if send_test_only:
		if not test_email:
			raise HTTPException(status_code=400, detail="test_email is required when send_test_only is true.")
		print(f"[send-newsletter] Test-only mode. Sending to {test_email}")
		try:
			send_email(test_email, subject, html_body)
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"Failed to send test email: {e}")
		return {
			"message": f"Test email sent to {test_email}.",
			"sent_count": 1,
			"test_only": True
		}

	if test_email:
		print(f"[send-newsletter] Broadcast mode: sending test first to {test_email}")
		try:
			send_email(test_email, subject, html_body)
		except Exception as e:
			raise HTTPException(status_code=500, detail=f"Failed to send test email before broadcast: {e}")

	try:
		subscribers = get_all_subscriber_emails()
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to load subscribers: {e}")

	if not subscribers:
		print("[send-newsletter] No subscribers found.")
		return {
			"message": "No subscribers found in newsletter_subscribers.",
			"sent_count": 0,
			"test_only": False
		}

	print(f"[send-newsletter] Sending newsletter to {len(subscribers)} subscribers...")
	sent_count = 0
	errors = 0

	for email in subscribers:
		try:
			send_email(email, subject, html_body)
			sent_count += 1
		except Exception as e:
			print(f"[send-newsletter] Error sending to {email}: {e}")
			errors += 1

	msg = f"Newsletter sent attempt finished: {sent_count} success, {errors} failed."
	print("[send-newsletter]", msg)

	return {
		"message": msg,
		"sent_count": sent_count,
		"test_only": False
	}


if __name__ == "__main__":
	import uvicorn
	port = int(os.getenv("PORT", "8000"))
	uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)