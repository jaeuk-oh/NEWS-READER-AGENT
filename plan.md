# Streamlit 웹 UI 추가 계획

## 목표
- 기존 `.env` 기반 이메일 발송은 그대로 유지
- Streamlit 웹 앱을 통해 외부 유저가 **키워드, 이메일, 시간**을 등록하면 해당 유저에게도 뉴스 브리핑 발송

---

## 아키텍처 설계

```
[기존 유지]
scheduler.py (07:00 KST) → main.run_crew → Notion + 기존 이메일

[신규 추가]
Streamlit (app.py)
    ├─ 구독 등록/관리 UI
    └─ SQLite (subscriptions.db)

subscription_scheduler.py
    └─ 매분 체크 → 시간 도래한 구독 그룹별 파이프라인 실행 → 구독자 이메일 발송
```

### 핵심 설계 원칙
1. **기존 코드 최소 변경** — 기존 `scheduler.py`, `main.py`는 건드리지 않음
2. **Supabase** — 클라우드 PostgreSQL 기반 구독 관리 (멀티 디바이스 접근, 확장성)
3. **구독 스케줄러 분리** — 기존 스케줄러와 독립적으로 동작

---

## 신규 파일

### 1. `db.py` — 구독 DB 관리 ✅

```python
# Supabase 기반 구독 CRUD
# 테이블: subscriptions (id uuid PK, email text, topic text, schedule_time text, is_active bool, created_at timestamptz)
# 환경 변수: SUPABASE_URL, SUPABASE_KEY
```

- `add_subscription(email, topic, schedule_time)` — 구독 등록 (중복 방지)
- `get_subscriptions()` — 전체 조회
- `get_due_subscriptions(current_time)` — 현재 시간에 발송할 활성 구독 조회
- `get_subscriptions_by_email(email)` — 특정 이메일 구독 조회
- `activate_subscription(id)` / `deactivate_subscription(id)` — 활성/비활성 토글
- `delete_subscription(id)` — 구독 삭제

### 2. `app.py` — Streamlit 웹 UI

**페이지 구성 (단일 페이지, 탭 기반):**

**탭 1: 구독 등록**
- 키워드(토픽) 입력 (text_input)
- 이메일 입력 (text_input, 간단한 형식 검증)
- 발송 시간 선택 (time_input, 기본값 07:00)
- "구독" 버튼 → SQLite에 저장 → 성공 메시지

**탭 2: 내 구독 관리**
- 이메일 입력으로 내 구독 조회
- 구독별 활성/비활성 토글, 삭제 버튼
- 현재 등록된 구독 목록 테이블 표시

**탭 3: 즉시 실행 (선택)**
- 등록된 구독 중 하나를 선택하여 즉시 파이프라인 실행
- 결과 미리보기

### 3. `subscription_scheduler.py` — 구독 기반 스케줄러 ✅

```
매 1분마다:
  1. DB에서 현재 HH:MM에 해당하는 활성 구독 조회
  2. 동일 토픽 구독자를 그룹핑 (같은 토픽이면 파이프라인 1번만 실행)
  3. 토픽별로 main.run_crew(topic) 실행
  4. 번역 (설정 시)
  5. 해당 그룹의 모든 구독자 이메일로 발송
  6. 실행 로그 기록
```

### 4. `services/notifier.py` 수정

- 기존 `send_email()` 함수는 유지
- `send_email_to_subscriber(recipient, topic, report_md)` 함수 추가
  - 기존 함수와 거의 동일하나, recipient를 파라미터로 받음
  - `.env`의 `GMAIL_SENDER`와 `GMAIL_APP_PASSWORD`는 공유 (발신 계정은 동일)
  - Notion URL은 포함하지 않음 (구독자에게는 이메일만)

---

## 실행 방법

```bash
# 기존 파이프라인 (변경 없음)
uv run python scheduler.py

# Streamlit 웹 UI
uv run streamlit run app.py

# 구독 스케줄러 (별도 프로세스)
uv run python subscription_scheduler.py
```

---

## 구현 순서

1. **`db.py`** — SQLite 스키마 + CRUD 함수
2. **`services/notifier.py` 수정** — `send_email_to_subscriber()` 추가
3. **`app.py`** — Streamlit UI (구독 등록 + 관리)
4. **`subscription_scheduler.py`** — 구독 기반 스케줄러
5. **`pyproject.toml`** — `streamlit` 의존성 추가
6. **`CLAUDE.md`** 업데이트 — 새 명령어/아키텍처 반영

---

## 의존성 추가

```toml
# pyproject.toml에 추가
"streamlit>=1.45.0",
"supabase>=2.16.0",
```

---

## 고려사항

- **Supabase 설정**: Supabase 프로젝트에서 `subscriptions` 테이블을 수동 생성해야 함 (아래 SQL 참조)
- **이메일 검증**: 기본적인 형식 검증만 (정규식). 인증 이메일 발송은 범위 밖
- **API 비용**: 동일 토픽 구독자를 그룹핑하여 Firecrawl/OpenAI API 호출 최소화
- **기존 파이프라인**: `.env`의 `GMAIL_RECIPIENT`로 보내는 기존 흐름은 완전히 독립적으로 유지

## Supabase 테이블 생성 SQL

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    topic TEXT NOT NULL,
    schedule_time TEXT NOT NULL,       -- "HH:MM" format
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (email, topic)
);
```
