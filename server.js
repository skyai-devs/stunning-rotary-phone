import express from "express";
import cors from "cors";
import nodemailer from "nodemailer";
import { createClient } from "@supabase/supabase-js";



const SUPABASE_URL ="https://puzorkxwukqaaupsroux.supabase.co";
const SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1em9ya3h3dWtxYWF1cHNyb3V4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTAwMjczOCwiZXhwIjoyMDgwNTc4NzM4fQ.ebXPmLlZAev3M3yhtoeu-q1zkELtW5wZ8hIeRVQ0cVU"; 
const SMTP_HOST = "smtp.gmail.com";
const SMTP_PORT = "587";
const SMTP_USER = "skywave.top@gmail.com";
const SMTP_PASSWORD ="xugh akbm ogpi fjhw";
const FROM_EMAIL = "skywave.top@gmail.com";

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.");
}

if (!SMTP_HOST || !SMTP_USER || !SMTP_PASSWORD) {
throw new Error("SMTP_HOST, SMTP_USER, and SMTP_PASSWORD must be set.");
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);


const transporter = nodemailer.createTransport({
host: SMTP_HOST,
port: SMTP_PORT,
secure: SMTP_PORT === 465, 
auth: {
user: SMTP_USER,
pass: SMTP_PASSWORD
}
});


transporter.verify((err, success) => {
if (err) {
console.error("[SMTP] Verification failed:", err);
} else {
console.log("[SMTP] Ready to send emails");
}
});



const app = express();
app.use(cors({ origin: "*", credentials: false }));
app.use(express.json()); 

async function sendEmail(to, subject, htmlBody) {
console.log(`[sendEmail] Sending to ${to} | subject="${subject}"`);

const mailOptions = {
from: FROM_EMAIL,
to,
subject,
text: "This email contains HTML content. Please enable HTML view.",
html: htmlBody
};

await transporter.sendMail(mailOptions);
console.log(`[sendEmail] Successfully sent to ${to}`);
}

async function getAllSubscriberEmails() {
console.log("[getAllSubscriberEmails] Loading from Supabase...");
const { data, error } = await supabase
.from("newsletter_subscribers")
.select("email");

if (error) {
console.error("[getAllSubscriberEmails] Supabase error:", error);
throw new Error("Supabase error: " + error.message);
}

const rows = data || [];
console.log("[getAllSubscriberEmails] Rows:", rows.length);

const unique = Array.from(
new Set(
rows
.map(r => (r.email || "").trim())
.filter(e => e.length > 0)
)
);

console.log("[getAllSubscriberEmails] Unique emails:", unique);
return unique;
}



app.get("/", (req, res) => {
res.json({ status: "ok", message: "Catch A Crime newsletter server running." });
});


app.post("/send-newsletter", async (req, res) => {
const payload = req.body || {};
console.log("[/send-newsletter] Payload:", payload);

const subject = String(payload.subject || "").trim();
const htmlBody = String(payload.html_body || "").trim();
const testEmailRaw = payload.test_email;
const sendTestOnly = Boolean(payload.send_test_only);

const testEmail =
typeof testEmailRaw === "string" && testEmailRaw.trim().length > 0
? testEmailRaw.trim()
: null;

if (!subject || !htmlBody) {
return res
.status(400)
.json({ error: "Subject and html_body are required." });
}


if (sendTestOnly) {
if (!testEmail) {
return res
.status(400)
.json({ error: "test_email is required when send_test_only is true." });
}

try {
await sendEmail(testEmail, subject, htmlBody);
return res.json({
message: `Test email sent to ${testEmail}.`,
sent_count: 1,
test_only: true
});
} catch (err) {
console.error("[/send-newsletter] Error sending test:", err);
return res
.status(500)
.json({ error: "Failed to send test email: " + err.message });
}
}


if (testEmail) {
try {
console.log("[/send-newsletter] Sending pre-broadcast test to", testEmail);
await sendEmail(testEmail, subject, htmlBody);
} catch (err) {
console.error("[/send-newsletter] Error sending pre-broadcast test:", err);
return res.status(500).json({
error: "Failed to send test email before broadcast: " + err.message
});
}
}

let subscribers;
try {
subscribers = await getAllSubscriberEmails();
} catch (err) {
console.error("[/send-newsletter] Error loading subscribers:", err);
return res
.status(500)
.json({ error: "Failed to load subscribers: " + err.message });
}

if (!subscribers || subscribers.length === 0) {
console.log("[/send-newsletter] No subscribers found.");
return res.json({
message: "No subscribers found in newsletter_subscribers.",
sent_count: 0,
test_only: false
});
}

console.log(
`[/send-newsletter] Broadcasting to ${subscribers.length} subscribers...`
);

let sentCount = 0;
let errors = 0;

for (const email of subscribers) {
try {
await sendEmail(email, subject, htmlBody);
sentCount += 1;
} catch (err) {
console.error(`[send-newsletter] Error sending to ${email}:`, err);
errors += 1;
}
}

const msg = `Newsletter send finished: ${sentCount} success, ${errors} failed.`;
console.log("[/send-newsletter] " + msg);

return res.json({
message: msg,
sent_count: sentCount,
test_only: false
});
});



const PORT = parseInt(process.env.PORT || "8000", 10);
app.listen(PORT, () => {
console.log(`Newsletter server listening on port ${PORT}`);
});