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
HARVEST_FILE = "output/content_harvest.md"


def _run_for_topic(topic: str) -> str | None:
    """Run the CrewAI pipeline for *topic* and return the raw English report markdown.

    Returns None on failure or when no articles were found.
    """
    try:
        from main import run_crew

        run_crew(topic)
    except Exception as e:
        logger.error(f"❌ Crew failed for topic '{topic}': {e}")
        return None

    # Zero-article guard: skip email if harvest found nothing
    try:
        with open(HARVEST_FILE, "r", encoding="utf-8") as f:
            harvest = f.read()
        if "Articles after filtering: 0" in harvest:
            logger.warning(f"⚠️ No articles found for topic '{topic}'. Skipping email.")
            return None
    except FileNotFoundError:
        pass

    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"❌ {REPORT_FILE} not found after crew run.")
        return None


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
        logger.info(f"Running pipeline for topic '{topic}' → {len(subscribers)} subscriber(s)")

        report_md = _run_for_topic(topic)
        if report_md is None:
            continue

        for sub in subscribers:
            target_lang = sub.get("target_lang", "ko")
            final_report = report_md

            if target_lang != "en":
                try:
                    from services.translator import translate_to_TargetLang
                    final_report = translate_to_TargetLang(report_md, target_lang)
                except Exception as e:
                    logger.warning(f"Translation skipped for {sub['email']}: {e}")

            try:
                send_email_to_subscriber(sub["email"], topic, final_report)
                logger.info(f"✅ Email sent to {sub['email']} (lang={target_lang})")
            except Exception as e:
                logger.error(f"❌ Email to {sub['email']} failed: {e}")

    logger.info("Subscription check complete.")


def run_once():
    """One-shot mode for GitHub Actions: process all subscriptions due this hour."""
    import db
    from services.notifier import send_email_to_subscriber

    now = datetime.now()
    hour = now.strftime("%H")
    due = db.get_due_subscriptions_for_hour(hour)

    if not due:
        logger.info(f"No subscriptions due for hour {hour}:xx")
        return

    logger.info(f"Found {len(due)} subscription(s) due in hour {hour}:xx")

    sorted_due = sorted(due, key=itemgetter("topic"))
    for topic, group in groupby(sorted_due, key=itemgetter("topic")):
        subscribers = list(group)
        logger.info(f"Running pipeline for topic '{topic}' → {len(subscribers)} subscriber(s)")

        report_md = _run_for_topic(topic)
        if report_md is None:
            continue

        for sub in subscribers:
            target_lang = sub.get("target_lang", "ko")
            final_report = report_md

            if target_lang != "en":
                try:
                    from services.translator import translate_to_TargetLang
                    final_report = translate_to_TargetLang(report_md, target_lang)
                except Exception as e:
                    logger.warning(f"Translation skipped for {sub['email']}: {e}")

            try:
                send_email_to_subscriber(sub["email"], topic, final_report)
                logger.info(f"✅ Email sent to {sub['email']} (lang={target_lang})")
            except Exception as e:
                logger.error(f"❌ Email to {sub['email']} failed: {e}")

    logger.info("run_once complete.")


if __name__ == "__main__":
    schedule.every(1).minutes.do(check_and_run)
    logger.info("Subscription scheduler ready — checking every minute. Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)
