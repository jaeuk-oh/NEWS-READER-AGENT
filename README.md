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
| `SUPABASE_KEY` | Supabase **service_role** 키 (백엔드 전용, 절대 프론트에 노출 금지) | ✅ |
| `GMAIL_SENDER` | 발신자 Gmail 주소 | ✅ |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (16자리) | ✅ |
| `TRANSLATION_ENABLED` | `true` 로 설정 시 한국어 번역 활성화 | 선택 |
| `TRANSLATION_TARGET_LANG` | 번역 대상 언어 코드 (기본값: `ko`) | 선택 |
| `NEWS_TOPIC` | `main.py` 직접 실행 시 기본 토픽 | 선택 |

> **Google OAuth** 설정은 `.streamlit/secrets.toml`에 별도로 구성한다.

### 프론트엔드 환경변수 (`frontend/.env`)

| 변수명 | 값 |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL (루트와 동일) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase **anon** 키 (브라우저 노출 안전) |
| `NEXT_PUBLIC_API_URL` | Render 백엔드 URL |

> 프론트는 Supabase를 **Auth 전용**으로만 사용. DB 접근은 FastAPI 백엔드를 통해서만 처리.

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

## 기술 선택 이유

### 왜 CrewAI인가
뉴스 처리는 수집 → 요약 → 큐레이션의 독립적인 3단계로 분리된다. 단일 LLM 호출로 세 작업을 한 번에 처리하면 컨텍스트가 너무 길어져 품질이 떨어진다. CrewAI는 각 단계를 전용 Agent에 위임하고 결과물을 파이프라인으로 연결하기 때문에, 각 Agent가 하나의 역할에만 집중할 수 있다.

### 왜 Supabase인가
PostgreSQL 기반의 managed DB + Auth를 프리티어에서 즉시 사용할 수 있다. 직접 PostgreSQL 서버를 운영하거나 Firebase를 선택하는 것보다 설정 비용이 낮고, Row Level Security(RLS)로 데이터 접근 제어를 DB 레벨에서 처리할 수 있다.

### 왜 Supabase를 쓰면서 FastAPI 서버를 별도로 두는가
Supabase에 프론트엔드에서 직접 접근하면 `service_role` 키(RLS 우회 권한)가 브라우저에 노출된다. FastAPI를 중간에 두면 민감한 키는 서버에만 존재하고, 비즈니스 로직(구독 중복 검사, 스케줄러 트리거 등)을 한 곳에서 관리할 수 있다. 프론트는 Supabase를 Auth 전용으로만 사용한다.

### 왜 이메일 발송인가
뉴스 브리핑은 정해진 시각에 푸시되어야 하는 비동기 콘텐츠다. 앱 푸시 알림은 모바일 앱이 필요하고, 웹소켓은 브라우저가 열려 있어야 한다. 이메일은 수신자가 오프라인이어도 전달되고, 별도 앱 설치 없이 모든 기기에서 읽을 수 있다.

### 왜 Next.js + TypeScript인가
FastAPI 백엔드가 타입이 있는 Pydantic 모델을 쓰기 때문에, 프론트도 TypeScript로 맞추면 API 응답 타입을 공유할 수 있다. Next.js App Router의 Server Components를 쓰면 구독 목록을 클라이언트 waterfall 없이 서버에서 직접 fetch하여 초기 렌더링 속도를 높인다.

### 왜 Render인가 (백엔드 배포)
FastAPI + 스케줄러를 함께 돌리려면 상시 구동 서버가 필요하다. Vercel은 서버리스(함수 단위)라 스케줄러 상시 실행이 불가능하다. Render의 Web Service는 컨테이너를 상시 유지하므로 `subscription_scheduler.py`가 계속 실행된다.

### 왜 스케줄러가 필요한가
구독자마다 설정 시각이 다르고, 서버가 재시작돼도 예약이 유지되어야 한다. DB에 `schedule_time`을 저장하고 매분 체크하는 방식은 외부 큐(Celery, SQS 등) 없이도 동작하며, 스케일이 작은 MVP 단계에서 가장 단순한 구현이다.