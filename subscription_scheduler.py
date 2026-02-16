"""
Subscription-based news pipeline scheduler.

Checks every minute for active subscriptions whose schedule_time matches
the current HH:MM.  Groups subscribers by topic so the CrewAI pipeline
runs only once per unique topic, then emails each subscriber in that group.

Start:  uv run python subscription_scheduler.py
Stop:   Ctrl+C
"""

import os
import time
import logging
from datetime import datetime
from itertools import groupby
from operator import itemgetter

import dotenv
import schedule

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPORT_FILE = "output/final_report.md"


def _run_for_topic(topic: str) -> str | None:
    """Run the CrewAI pipeline for *topic* and return the report markdown.

    Returns None on failure.
    """
    try:
        from main import run_crew

        run_crew(topic)
    except Exception as e:
        logger.error(f"❌ Crew failed for topic '{topic}': {e}")
        return None

    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report_md = f.read()
    except FileNotFoundError:
        logger.error(f"❌ {REPORT_FILE} not found after crew run.")
        return None

    # Optional translation
    try:
        from services.translator import translate_to_korean

        report_md = translate_to_korean(report_md)
        logger.info(f"Report translated for topic '{topic}'.")
    except Exception as e:
        logger.warning(f"Translation skipped for '{topic}': {e}")

    return report_md


def check_and_run():
    """Check DB for due subscriptions and dispatch pipelines."""
    import db
    from services.notifier import send_email_to_subscriber

    now_hhmm = datetime.now().strftime("%H:%M")
    due = db.get_due_subscriptions(now_hhmm)

    if not due:
        return

    logger.info(f"Found {len(due)} due subscription(s) at {now_hhmm}")

    # Group by topic to avoid redundant pipeline runs
    sorted_due = sorted(due, key=itemgetter("topic"))
    for topic, group in groupby(sorted_due, key=itemgetter("topic")):
        subscribers = list(group)
        emails = [s["email"] for s in subscribers]
        logger.info(f"Running pipeline for topic '{topic}' → {len(emails)} subscriber(s)")

        report_md = _run_for_topic(topic)
        if report_md is None:
            continue

        for email in emails:
            try:
                send_email_to_subscriber(email, topic, report_md)
                logger.info(f"✅ Email sent to {email}")
            except Exception as e:
                logger.error(f"❌ Email to {email} failed: {e}")

    logger.info("Subscription check complete.")


if __name__ == "__main__":
    schedule.every(1).minutes.do(check_and_run)
    logger.info("Subscription scheduler ready — checking every minute. Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)
