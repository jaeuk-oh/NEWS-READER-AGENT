import re
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import db  # noqa: E402  (after load_dotenv so SUPABASE_* vars are available)

st.set_page_config(page_title="News Briefing Subscription", page_icon="📰", layout="centered")
st.title("📰 News Briefing Subscription")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

tab_register, tab_manage = st.tabs(["구독 등록", "내 구독 관리"])

# ── Tab 1: Register ──────────────────────────────────────────────

with tab_register:
    st.subheader("새 구독 등록")

    topic = st.text_input("키워드 (토픽)", placeholder="AI, AI-agent")
    email = st.text_input("이메일", placeholder="you@example.com")
    schedule_time = st.time_input("발송 시간", value=None)

    if st.button("구독하기", type="primary"):
        # Validation
        if not topic.strip():
            st.error("키워드를 입력해주세요.")
        elif not email.strip() or not EMAIL_RE.match(email.strip()):
            st.error("올바른 이메일 주소를 입력해주세요.")
        elif schedule_time is None:
            st.error("발송 시간을 선택해주세요.")
        else:
            time_str = schedule_time.strftime("%H:%M")
            try:
                db.add_subscription(email.strip(), topic.strip(), time_str)
                st.success(f"구독 완료! {time_str}에 '{topic.strip()}' 브리핑을 발송합니다.")
            except ValueError as e:
                st.warning(str(e))

# ── Tab 2: Manage ────────────────────────────────────────────────

with tab_manage:
    st.subheader("내 구독 관리")

    lookup_email = st.text_input("이메일로 조회", placeholder="you@example.com", key="lookup")

    if st.button("조회"):
        if not lookup_email.strip() or not EMAIL_RE.match(lookup_email.strip()):
            st.error("올바른 이메일 주소를 입력해주세요.")
        else:
            subs = db.get_subscriptions_by_email(lookup_email.strip())
            if not subs:
                st.info("등록된 구독이 없습니다.")
            else:
                st.session_state["subs"] = subs

    # Render subscription list from session state
    subs = st.session_state.get("subs", [])
    for sub in subs:
        col1, col2, col3 = st.columns([3, 1, 1])
        status = "✅ 활성" if sub["is_active"] else "⏸️ 비활성"
        col1.write(f"**{sub['topic']}** — {sub['schedule_time']} ({status})")

        if sub["is_active"]:
            if col2.button("비활성", key=f"deact_{sub['id']}"):
                db.deactivate_subscription(sub["id"])
                st.session_state["subs"] = db.get_subscriptions_by_email(lookup_email.strip())
                st.rerun()
        else:
            if col2.button("활성화", key=f"act_{sub['id']}"):
                db.activate_subscription(sub["id"])
                st.session_state["subs"] = db.get_subscriptions_by_email(lookup_email.strip())
                st.rerun()

        if col3.button("삭제", key=f"del_{sub['id']}"):
            db.delete_subscription(sub["id"])
            st.session_state["subs"] = db.get_subscriptions_by_email(lookup_email.strip())
            st.rerun()
