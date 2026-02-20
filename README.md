# News Reader Agent

구독 기반 AI 뉴스 브리핑 시스템. 원하는 토픽과 시간을 등록하면 CrewAI 멀티 에이전트 파이프라인이 뉴스를 수집·요약·큐레이션하여 이메일로 발송한다.

---

## 주요 기능

- **Google OAuth 로그인** — Streamlit 내장 OAuth로 소셜 로그인 지원
- **토픽 구독** — 키워드(쉼표 구분 다중 토픽 가능)와 발송 시각을 등록
- **3단계 CrewAI 파이프라인** — 수집 → 요약 → 큐레이션 순서로 자동 처리
- **예약 발송** — 스케줄러가 매분 DB를 확인, 설정 시각에 자동 실행
- **한국어 번역 (선택)** — `TRANSLATION_ENABLED=true` 설정 시 보고서를 자동 번역

---

## 아키텍처

```
Streamlit (app.py)
    ├─ 구독 등록/관리 UI (2탭)
    └─ db.py → Supabase (subscriptions 테이블)

subscription_scheduler.py (매분 체크)
    ├─ db.get_due_subscriptions(HH:MM)
    ├─ 동일 토픽 그룹핑 → main.run_crew() 1회 실행
    │       │
    │       ├─ news_hunter_agent   →  output/content_harvest.md
    │       │      멀티 쿼리 검색, 스크래핑, 전문 + 점수
    │       ├─ summarizer_agent    →  output/summary.md
    │       │      3단계 요약 + 핵심 시사점, 점수 유지
    │       └─ curator_agent       →  output/final_report.md
    │              점수 기반 리드 선정, 동적 섹션, 에디터 분석
    ├─ 번역 (설정 시) → services/translator.py
    └─ send_email_to_subscriber() → 구독자 이메일 발송
```

---

## 빠른 시작

**1. 의존성 설치**

```bash
uv sync
```

**2. 환경변수 설정**

`.env` 파일을 생성하고 아래 환경변수 섹션을 참고해 값을 채운다.

**3. Streamlit UI 실행**

```bash
uv run streamlit run app.py
```

**4. 구독 스케줄러 실행** (별도 터미널)

```bash
uv run python subscription_scheduler.py
```

---

## 환경변수

`.env` 파일에 아래 키를 설정한다.

| 변수명 | 설명 | 필수 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 (CrewAI LLM 백엔드) | ✅ |
| `FIRECRAWL_API_KEY` | Firecrawl API 키 (웹 검색·스크래핑) | ✅ |
| `SUPABASE_URL` | Supabase 프로젝트 URL | ✅ |
| `SUPABASE_KEY` | Supabase anon/service 키 | ✅ |
| `GMAIL_SENDER` | 발신자 Gmail 주소 | ✅ |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (16자리) | ✅ |
| `TRANSLATION_ENABLED` | `true` 로 설정 시 한국어 번역 활성화 | 선택 |
| `TRANSLATION_TARGET_LANG` | 번역 대상 언어 코드 (기본값: `ko`) | 선택 |
| `NEWS_TOPIC` | `main.py` 직접 실행 시 기본 토픽 | 선택 |

> **Google OAuth** 설정은 `.streamlit/secrets.toml`에 별도로 구성한다.

---

## 유용한 명령어

```bash
# 파이프라인 1회 수동 실행
uv run python main.py

# 구독 파이프라인 1회 수동 실행 (스케줄러 없이)
uv run python -c "from subscription_scheduler import run_once; run_once()"
```

---

## 트러블슈팅

### Streamlit: `st.login()` / `st.logout()`는 반드시 버튼 안에서 호출할 것

**문제**

Streamlit은 상태가 바뀔 때마다 스크립트 전체를 위에서 아래로 재실행한다. 최상위 스코프에 `st.login()` 또는 `st.logout()`을 그냥 두면 **렌더링마다 자동 호출**되어 무한 루프가 발생한다.

- `st.login()` 노출 → 페이지 로드마다 Google 리다이렉트 자동 발생
- `st.logout()` 노출 → 로그인 직후 자동 로그아웃 → 다시 로그인 화면 → 반복

**해결**

```python
# ❌ 잘못된 방식 — 렌더링마다 자동 실행됨
st.login("google")
st.logout()

# ✅ 올바른 방식 — 버튼 클릭 시에만 실행됨
if st.button("Google로 로그인", type="primary"):
    st.login("google")

if st.button("로그아웃"):
    st.logout()
```

> 관련 커밋: `575dc58` (fix: resolve Google OAuth auto-redirect and infinite login loop)

---