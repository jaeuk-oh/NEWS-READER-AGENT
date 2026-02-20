import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import markdown2

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email_to_subscriber(recipient: str, topic: str, report_md: str) -> None:
    """Send a news briefing to a specific subscriber.

    Args:
        recipient: Subscriber email address.
        topic: News topic — used in the subject line.
        report_md: Full markdown report content (plain text body).
    """
    sender   = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    today   = datetime.now().strftime("%Y-%m-%d")
    subject = f"[News Briefing] {today} — {topic}"

    html_body = markdown2.markdown(
        report_md, extras=["fenced-code-blocks", "tables", "header-ids"]
    )

    msg = MIMEMultipart("alternative")
    msg["From"]    = sender
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(report_md, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    logger.info(f"Subscriber email sent to {recipient}")
