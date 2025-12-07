import express from "express";
import cors from "cors";
import { createClient } from "@supabase/supabase-js";
import fetch from "node-fetch";

const SUPABASE_URL = "https://puzorkxwukqaaupsroux.supabase.co";
const SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1em9ya3h3dWtxYWF1cHNyb3V4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTAwMjczOCwiZXhwIjoyMDgwNTc4NzM4fQ.ebXPmLlZAev3M3yhtoeu-q1zkELtW5wZ8hIeRVQ0cVU";
const RESEND_API_KEY = "re_d8u2SGXU_FUwr3BwkDgcSrLHc3FkLusVy";
const FROM_EMAIL ="onboarding@resend.dev";
const PORT = "8080";

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
throw new Error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set");
}
if (!RESEND_API_KEY || !FROM_EMAIL) {
throw new Error("RESEND_API_KEY and FROM_EMAIL must be set");
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

const app = express();
app.use(cors());
app.use(express.json());

async function sendEmail(to, subject, html) {
const resp = await fetch("https://api.resend.com/emails", {
method: "POST",
headers: {
Authorization: `Bearer ${RESEND_API_KEY}`,
"Content-Type": "application/json",
},
body: JSON.stringify({
from: FROM_EMAIL,
to: [to],
subject,
html,
}),
});

if (!resp.ok) {
const text = await resp.text();
console.error("[Resend] Error", resp.status, text.slice(0, 300));
throw new Error("Failed to send email via Resend");
}
}

app.get("/", (_req, res) => {
res.send("Catch A Crime newsletter server is running.");
});

app.post("/send-newsletter", async (req, res) => {
try {
const { subject, html_body, test_email, send_test_only } = req.body || {};

if (!subject || !html_body) {
return res
.status(400)
.json({ error: "subject and html_body are required" });
}

if (send_test_only) {
if (!test_email) {
return res
.status(400)
.json({ error: "test_email is required for test send" });
}

await sendEmail(test_email, subject, html_body);
return res.json({
ok: true,
mode: "test",
sent: 1,
message: `Test email sent to ${test_email}`,
});
}

const { data, error } = await supabase
.from("newsletter_subscribers")
.select("email")
.neq("email", null);

if (error) {
console.error("Supabase select error:", error);
return res
.status(500)
.json({ error: "Failed to fetch subscribers from Supabase" });
}

const emails = (data || [])
.map((row) => row.email)
.filter((e) => typeof e === "string" && e.includes("@"));

if (!emails.length) {
return res.json({
ok: true,
mode: "broadcast",
sent: 0,
total: 0,
message: "No subscribers found.",
});
}

let sentCount = 0;

for (const email of emails) {
try {
await sendEmail(email, subject, html_body);
sentCount += 1;
console.log("[sendEmail] Sent to", email);
} catch (err) {
console.error("[sendEmail] Error sending to", email, err.message);
}
}

return res.json({
ok: true,
mode: "broadcast",
total: emails.length,
sent: sentCount,
message: `Broadcast finished. Sent to ${sentCount}/${emails.length} subscribers.`,
});
} catch (err) {
console.error("[/send-newsletter] Handler error:", err);
return res
.status(500)
.json({ error: "Unexpected server error", detail: err.message });
}
});

app.listen(PORT, () => {
console.log(`Newsletter server listening on port ${PORT}`);
});