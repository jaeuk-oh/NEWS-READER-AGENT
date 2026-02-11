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
TRANSLATED_REPORT_FILE = "output/final_report_ko.md"


def run_pipeline():
    """Execute crew → translate → Notion → email.

    Error strategy:
      - Crew failure        → abort. No report to send.
      - Translation failure → log, continue with English version.
      - Notion failure      → log, continue to email.
      - Email failure       → log.
    """
    topic = os.getenv("NEWS_TOPIC", "AI, AI-agent, influence of agent in industry")
    translation_enabled = os.getenv("TRANSLATION_ENABLED", "false").lower() == "true"
    target_lang = os.getenv("TRANSLATION_TARGET_LANG", "ko")

    logger.info(f"Pipeline starting — topic: {topic}")
    logger.info(f"Translation: {'enabled' if translation_enabled else 'disabled'} (target: {target_lang})")

    # --- Stage 1: CrewAI pipeline ---
    try:
        from main import run_crew
        run_crew(topic)
        logger.info(f"✅ [Stage 1] Crew completed. Report: {REPORT_FILE}")
    except Exception as e:
        logger.error(f"❌ [Stage 1] Crew failed: {e}")
        return

    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report_md = f.read()
    except FileNotFoundError:
        logger.error(f"❌ [Stage 1] {REPORT_FILE} not found after crew run. Aborting.")
        return

    # --- Stage 1.5: Translation (optional) ---
    if translation_enabled:
        try:
            from services.translator import translate_report_safe

            logger.info(f"🌐 [Stage 1.5] Starting translation (en → {target_lang})...")
            translated_md = translate_report_safe(report_md, target_lang=target_lang)

            if translated_md:
                # Save translated version
                with open(TRANSLATED_REPORT_FILE, "w", encoding="utf-8") as f:
                    f.write(translated_md)

                # Use translated version for Notion/Email
                report_md = translated_md
                logger.info(f"✅ [Stage 1.5] Translation completed. Saved to: {TRANSLATED_REPORT_FILE}")
            else:
                logger.warning("⚠️  [Stage 1.5] Translation returned None. Using English version.")

        except Exception as e:
            logger.error(f"❌ [Stage 1.5] Translation failed: {e}. Using English version.")
    else:
        logger.info("⏭️  [Stage 1.5] Translation skipped (TRANSLATION_ENABLED=false)")

    # --- Stage 2: Publish to Notion ---
    notion_url = None
    try:
        from services.notion import create_notion_page
        notion_url = create_notion_page(topic=topic, markdown_content=report_md)
        logger.info(f"✅ [Stage 2] Notion page created: {notion_url}")
    except Exception as e:
        logger.error(f"❌ [Stage 2] Notion publish failed: {e}")

    # --- Stage 3: Send email ---
    try:
        from services.notifier import send_email
        send_email(topic=topic, report_md=report_md, notion_url=notion_url)
        logger.info("✅ [Stage 3] Email sent.")
    except Exception as e:
        logger.error(f"❌ [Stage 3] Email failed: {e}")

    logger.info("🎉 Pipeline complete.")


if __name__ == "__main__":
    schedule.every().day.at("07:00").do(run_pipeline)
    logger.info("Scheduler ready — daily job at 07:00 (system local time). Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)
