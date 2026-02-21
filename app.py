import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import db  # noqa: E402  (after load_dotenv so SUPABASE_* vars are available)

st.set_page_config(page_title="News Briefing Subscription", page_icon="📰", layout="centered")

LANGUAGES = {
    "한국어": "ko",
    "English (번역 없음)": "en",
    "日本語": "ja",
    "中文 (简体)": "zh-CN",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
}

# ── Auth ──────────────────────────────────────────────────────────

if not st.user.is_logged_in:
    st.title("📰 News Briefing Subscription")
    st.write("서비스를 이용하려면 Google 계정으로 로그인하세요.")
    if st.button("Google로 로그인", type="primary"):
        st.login("google")
    st.stop()

_user_name = st.user.get("name") or st.user.get("given_name") or "사용자"
_user_email = st.user.get("email") or ""

with st.sidebar:
    st.write(f"**{_user_name}**")
    st.write(_user_email)
    if st.button("로그아웃"):
        st.logout()

if not _user_email:
    st.error("Google 계정에서 이메일 정보를 가져올 수 없습니다. 다른 계정으로 시도해주세요.")
    st.stop()

user_email = _user_email

# ── Main UI ───────────────────────────────────────────────────────

st.title("📰 News Briefing Subscription")

tab_register, tab_manage = st.tabs(["구독 등록", "내 구독 관리"])

# ── Tab 1: Register ──────────────────────────────────────────────

with tab_register:
    st.subheader("새 구독 등록")
    st.caption(f"구독 이메일: {user_email}")

    topic = st.text_input("키워드 (토픽)", placeholder="AI, AI-agent")
    schedule_time = st.time_input("발송 시간", value=None)
    lang_label = st.selectbox("리포트 언어", list(LANGUAGES.keys()), index=0)
    lang_code = LANGUAGES[lang_label]

    if st.button("구독하기", type="primary"):
        if not topic.strip():
            st.error("키워드를 입력해주세요.")
        elif schedule_time is None:
            st.error("발송 시간을 선택해주세요.")
        else:
            time_str = schedule_time.strftime("%H:%M")
            try:
                db.add_subscription(user_email, topic.strip(), time_str, lang_code)
                st.success(f"구독 완료! {time_str}에 '{topic.strip()}' 브리핑을 발송합니다.")
            except ValueError as e:
                st.warning(str(e))
            except Exception as e:
                st.error(f"구독 등록 중 오류가 발생했습니다: {e}")

# ── Tab 2: Manage ────────────────────────────────────────────────

with tab_manage:
    st.subheader("내 구독 관리")

    try:
        subs = db.get_subscriptions_by_email(user_email)
    except Exception as e:
        st.error(f"구독 목록을 불러오는 중 오류가 발생했습니다: {e}")
        subs = []
    if not subs:
        st.info("등록된 구독이 없습니다.")
    else:
        for sub in subs:
            col1, col2, col3 = st.columns([3, 1, 1])
            status = "✅ 활성" if sub["is_active"] else "⏸️ 비활성"
            lang = sub.get("target_lang", "ko")
            col1.write(f"**{sub['topic']}** — {sub['schedule_time']} | {lang} ({status})")

            if sub["is_active"]:
                if col2.button("비활성", key=f"deact_{sub['id']}"):
                    try:
                        db.deactivate_subscription(sub["id"])
                    except Exception as e:
                        st.error(f"오류: {e}")
                    st.rerun()
            else:
                if col2.button("활성화", key=f"act_{sub['id']}"):
                    try:
                        db.activate_subscription(sub["id"])
                    except Exception as e:
                        st.error(f"오류: {e}")
                    st.rerun()

            if col3.button("삭제", key=f"del_{sub['id']}"):
                try:
                    db.delete_subscription(sub["id"])
                except Exception as e:
                    st.error(f"오류: {e}")
                st.rerun()
