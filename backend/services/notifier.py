"""이메일 발송 서비스.

Gmail SMTP를 사용해 뉴스 브리핑을 구독자에게 전송한다.
HTML 본문은 inline CSS로 스타일링되며, 구독 취소 링크를 포함한다.
"""
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


def _build_html(topic: str, today: str, content_html: str, unsubscribe_url: str) -> str:
    """뉴스 브리핑 HTML 이메일 본문을 생성한다.

    inline CSS를 사용해 대부분의 이메일 클라이언트에서 렌더링된다.

    Args:
        topic: 뉴스 주제 (헤더에 표시).
        today: 발송 날짜 문자열 (YYYY-MM-DD).
        content_html: markdown2로 변환된 HTML 본문.
        unsubscribe_url: 구독 취소 링크 URL.
    """
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f8;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- 헤더 -->
        <tr>
          <td style="background-color:#1a1a2e;padding:28px 32px;">
            <p style="margin:0;font-size:12px;color:#8892b0;letter-spacing:1px;text-transform:uppercase;">News Briefing</p>
            <h1 style="margin:6px 0 0;font-size:22px;color:#ffffff;font-weight:700;">{topic}</h1>
            <p style="margin:8px 0 0;font-size:13px;color:#8892b0;">{today}</p>
          </td>
        </tr>

        <!-- 본문 -->
        <tr>
          <td style="padding:32px;color:#333333;font-size:15px;line-height:1.7;">
            <style>
              /* 이메일 클라이언트 일부는 <style> 태그를 무시하지만, 지원하는 곳에선 동작함 */
              h1,h2,h3{{color:#1a1a2e;margin-top:24px;margin-bottom:8px;}}
              h2{{font-size:18px;border-bottom:2px solid #e8eaf6;padding-bottom:6px;}}
              h3{{font-size:15px;}}
              p{{margin:0 0 12px;}}
              a{{color:#4f6ef7;}}
              ul,ol{{padding-left:20px;}}
              li{{margin-bottom:6px;}}
              hr{{border:none;border-top:1px solid #e8eaf6;margin:24px 0;}}
              blockquote{{border-left:3px solid #4f6ef7;margin:0;padding:8px 16px;background:#f0f4ff;color:#555;}}
            </style>
            {content_html}
          </td>
        </tr>

        <!-- 구분선 -->
        <tr>
          <td style="padding:0 32px;">
            <hr style="border:none;border-top:1px solid #e8eaf6;margin:0;">
          </td>
        </tr>

        <!-- 푸터 -->
        <tr>
          <td style="padding:24px 32px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#999999;">
              이 이메일은 News Reader Agent 구독자에게 발송됩니다.
            </p>
            <p style="margin:8px 0 0;font-size:12px;color:#999999;">
              더 이상 받고 싶지 않으신가요?
              <a href="{unsubscribe_url}" style="color:#4f6ef7;text-decoration:underline;">구독 취소</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email_to_subscriber(
    recipient: str,
    topic: str,
    report_md: str,
    unsubscribe_token: str,
) -> None:
    """뉴스 브리핑 이메일을 구독자에게 발송한다.

    Args:
        recipient: 구독자 이메일 주소.
        topic: 뉴스 주제 (제목 및 헤더에 사용).
        report_md: 마크다운 형식의 리포트 본문.
        unsubscribe_token: 구독 취소 링크에 사용할 UUID 토큰.
    """
    sender   = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    # 구독 취소 링크 기반 URL (환경 변수로 주입, 기본값은 로컬)
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    today   = datetime.now().strftime("%Y-%m-%d")
    subject = f"[News Briefing] {today} — {topic}"

    # 마크다운 → HTML 변환
    content_html = markdown2.markdown(
        report_md, extras=["fenced-code-blocks", "tables", "header-ids"]
    )

    # 구독 취소 URL 생성
    unsubscribe_url = f"{base_url}/subscriptions/unsubscribe?token={unsubscribe_token}"

    html_body = _build_html(topic, today, content_html, unsubscribe_url)

    msg = MIMEMultipart("alternative")
    msg["From"]    = sender
    msg["To"]      = recipient
    msg["Subject"] = subject
    # List-Unsubscribe 헤더 — Gmail/Outlook이 자동으로 취소 버튼을 노출함
    msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    msg.attach(MIMEText(report_md, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    logger.info(f"Subscriber email sent to {recipient} (topic={topic})")
