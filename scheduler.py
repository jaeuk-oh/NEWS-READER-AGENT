"""
Scheduled news pipeline runner.

Runs the full pipeline every day at 07:00 system local time.
Assumes system timezone is Asia/Seoul (KST).

Start:  uv run python scheduler.py
Stop:   Ctrl+C
"""

import os
import time
import logging

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


def run_pipeline():
    """Execute crew → Notion → email.

    Error strategy:
      - Crew failure  → abort. No report to send.
      - Notion failure → log, continue to email.
      - Email failure  → log.
    """
    topic = os.getenv("NEWS_TOPIC", "AI, AI-agent, influence of agent in industry")
    logger.info(f"Pipeline starting — topic: {topic}")

    # --- Stage 1: CrewAI pipeline ---
    try:
        from main import run_crew
        run_crew(topic)
        logger.info(f"Crew completed. Report: {REPORT_FILE}")
    except Exception as e:
        logger.error(f"[Stage 1] Crew failed: {e}")
        return

    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report_md = f.read()
    except FileNotFoundError:
        logger.error(f"[Stage 1] {REPORT_FILE} not found after crew run. Aborting.")
        return

    # --- Stage 2: Publish to Notion ---
    notion_url = None
    try:
        from services.notion import create_notion_page
        notion_url = create_notion_page(topic=topic, markdown_content=report_md)
        logger.info(f"[Stage 2] Notion page created: {notion_url}")
    except Exception as e:
        logger.error(f"[Stage 2] Notion publish failed: {e}")

    # --- Stage 3: Send email ---
    try:
        from services.notifier import send_email
        send_email(topic=topic, report_md=report_md, notion_url=notion_url)
        logger.info("[Stage 3] Email sent.")
    except Exception as e:
        logger.error(f"[Stage 3] Email failed: {e}")

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    schedule.every().day.at("07:00").do(run_pipeline)
    logger.info("Scheduler ready — daily job at 07:00 (system local time). Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)
