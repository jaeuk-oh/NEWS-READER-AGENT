import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(topic: str, report_md: str, notion_url: str | None = None) -> None:
    """Send the daily news briefing via Gmail.

    Args:
        topic: News topic — used in the subject line.
        report_md: Full markdown report content (plain text body).
        notion_url: If provided, prepended to the body as a link to the Notion page.

    Requires env vars: GMAIL_SENDER, GMAIL_APP_PASSWORD, GMAIL_RECIPIENT
    """
    sender    = os.environ["GMAIL_SENDER"]
    password  = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["GMAIL_RECIPIENT"]

    today   = datetime.now().strftime("%Y-%m-%d")
    subject = f"[News Briefing] {today} — {topic}"

    body_parts: list[str] = []
    if notion_url:
        body_parts.append(f"📄 Notion page: {notion_url}\n")
    body_parts.append(report_md)
    body = "\n".join(body_parts)

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    logger.info(f"Email sent to {recipient}")
